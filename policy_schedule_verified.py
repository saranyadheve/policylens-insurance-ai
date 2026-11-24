"""Verified, geometry-backed policy schedule fields.

This module uses PDF *source text and positions*, not LLM guesses or predefined
policy values. Only a policy schedule's own labels are authoritative.
It deliberately refuses to attribute insurer/agent contacts to the insured.
"""
import re
import pymupdf
from vehicle_geometry import vehicle_records

DATE = r'\d{1,2}[/-]\d{1,2}[/-]\d{4}'
BAD = {'none', 'na', 'n/a', '-', ''}

def clean(s):
    return ' '.join(str(s or '').replace('\u00a0',' ').split()).strip(' :')

def coords(page, value, label=None, clip=None):
    """Match source text. Never substitute the wrong page/word silently."""
    value = clean(value)
    if not value: return None
    spots = page.search_for(value)
    if clip is not None:
        region = pymupdf.Rect(clip)
        spots = [r for r in spots if region.intersects(r)]
    if not spots:
        # Phrase may span line fragments; match the longest text token in area.
        words = [w for w in page.get_text('words') if (clip is None or pymupdf.Rect(clip).intersects(pymupdf.Rect(w[:4])))]
        wanted = re.sub(r'[^a-z0-9]', '', value.lower())
        for i, word in enumerate(words):
            r = pymupdf.Rect(word[:4]); assembled = ''
            for w in words[i:i+32]:
                if w[5] != word[5] and r.y1 + 20 < w[1]: break
                assembled += re.sub(r'[^a-z0-9]', '', w[4].lower())
                r |= pymupdf.Rect(w[:4])
                if assembled == wanted:
                    spots.append(r);break
                if len(assembled)>len(wanted):break
    if not spots:return None
    if label:
        labels=page.search_for(label)
        if labels:
            spots.sort(key=lambda r:min(abs(r.y0-l.y0)*3+abs(r.x0-l.x1)*.16 for l in labels))
    r=spots[0]
    return [round(float(x),2) for x in (r.x0,r.y0,r.x1,r.y1)]

def make(field, val, page, page_num, label='', *, bbox=None, review=False):
    val=clean(val)
    if not val or val.lower() in BAD: return None
    rect = bbox if bbox is not None else coords(page,val,label)
    return {'Field':field,'Value':val,'Page':page_num,'BBox':rect,
            'Evidence':f'{label or field}: {val}'[:250], 'Person':'',
            'Method':'verified policy schedule', 'Review':review}

def line_value(text,label_pattern, value_pattern=r'[^\n]+'):
    match=re.search(r'(?im)^\s*(?:'+label_pattern+r')\s*\n\s*:?\s*('+value_pattern+r')',text)
    return clean(match.group(1)) if match else ''

