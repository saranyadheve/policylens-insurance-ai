"""Evidence-first PDF fields extraction with geometry-aware two-column reads.
No LLM; unrecognized values stay unfilled. Compatible with digital and scanned PDFs.
"""
import io, re
from collections import defaultdict
import pymupdf

FIELDS = [
    'Policy Number','Insured Name','Insured Code','Insured GSTIN','Insured Address',
    'Issue Office Name','Issue Office Code','Issue Office GSTIN','Issue Office Address',
    'Cover Note Number','Cover Note Date','Start Date','End Date',
    'Gross Premium','GST Amount','CGST Amount','SGST Amount','IGST Amount','Stamp Duty','Total Premium','Sum Insured',
    'TPA ID','TPA Name','TPA Address','TPA Toll Free','Insured Email','Office Email',
    'Nominee Name','Insurer Name',
]
ALIASES = {
 'policy no':'Policy Number','policy number':'Policy Number','policy id':'Policy Number',
 'insured name':'Insured Name','insured company':'Insured Name','insured code':'Insured Code',
 'customer name':'Insured Name','policyholder name':'Insured Name','proposer name':'Insured Name',
 'insured gstin':'Insured GSTIN', 'office gstin':'Issue Office GSTIN',
 'issue office':'Issue Office Name','issuing office':'Issue Office Name',
 'issue office name':'Issue Office Name','office name':'Issue Office Name',
 'issue office address':'Issue Office Address','office address':'Issue Office Address',
 'insured address':'Insured Address','policyholder address':'Insured Address',
 'customer address':'Insured Address','address':'ADDRESSES',
 'cover note number':'Cover Note Number','cover note no':'Cover Note Number',
 'cover note date':'Cover Note Date','start date':'Start Date','commencement date':'Start Date',
 'policy start date':'Start Date','effective date':'Start Date',
 'end date':'End Date','expiry date':'End Date','expiration date':'End Date',
 'policy end date':'End Date','maturity date':'End Date',
 'base premium':'Gross Premium','gross premium':'Gross Premium',
 'total premium':'Total Premium','premium amount':'Total Premium',
 'gst amount':'GST Amount','total gst':'GST Amount','gst':'GST Amount',
 'igst amount':'IGST Amount','igst':'IGST Amount','cgst amount':'CGST Amount','cgst':'CGST Amount',
 'sgst amount':'SGST Amount','sgst':'SGST Amount',
 'stamp duty':'Stamp Duty','sum insured':'Sum Insured','coverage amount':'Sum Insured',
 'tpa name':'TPA Name','tpa id':'TPA ID','tpa address':'TPA Address',
 'tpa toll free':'TPA Toll Free','nominee':'Nominee Name','nominee name':'Nominee Name',
 'insurer name':'Insurer Name','insurance company':'Insurer Name',
 'insured email':'Insured Email','office email':'Office Email',
}
PATTERNS = {
 'Policy Number':r'\bpolicy\s*(?:no\.?|number|id)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]{7,})',
 'Cover Note Number':r'\bcover\s*note\s*(?:no\.?|number)\s*[:#-]?\s*([A-Z0-9/-]{5,})',
 'Cover Note Date':r'\bcover\s*note\s*date\s*[:=-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
 'Insured Code':r'\binsured(?:\x27s)?\s*code\s*[:=-]?\s*([A-Z0-9]{7,})',
 'Issue Office Code':r'\bissue\s*office\s*code\s*[:=-]?\s*(\d{3,})',
 'Gross Premium':r'\b(?:gross|base)\s*premium\s*[:=-]?\s*(?:rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)',
 'Stamp Duty':r'\bstamp\s*duty\s*[:=-]?\s*(?:rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)',
 'Total Premium':r'\b(?:total\s*premium|total)\s*[:=-]\s*(?:rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)',
 'TPA ID':r'\btpa\s*id\s*[:=-]?\s*([A-Z0-9]{6,})',
 'TPA Name':r'\btpa\s*name\s*[:=-]?\s*(.{4,90})',
 'TPA Toll Free':r'\btoll\s*free\s*no\s*[:=-]?\s*(\d[\d ]{8,})',
 'Nominee Name':r'\bnominee\s*name\s*[:=-]?\s*([^;|\n]{3,80})',
}
DATE = r'\d{1,2}[/-]\d{1,2}[/-]\d{4}'
AMOUNT = r'\d[\d,]*(?:\.\d{1,2})?'

def tidy(s): return re.sub(r'\s+',' ',str(s)).strip(' :-|\t\n')

