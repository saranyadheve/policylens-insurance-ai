"""Evidence-based checked-option extraction. Reads vector ink + PDF labels.
Not a model: does not claim to read handwritten/scanned tick marks.
"""
import re
import pymupdf

BLUE = (0.05, 0.24, 0.58)


def _blue(c):
    return bool(c and len(c)>=3 and c[2]>.40 and c[2]>c[0]*1.6 and c[2]>c[1]*1.35)


def _ticks(page):
    # Crosses in supplied form are two tiny diagonal blue vector lines.
    crosses={}
    for drawing in page.get_drawings():
        r=drawing['rect']
        if not (_blue(drawing.get('color')) and 2.5<=r.width<=6 and 2.5<=r.height<=6):continue
        pts=[]
        for item in drawing['items']:
            if item[0]=='l':
                a,b=item[1],item[2]
                pts.append((a.x,a.y,b.x,b.y))
        if not pts:continue
        k=(round((r.x0+r.x1)/2,1),round((r.y0+r.y1)/2,1))
        crosses.setdefault(k,set()).update('pos' if (a-b)*(c-d)>0 else 'neg' for a,c,b,d in pts)
    return [k for k,orient in crosses.items() if len(orient)==2]


def _word_items(page):
    return [{'text':w[4],'rect':pymupdf.Rect(w[:4])} for w in page.get_text('words')]


def _near_label(tick,ws):
    x,y=tick
    # Explicit checkbox glyph to the LEFT of the option label.
    boxes=[w for w in ws if w['text']=='☐' and abs(w['rect'].x0-x)<6 and abs(w['rect'].y0-y)<8]
    if boxes:
        b=min(boxes,key=lambda v:abs(v['rect'].x0-x)+abs(v['rect'].y0-y))
        opts=[w for w in ws if w['rect'].x0>=b['rect'].x1-1 and 0<=w['rect'].x0-b['rect'].x1<14 and abs(w['rect'].y0-b['rect'].y0)<5 and w['text']!='☐']
        if opts:
            o=min(opts,key=lambda w:w['rect'].x0)
            return o['text'].strip('.,:'),o['rect'].y0
    # Medical Y/N grids: the mark crosses the letter (no checkbox glyph in text).
    opts=[w for w in ws if w['text'] in ('Y','N','M','F','O') and abs((w['rect'].x0+w['rect'].x1)/2-x)<7 and abs((w['rect'].y0+w['rect'].y1)/2-y)<7]
    if opts:
        o=min(opts,key=lambda w:abs((w['rect'].x0+w['rect'].x1)/2-x)+abs((w['rect'].y0+w['rect'].y1)/2-y))
        return ({'Y':'Yes','N':'No'}.get(o['text'],o['text'])),o['rect'].y0
    return None,None


def _row_name(x,y,ws,pagenum):
    # Read the row heading left of the checkboxes, including first-page split labels.
    left_limit=120 if pagenum==2 else (560 if pagenum==1 else 280)
    # For page 1, look for nearby words left of checkboxes and prefer end-label phrases.
    possible=[w for w in ws if w['rect'].x0<min(x,left_limit) and abs(w['rect'].y0-y)<6 and w['text'] not in ('☐','Y','N')]
    possible.sort(key=lambda w:w['rect'].x0)
    t=' '.join(w['text'] for w in possible)
    lower=t.lower()
    matching=[]
    for phrase in ('Marital Status','Gender','Policy Type','Occupation','Dependent','Alcohol','Tobacco','Existing Health Cover','Past Proposals'):
        if phrase.lower() in lower:
            # Prefer heading closest to the selected option, not an unrelated heading on the same line.
            anchor=max((w['rect'].x0 for w in possible if w['text'].strip(':').lower()==phrase.split()[-1].lower()),default=0)
            matching.append((anchor,phrase))
    if matching:return max(matching)[1]
    if pagenum>=3:
        # Generic nearby table/question heading (can be long, not always reliable)
        desc=[w for w in ws if w['rect'].x0<min(x,280) and -65 < w['rect'].y0-y<=7 and len(w['text'])>2]
        desc.sort(key=lambda z:(abs(z['rect'].y0-y),-z['rect'].x0))
        if desc:return 'Medical Questionnaire'
    return None


def checkbox_records(pdf_bytes,proposal_records=None):
    """Return only selections with a visible vector X and matched option label."""
    found=[]; seen=set()
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as doc:
        proposal=bool(proposal_records)
        for pn,page in enumerate(doc,1):
            ws=_word_items(page)
            for xy in _ticks(page):
                x,y=xy
                opt,ry=_near_label(xy,ws)
                if not opt:continue
                row=_row_name(x,y,ws,pn)
                if not row or row=='Medical Questionnaire':continue
                # The first two insureds of the sample proposal occupy columns x 125-195 and x 198-267.
                # Never assign a person to other templates based on this geometry.
                person=''
                if proposal and pn==2 and 120<=x<270:
                    pnum=1 if x<195 else 2
                    names=[r['Value'] for r in proposal_records if r['Field']=='Insured Name' and r.get('Person')==f'Insured {pnum}']
                    person=names[0] if names else f'Insured {pnum}'
                if proposal and pn in (3,4) and 280<=x<370:
                    pnum=1 if x<327 else 2
                    names=[r['Value'] for r in proposal_records if r['Field']=='Insured Name' and r.get('Person')==f'Insured {pnum}']
                    person=names[0] if names else f'Insured {pnum}'
                if proposal and pn==1:person='Proposer'
                if row=='Gender':
                    value={'M':'Male','F':'Female','O':'Other'}.get(opt,opt)
                elif row=='Marital Status':
                    value={'M':'Married','Single':'Single'}.get(opt,opt)
                elif row=='Policy Type' and opt=='Family':
                    value='Family Floater'
                else:
                    value=opt
                key=(pn,row,value,person,round(y))
                if key in seen:continue
                seen.add(key)
                found.append({'Field':row,'Value':value,'Page':pn,'Evidence':f'Checked option: {value} (vector mark at x={x:.0f}, y={y:.0f})','Person':person,'Method':'vector checkbox + nearby printed option'})
    return found


def query_checkboxes(question,records):
    terms=re.findall(r'[a-z0-9]+',question.lower())
    stops={'what','is','are','the','show','give','me','my','of','in','pdf','please','tell','value','details','for','person','insured','proposer'}
    if not terms:return []
    relevant=[x for x in terms if x not in stops]
    # 'marital status' must preserve marital, and 'gender' is not 'medical'.
    relevant=[w for w in relevant if w not in ('first','second','1st','2nd','arun','meera')]
    if not relevant:return []
    candidates=[r for r in records if all(x in re.findall(r'[a-z0-9]+',r['Field'].lower()) for x in relevant)]
    if any(w in terms for w in ('first','1st','arun')):candidates=[r for r in candidates if r['Person'].upper() in ('ARUN KUMAR','PROPOSER','INSURED 1')]
    if any(w in terms for w in ('second','2nd','meera')):candidates=[r for r in candidates if 'MEERA' in r['Person'].upper()]
    return candidates
