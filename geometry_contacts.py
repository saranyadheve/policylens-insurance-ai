"""Grounded form contacts from word positions (digital PDFs); no invented fields.
Special care: two-column schedules can contain insured and insurer office contacts
on the same row; only the insured column populates generic contact fields.
"""
import re
import pymupdf
from dynamic_fields import add

EMAIL = re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b')
MOBILE = re.compile(r'(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{9})(?!\d)')
# Preserve unexpanded slash suffixes (080-23160532/33/35) as printed.
LANDLINE = re.compile(r'(?<!\d)(?:0\d{2,4}[\s-]?)?\d{6,8}(?:/\d{2,8})*(?!\d)')
CONTACT = re.compile(r'(?i)\b(?:tel\.?|telephone|phone|mobile|contact|fax|e[- ]?mail)\b')
ADDR = re.compile(r'(?i)^\s*(?:address|insured(?:\x27s)? address|policyholder address|present address|permanent address|correspondence address)\s*:')
STOP = re.compile(r'(?i)\b(?:agent/broker|dev\.off|period of insurance|collection no|gross premium|tpa details|risk details|sum insured|policy no|cover note)\b')

def _lines(page):
    result=[]
    # Prefer native PDF words; blocks may cross multiple columns.
    for block in page.get_text('dict',sort=False).get('blocks',[]):
        if 'lines' not in block:continue
        for ln in block['lines']:
            spans=[s for s in ln['spans'] if s.get('text','').strip()]
            if not spans:continue
            text=' '.join(s['text'].strip() for s in spans)
            x0=min(s['bbox'][0] for s in spans)
            y0=min(s['bbox'][1] for s in spans)
            x1=max(s['bbox'][2] for s in spans)
            result.append((x0,y0,x1,text))
    return sorted(result,key=lambda v:(v[1],v[0]))