def build_lines(page):
    # word coordinates preserve columns unlike full-page sorted text
    raw = page.get_text('words',sort=False)
    out = defaultdict(list)
    for w in raw:
        x0,y0,x1,y1,word,block,line,wn = w[:8]
        out[(block,line)].append((x0,y0,x1,y1,word))
    rows = []
    for grp in out.values():
        grp.sort(key=lambda x:x[0])
        rows.append({'y':min(z[1] for z in grp),'x':min(z[0] for z in grp),
                     'text':tidy(' '.join(z[4] for z in grp)), 'words':grp})
    return sorted(rows,key=lambda x:(x['y'],x['x']))

def region_rows(page, x_min, x_max, y_start, y_end):
    # Collect words within a geometric region; reconstruct rows using native block line IDs
    groups=defaultdict(list)
    for w in page.get_text('words',sort=False):
        x0,y0,x1,y1,token,bid,lid,wn=w[:8]
        cx=(x0+x1)/2
        if x_min<=cx<x_max and y_start<=y0<y_end:
            groups[(bid,lid)].append((x0,y0,token))
    rows=[]
    for group in groups.values():
        group.sort(key=lambda x:x[0]); rows.append((min(x[1] for x in group),tidy(' '.join(x[2] for x in group))))
    return [txt for _,txt in sorted(rows)]

def clean_address(parts):
    parts=[p for p in parts if p and p not in ('-',':','- -')]
    out=tidy(' '.join(parts))
    out=re.sub(r'\s+,',',',out)
    out=re.sub(r',{2,}',',',out)
    return out

def parse_tax_line(line):
    """Return tax kind and monetary amount, not the tax RATE or a GSTIN."""
    # Require a tax heading, not a word such as GSTIN or text mentioning tax.
    match=re.match(r'^\s*(IGST|CGST|SGST)\b(.*)$',line,re.I)
    if not match:return None
    kind=match.group(1).upper()
    rest=match.group(2).strip()
    # Typical table: 'IGST 18 132919'; inline: 'IGST @18% : 804 /-'
    clean=re.sub(r'@\s*\d+(?:\.\d+)?\s*%', ' ', rest)
    clean=re.sub(r'(?i)\brs\.?\b|₹|`', ' ', clean)
    values=re.findall(r'(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?(?![A-Za-z0-9])',clean)
    if not values:return None
    # Explicit table with rate + amount: take final number.
    amount=values[-1]
    try:return kind,float(amount.replace(',',''))
    except ValueError:return None

def fmt_money(num):
    return str(int(num)) if float(num).is_integer() else ('%.2f'%num).rstrip('0').rstrip('.')