def policy_schedule_records(pdf_bytes, max_pages=6):
    """Retrieve trustworthy common fields and related policy-specific numbers.

    A policy schedule is detected via semantic page headings/labels, not type
    selection. Does not invent missing customer contacts.
    """
    records=[]
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as doc:
        policy_pages=[]
        for pi,page in enumerate(doc):
            if pi>=max_pages:break
            t=page.get_text('text').replace('\u00a0',' ')
            if ('POLICY SCHEDULE' in t.upper() or 'CERTIFICATE OF INSURANCE' in t.upper() or
                ('Policy Number' in t and 'Insurance Start Date' in t)):
                policy_pages.append((pi,page,t))
        if not policy_pages:return []

        # Insurer is the actual underwriter, never broker, dealer or agent.
        for pi,page,t in policy_pages:
            for m in re.finditer(r'(?im)^\s*([A-Z][A-Z .&-]{6,90}\bINSURANCE(?:\s+COMPANY)?(?:\s+LIMITED|\s+LTD\.?))\s*$',t):
                company=clean(m.group(1))
                if 'BROKER' in company or 'AGENT' in company:continue
                record=make('Insurer Name',company,page,pi+1,'')
                if record:
                    records.append(record);break
            if any(x['Field']=='Insurer Name' for x in records):break

        for pi,page,t in policy_pages:
            pn=pi+1
            # Source text may use a label on the same line or next line.
            def add(field,value, label=None, bbox=None, review=False):
                r=make(field,value,page,pn,label or field,bbox=bbox,review=review)
                if r:records.append(r)

            policy=line_value(t,r'Policy (?:Number|No\.?)',r'[A-Za-z0-9/-]{8,35}')
            if policy:add('Policy Number',policy,'Policy Number')
            start=line_value(t,r'Insurance Start Date\s*&\s*Time',DATE+r'(?:\s+\d{1,2}:\d{2})?(?:\s*\(hours\))?')
            if start:
                date=re.search(DATE,start)
                if date:add('Policy Start Date',date.group(0),'Insurance Start Date & Time')
            expiry=line_value(t,r'Insurance expiry Date\s*&\s*Time',DATE+r'(?:\s+midnight)?')
            if expiry:
                date=re.search(DATE,expiry)
                if date:add('Policy End Date',date.group(0),'Insurance expiry Date & Time')
            insured=line_value(t,r'Insured Name/ID',r'[^\n]{3,100}')
            if insured:
                # Split customer's actual name from trailing Customer ID.
                name=re.sub(r'/\s*\d{5,}\b.*$','',insured).strip()
                if name:add('Insured Name',name,'Insured Name/ID')
            # The insured address is in the LEFT schedule box. Do not read office on right.
            label_rects=page.search_for('Insured address')
            office_rects=page.search_for('Policy Issuing Office Address')
            if label_rects:
                y=label_rects[0].y1+1
                x0=page.rect.x0+20
                # Restrict to left column (right office is adjacent).
                right=min(page.rect.width*.45,(office_rects[0].x0-5) if office_rects else page.rect.width*.48)
                if 0<right and y<page.rect.height:
                    cropped=page.get_text('text',clip=pymupdf.Rect(x0,y,right,y+29),sort=True)
                    items=[clean(s) for s in cropped.splitlines() if clean(s)]
                    items=[x for x in items if not re.fullmatch(r'(?i)(City:|State:|District:|Pincode:)',x)]
                    address=' '.join(items)
                    # Append only customer's city/state/pincode, not broker details.
                    left_words=[w for w in page.get_text('words') if w[0]<right and y<=w[1]<y+28]
                    postal=[w[4] for w in left_words if re.fullmatch(r'\d{6}',w[4])]
                    if postal and postal[0] not in address: address += ' '+postal[0]
                    address=clean(address)
                    if len(address)>15 and 'POLICY ISSUING' not in address.upper():
                        bbox=[round(x0,2),round(y,2),round(right,2),round(y+28,2)]
                        add('Insured Address',address,'Insured address',bbox=bbox)
            # If insured's mobile is masked, NEVER replace with broker/office mobile.
            if 'Mobile:' in t:
                masked=re.search(r'(?m)^Mobile:\s*\n\s*(\*{2,}\d{2,6})',t)
                if masked:add('Insured Mobile (masked)',masked.group(1),'Mobile',review=True)

            # Policy total is the amount actually payable; pre-tax premium kept separate.
            # In a native table, the label + value share a single row.
            for table in page.find_tables().tables:
                try: rows=table.extract()
                except Exception:continue
                for ri,row in enumerate(rows):
                    cells=[clean(c) for c in row]
                    for j,label in enumerate(cells[:-1]):
                        lname=re.sub(r'\s+',' ',label).lower()
                        nxt=clean(cells[j+1])
                        if not re.fullmatch(r'[\d,]+(?:\.\d{1,2})?',nxt):continue
                        if ('total payable premium' in lname or 'gross premium paid' in lname or
                            'total(rounded off)' in lname):
                            rb=None
                            try:rb=[round(float(v),2) for v in table.rows[ri].cells[j+1]]
                            except Exception:pass
                            add('Total Premium',nxt,label,bbox=rb)
                        elif lname in {'premium(a+b)','total premium (a+b)','premium'}:
                            rb=None
                            try:rb=[round(float(v),2) for v in table.rows[ri].cells[j+1]]
                            except Exception:pass
                            add('Premium Before Tax',nxt,label,bbox=rb)

        # Add source-grounded IDV as a SUM INSURED proxy only for motor cover.
        vehicle=list(vehicle_records(pdf_bytes))
        if vehicle and any('MOTOR' in t.upper() for _,_,t in policy_pages):
            for r in vehicle:
                if r.get('Field')=='Total IDV':
                    proxy=dict(r,Field='Sum Insured',Method='motor IDV policy schedule',
                               Evidence='Motor insured declared value (Total IDV): '+r['Value'])
                    records.append(proxy)
                    break
    # Dedup: prefer policy schedule page with exact match; later corrections cannot overwrite.
    seen=set();out=[]
    for r in records:
        k=(r['Field'],r['Value'],r['Page'])
        if k not in seen:seen.add(k);out.append(r)
    return out


def apply_verified(resolved, records, strict_schedule=False):
    """Fix common fields from verified records; refuse broker contact misattribution."""
    for field in ['Email','Mobile Number','Phone Number']:
        # Policy certificates often print insurer, broker and servicing-office contacts.
        # Never silently assign those to the insured customer.
        old=resolved.get(field,{})
        if strict_schedule and not any(r.get('Field')==field for r in records):
            resolved[field]={'value':'','page':None,'evidence':'','person':'','bbox':None,'status':'not_found'}
            continue
        if old.get('value'):
            label=(str(old.get('evidence',''))+' '+str(old.get('value',''))).lower()
            if (field=='Email' and any(x in label for x in ('customercare@','grievance@','helpdesk@')) or
                field=='Mobile Number' and ('agent' in label or 'broker' in label) or
                field=='Phone Number' and ('office' in label or 'broker' in label)):
                resolved[field]={'value':'','page':None,'evidence':'','person':'','bbox':None,'status':'not_found'}
    for r in records:
        field=r['Field']
        if field not in resolved:continue
        if field=='Insurer Name' and 'BROKER' in r['Value'].upper():continue
        previous=resolved[field]
        # Do not let a less precise source overwrite policy schedule.
        if previous.get('_verified'):continue
        resolved[field]={'value':r['Value'],'page':r['Page'],'evidence':r.get('Evidence',''),
                         'person':'','bbox':r.get('BBox'),
                         'status':'review' if r.get('Review') or not r.get('BBox') else 'found',
                         '_verified':True}
    return resolved