def _native_contacts(page, number, out, seen):
    lines=_lines(page)
    # Find two-column insurance schedule: repeated Address or Tel/Fax/Email on same baseline.
    addrs=[(x,y) for x,y,_,text in lines if re.match(r'(?i)^\s*address\s*$',text.strip(' :'))]
    contact_headers=[(x,y) for x,y,_,text in lines if re.search(r'(?i)^\s*(?:tel\.?\s*/?\s*fax\s*/?\s*email|phone\s*no\.?|e[- ]?mail\s*/?\s*fax)\s*$',text.strip(' :'))]
    if len(addrs)<2 and len(contact_headers)<2:
        return
    anchors = sorted(addrs or contact_headers,key=lambda a:a[0]);left_x,right_x=anchors[0][0],anchors[-1][0]
    if right_x-left_x<90:return
    boundary=(left_x+right_x)/2
    # First insured column begins before right address header; contact values may start at x=120.
    # Avoid including issuing office text x>=right_x.
    address_y=min((y for x,y in addrs if x<boundary),default=None)
    contact_y=min((y for x,y in contact_headers if x<boundary),default=None)
    if address_y is not None:
        limit = contact_y if contact_y and contact_y>address_y else address_y+95
        parts=[]
        for x,y,_,text in lines:
            if not (address_y-5<=y<limit-1 and left_x+55<=x<right_x-2):continue
            val=text.strip(' :\t')
            if not val or val in {'-',':','/'} or re.fullmatch(r'[-/\s]+',val):continue
            if STOP.search(val):continue
            if re.fullmatch(r'(?i)(?:address|:)',val):continue
            parts.append((y,x,val))
        parts.sort(key=lambda z:(z[0],z[1]))
        # Keep only address portion; header/addresses are in separate spans/lines.
        addr=' '.join(z[2] for z in parts)
        addr=re.sub(r'\s+',' ',addr).strip(' ,;')
        if len(addr)>=12 and len(addr)<=260:
            # Not a permanent address unless explicitly identified.
            add(out,seen,'Insured Address',addr,number,'Insured address (left column): '+addr,'insured address geometry')
    # Insured name often wraps onto another physical line within the left column.
    # Avoid concatenating GSTIN and issuing-office name into the legal entity name.
    name_y=min((y for x,y,_,t in lines if x<left_x+30 and re.match(r"(?i)^insured(?:'s)?\s+name$", t.strip(' :'))),default=None)
    if name_y is not None:
        cutoff=address_y-3 if address_y and address_y>name_y else name_y+38
        for x,y,_,t in lines:
            if x<right_x-5 and y>name_y+5 and re.match(r"(?i)^(?:insured(?:'s)? details|customer id|address|phone no|tel|policy|proposer)",t.strip()):
                cutoff=min(cutoff,y-2)
        chunks=[]
        for x,y,_,t in lines:
            if not (name_y-3<=y<cutoff-2 and left_x+55<=x<right_x-2):continue
            v=t.strip(' :')
            if re.search(r'(?i)GSTIN|\b[A-Z0-9]{15}\b',v):
                v=v.split('(')[0].strip()
                if re.fullmatch(r'[A-Z0-9]{15}\)?',v):continue
            if v and not v.startswith(':') and not re.fullmatch(r'[A-Z0-9]{15}',v):chunks.append((y,x,v))
        chunks.sort(key=lambda z:(z[0],z[1]))
        name=' '.join(a[2] for a in chunks).strip(' ,;')
        if len(name)>=5 and len(name)<125:
            add(out,seen,'Insured Name',name,number,'Insured name (left column): '+name,'insured name geometry')
    if contact_y is not None:
        limit= min(contact_y+49, page.rect.height-10)
        # Stop before the next non-contact label in insured column (e.g. PAN).
        for x,y,_,t in lines:
            if y>contact_y+18 and x<left_x+22 and re.search(r'(?i)^(?:pan\s*no|gstin|agent/broker(?:\s+details)?|policy|risk details|collection|period of insurance)$',t.strip()):
                limit=min(limit,y-1)
        values=[]
        for x,y,_,text in lines:
            if contact_y-1<=y<limit and left_x+55<=x<right_x-2:
                val=text.strip()
                if val not in {'-',':','/'}:values.append((y,x,val))
        values.sort(key=lambda z:(z[0],z[1]))
        evidence=' '.join(z[2] for z in values)
        # Some page blocks contain both columns in one span; crop word positions instead.
        if not evidence or not EMAIL.search(evidence):
            values2=[]
            for w in page.get_text('words'):
                x,y=w[:2];txt=w[4]
                if contact_y-2<=y<limit and left_x+55<=x<right_x-2:
                    values2.append((y,x,txt))
            values2.sort(key=lambda z:(round(z[0]/4),z[1]))
            evidence=' '.join(z[2] for z in values2)
        for email in EMAIL.findall(evidence):
            add(out,seen,'Email',email,number,'Insured contact: '+evidence[:220],'insured email geometry')
        for m in MOBILE.finditer(evidence):
            add(out,seen,'Mobile Number',m.group(1),number,'Insured contact: '+evidence[:220],'insured mobile geometry')
        masked = re.findall(r'(?i)(?:X{2,}\d{3,}(?:/{1,2}X{2,}\d{3,})*)', evidence)
        for v in masked:
            add(out,seen,'Phone Number',v,number,'Masked insured phone, full number not available: '+evidence[:220],'insured masked phone geometry')
        for m in LANDLINE.finditer(evidence):
            v=m.group()
            digits=re.sub(r'\D','',v)
            if MOBILE.fullmatch(v) or len(digits)<9:continue
            if re.search(r'(?<!\d)'+re.escape(v)+r'(?!\d)',evidence):
                add(out,seen,'Phone Number',v,number,'Insured contact: '+evidence[:220],'insured phone geometry')

def extract_contact_geometry(pdf_bytes, max_pages=20):
    out=[];seen=set()
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as doc:
        for i,p in enumerate(doc):
            if i>=max_pages:break
            if len(p.get_text().strip())<70:continue
            _native_contacts(p,i+1,out,seen)
    return out