def extract(pdf_bytes, dpi=160):
    doc=pymupdf.open(stream=pdf_bytes,filetype='pdf')
    result={k:{'value':None,'page':None,'evidence':'','method':''} for k in FIELDS}
    page_text=[]; page_modes=[]; page_lines=[]
    tax_parts={}
    def put(field,value,pnum,evidence,method):
        value=tidy(value)
        if value and not result[field]['value']:
            result[field]={'value':value,'page':pnum,'evidence':tidy(evidence),'method':method}
    try:
        for pi,page in enumerate(doc):
            pn=pi+1
            text=page.get_text('text',sort=True)
            digital=len(text.strip())>=75
            if not digital:
                import pytesseract
                from PIL import Image
                pix=page.get_pixmap(dpi=dpi,alpha=False)
                im=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
                try:
                    text=pytesseract.image_to_string(im)
                except (pytesseract.TesseractNotFoundError, FileNotFoundError):
                    text=''
            page_text.append(text);page_modes.append('Embedded text' if digital else ('Tesseract OCR' if text.strip() else 'OCR unavailable'))
            lines=[tidy(z) for z in text.splitlines() if tidy(z)];page_lines.append(lines)
            # Field line matches: avoid mixing nearby columns for two-column policy schedules
            for row in lines:
                for field,regex in PATTERNS.items():
                    m=re.search(regex,row,re.I)
                    if m:
                        val=tidy(m.group(1))
                        if field in ('Gross Premium','GST Amount','Total Premium','Stamp Duty') and not re.fullmatch(AMOUNT,val): continue
                        if field=='Policy Number' and not re.search(r'\d',val):continue
                        put(field,val,pn,row,'text')
            # Prefer the tax breakdown over a partial SGST/CGST line.
            # The first valid occurrence for each tax type is retained even across pages.
            for row in lines:
                item=parse_tax_line(row)
                if not item:continue
                kind,amount=item
                if kind not in tax_parts:
                    tax_parts[kind]=(amount,pn,row)
                    put(kind+' Amount',fmt_money(amount),pn,row,'tax row')
            # Some documents print only a single GST total rather than IGST/CGST/SGST.
            # This is a fallback if no component rows exist in the document.
            # Header-row premium table used by New India and similar policy schedules:
            # Premium | GST | Total followed by a row of three monetary values.
            for line_index, row in enumerate(lines[:-1]):
                if (re.search(r'\bPremium\b',row,re.I)
                    and re.search(r'\bGST\b',row,re.I)
                    and re.search(r'\bTotal\b',row,re.I)):
                    next_row=lines[line_index+1]
                    amounts=re.findall(r'(?<![A-Za-z0-9])\d[\d,]*(?:\.\d{1,2})?(?![A-Za-z0-9])',next_row)
                    # Exclude receipt number in fourth column; use first three values.
                    if len(amounts)>=3 and all(',' in x or len(x)>=4 for x in amounts[:3]):
                        put('Gross Premium',amounts[0],pn,row+' | '+next_row,'premium table')
                        put('Total Premium',amounts[2],pn,row+' | '+next_row,'premium table')
            # policy dates are specifically FROM/TO insurance period, not signature/print date
            m=re.search(r'period\s+of\s+insurance\s*:?\s*FROM\s+.*?('+DATE+r')\s+TO\s+.*?('+DATE+r')',text,re.I|re.S)
            if m:
                put('Start Date',m.group(1),pn,m.group(0),'period')
                put('End Date',m.group(2),pn,m.group(0),'period')
            # If source is digital, inspect columns accurately via geometry
            if digital:
                W=page.rect.width
                # Locate specific headings using document words
                words=page.get_text('words',sort=True)
                def find_seq(seq):
                    seq=seq.lower().split()
                    for i in range(len(words)-len(seq)+1):
                        segment=words[i:i+len(seq)]
                        if [re.sub(r'[^a-z]','',z[4].lower()) for z in segment] == [re.sub(r'[^a-z]','',z) for z in seq] and max(z[1] for z in segment)-min(z[1] for z in segment)<8:
                            return segment
                    return None
                # specific paired headings, next line of name may be below the right office name
                nameleft=find_seq("Insured's Name")
                nameright=find_seq('Issue Office Name')
                if nameleft and nameright:
                    ly=min(z[1] for z in nameleft); ry=min(z[1] for z in nameright)
                    # value x begins at approx 20% page width, right column at 63%
                    left=region_rows(page,W*.195,W*.49,ly-3,ly+39)
                    right=region_rows(page,W*.61,W*.99,ry-3,ry+35)
                    # remove unrelated rows; stop before address / next field
                    if left:
                        val=' '.join(x for x in left if not re.search(r'\b(?:GSTIN|\d{2}[A-Z]{5}\d{4})',x,re.I))
                        # only first 2 logical lines; GSTIN typically on 2nd
                        left_names=[]
                        for line in left:
                            if 'GSTIN' in line.upper():
                                prefix=line.split('(GSTIN')[0].strip()
                                if prefix:left_names.append(prefix)
                                break
                            left_names.append(line)
                        put('Insured Name',' '.join(left_names),pn,'Insured\'s Name: '+' '.join(left),'column')
                    if right:
                        right_names=[]
                        for line in right:
                            if 'GSTIN' in line.upper():
                                prefix=re.split(r'\(?GSTIN',line,flags=re.I)[0].strip()
                                if prefix:right_names.append(prefix)
                                break
                            right_names.append(line)
                        put('Issue Office Name',' '.join(right_names),pn,'Issue Office Name: '+' '.join(right),'column')
                # Address via side-by-side column geometry anchored on Address labels
                adr_candidates=[w for w in words if w[4].lower().strip(':')=='address' and 0<w[1]<page.rect.height*.46]
                adr_left=[w for w in adr_candidates if w[0]<W*.20]
                adr_right=[w for w in adr_candidates if W*.45<w[0]<W*.6]
                if adr_left and adr_right:
                    y0=min(adr_left[0][1],adr_right[0][1]);
                    # next section Tel/Fax roughly below addresses, derive from word positions
                    tel=[w[1] for w in words if re.match(r'^(?:tel\.?|phone|fax|e-?mail|pan|gstin)',w[4],re.I) and w[1]>y0+3]
                    yend=min(tel) if tel else y0+105
                    leftparts=region_rows(page,W*.195,W*.49,y0-2,yend-2)
                    rightparts=region_rows(page,W*.61,W*.99,y0-2,yend-2)
                    put('Insured Address',clean_address(leftparts),pn,'Left Address: '+' | '.join(leftparts),'column')
                    put('Issue Office Address',clean_address(rightparts),pn,'Right Address: '+' | '.join(rightparts),'column')
                # GSTIN values contextual by x
                for w in words:
                    if re.fullmatch(r'\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z0-9]{2}\)?',w[4],re.I):
                        field='Insured GSTIN' if w[0]<W*.5 else 'Issue Office GSTIN'
                        put(field,w[4].strip(')'),pn,w[4],'column')
                # TPA address (single column); locate TPA Address heading, capture next row(s) to toll-free or phone
                ta=find_seq('TPA Address')
                if ta:
                    sy=ta[0][1]
                    r=region_rows(page,W*.19,W*.59,sy-2,sy+48)
                    r=[z for z in r if not re.search(r'^(?:toll\s+free|fax\s+no|telephone)',z,re.I)]
                    put('TPA Address',clean_address(r),pn,'TPA Address: '+' | '.join(r),'column')
                # Some insurers use 'Office Code: TRICHY BR II (730901)'
                if not result['Issue Office Code']['value']:
                    om=re.search(r'\bOffice\s+Code\s*:\s*([^\n]+)',text,re.I)
                    if om:
                        put('Issue Office Code', om.group(1), pn, om.group(0), 'office code label')
                # Sum insured may appear in words rather than figures
                if not result['Sum Insured']['value']:
                    mm=re.search(r'Total\s+Sum\s+Insured\s+in\s+words\s*:\s*([^\n]+)',text,re.I)
                    if mm:
                        put('Sum Insured',mm.group(1),pn,mm.group(0),'amount in words')
                # TPA name/id values may be on next line rather than in row
                for fld,seq in [('TPA Name','TPA Name'),('TPA ID','TPA ID')]:
                    if result[fld]['value']:continue
                    hdr=find_seq(seq)
                    if hdr:
                        vals=region_rows(page,W*.19,W*.59,hdr[0][1]-3,hdr[0][1]+17)
                        if vals:put(fld,vals[0],pn,seq+': '+vals[0],'column')
                # emails by column
                for w in words:
                    if '@' in w[4] and '.' in w[4]:
                        fld='Insured Email' if w[0]<W*.5 else 'Office Email'
                        put(fld,w[4],pn,w[4],'column')
                # insurer company is explicitly listed, not just product name
                if re.search(r'The Oriental Insurance Company Limited',text,re.I):
                    put('Insurer Name','The Oriental Insurance Company Limited',pn,'The Oriental Insurance Company Limited','text')
            # fallback regex for TPA and main names for scanned PDF
            for k,pat in [('Insured Name',r"insured(?:'s)?\s*name\s*[:=-]\s*([^\n]{3,100})"),
                          ('Issue Office Name',r'issue\s*office\s*name\s*[:=-]\s*([^\n]{3,100})')]:
                if not result[k]['value']:
                    for line in lines:
                        m=re.search(pat,line,re.I)
                        if m:put(k,m.group(1),pn,line,'regex')
        if tax_parts:
            total=sum(a for a,_,_ in tax_parts.values())
            src=' | '.join(f'{k}: {row}' for k,(_,_,row) in tax_parts.items())
            first_page=min(p for _,p,_ in tax_parts.values())
            result['GST Amount']={
                'value':fmt_money(total), 'page':first_page,
                'evidence':src, 'method':'sum of CGST + SGST + IGST'
            }
        else:
            # Explicit standalone GST value, NOT SGST/CGST/IGST or GSTIN.
            for pi,lines in enumerate(page_lines,1):
                for row in lines:
                    m=re.search(r'(?<![A-Za-z])GST\s*(?:amount)?\s*[:=-]\s*(?:Rs\.?|₹|`)?\s*([\d,]+(?:\.\d+)?)\b',row,re.I)
                    if m:
                        put('GST Amount',m.group(1),pi,row,'explicit GST total')
                        break
                if result['GST Amount']['value']:break
            # 'towards premium and GST of `132919' is also an explicit total.
            if not result['GST Amount']['value']:
                for pi,lines in enumerate(page_lines,1):
                    for row in lines:
                        m=re.search(r'\bGST\s+of\s*[₹`]?\s*([\d,]+)\b',row,re.I)
                        if m:
                            put('GST Amount',m.group(1),pi,row,'explicit GST amount')
                            break
                    if result['GST Amount']['value']:break
        from proposal_fields import extract_proposal
        proposal_records = extract_proposal(pdf_bytes)
        if proposal_records:
            # This is an application/proposal, NOT an issued policy schedule.
            # Prevent a previous policy number or office-use premium being reported as issued policy details.
            for field in ('Policy Number','GST Amount','CGST Amount','SGST Amount','IGST Amount'):
                result[field]={'value':None,'page':None,'evidence':'','method':'not specified in proposal'}
        return {'fields':result,'pages':page_text,'modes':page_modes,'page_count':len(page_text),
                'proposal_records':proposal_records}
    finally:doc.close()


# Question matching deliberately uses whole words: GST != GSTIN != IGST.
# Never route unknown trailing words (e.g. "GST innu") to the GST field.
QUESTION_STOPWORDS = {
    'what','which','where','is','are','the','a','an','of','for','in','on','to',
    'show','give','get','find','tell','me','please','my','this','that','from',
    'pdf','document','policy','value','values','field','fields','details',
    'amount','number','no','enaku','enna','sollu','kudu','showme'
}

# Phrases accepted as structured questions. These are checked on token
# boundaries, from longest / most specific to shortest.
QUESTION_ALIASES = {
    **ALIASES,
    'gstin':'ALL_GSTIN',
    'gstin uin':'ALL_GSTIN',
    'gst numbers':'ALL_GSTIN',
    'gst number':'ALL_GSTIN',
    'tax registration number':'ALL_GSTIN',
    'all addresses':'ADDRESSES',
    'addresses':'ADDRESSES',
    'all names':'NAMES',
    'premium':'PREMIUMS',
    'tax':'TAXES',
    'taxes':'TAXES',
    'start and end dates':'DATES',
    'policy dates':'DATES',
    'insured gstin':'Insured GSTIN',
    'insured gst number':'Insured GSTIN',
    'issuing office gstin':'Issue Office GSTIN',
    'issue office gstin':'Issue Office GSTIN',
    'office gstin':'Issue Office GSTIN',
    'insurer gstin':'Issue Office GSTIN',
    'issue office code':'Issue Office Code',
    'office code':'Issue Office Code',
    'issuing office code':'Issue Office Code',
    'gst amount':'GST Amount',
    'gst':'GST Amount',
}

def _query_tokens(s):
    return re.findall(r'[a-z0-9]+', s.lower())

def _alias_tokens(alias):
    return _query_tokens(alias)

def _span_positions(haystack, needle):
    n=len(needle)
    return [i for i in range(len(haystack)-n+1) if haystack[i:i+n]==needle]

def answer_question(query, result):
    """Return (label, field-info) rows or exact source lines; no guessed answers.

    Exact field intent resolves to structured values. Unsupported/ambiguous
    questions are never coerced to a substring alias.
    """
    words=_query_tokens(query)
    if not words:
        return []
    # Disallow invented suffix words after a legitimate field name.
    # Match a phrase, then ensure every other non-stopword is known.
    aliases=sorted(QUESTION_ALIASES.items(), key=lambda kv: -len(_alias_tokens(kv[0])))
    found=[]
    used=set()
    for alias,field in aliases:
        pattern=_alias_tokens(alias)
        if not pattern: continue
        for start in _span_positions(words,pattern):
            positions=set(range(start,start+len(pattern)))
            if positions & used: continue
            found.append((field,positions))
            used |= positions
            break
    residual=[t for i,t in enumerate(words) if i not in used and t not in QUESTION_STOPWORDS]
    if found and not residual:
        categories={
            'ALL_GSTIN':['Insured GSTIN','Issue Office GSTIN'],
            'ADDRESSES':['Insured Address','Issue Office Address','TPA Address'],
            'NAMES':['Insured Name','Issue Office Name','TPA Name','Nominee Name','Insurer Name'],
            'PREMIUMS':['Gross Premium','Total Premium'],
            'TAXES':['GST Amount','CGST Amount','SGST Amount','IGST Amount'],
            'DATES':['Start Date','End Date','Cover Note Date'],
        }
        labels=[]
        for field, _ in found:
            for label in categories.get(field,[field]):
                if label not in labels: labels.append(label)
        return [(label,result['fields'][label]) for label in labels if label in result['fields']]
    # For arbitrary PDF labels, return precisely matching *source text*, never
    # an unrelated structured value. Requiring each content token prevents GSTIN
    # being treated as GST, and prevents malformed questions being force-matched.
    tokens=[t for t in words if t not in QUESTION_STOPWORDS]
    if not tokens:
        return []
    hits=[]
    for pi,page in enumerate(result['pages'],1):
        for line in page.splitlines():
            line_tokens=_query_tokens(line)
            if all(t in line_tokens for t in tokens):
                hits.append((pi,tidy(line)))
                if len(hits)>=15: return hits
    return hits
