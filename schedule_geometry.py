"""Evidence-first PDF schedule reader.

Extracts labelled cells in native PDF using word coordinates. Labels are
field hints, but values are read from the source at runtime, never hardcoded.
"""
import re
import pymupdf
from table_cache import table_rows

DATE=r'(?:\d{1,2}[-/][A-Z]{3}[-/]\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})'
DATE_RE=re.compile(DATE,re.I)
RANGE_RE=re.compile(r'('+DATE+r')\s*(?:\([^)]*\))?\s*(?:to|till|through|–|-)\s*('+DATE+r')',re.I)
LABELS = {
 'Policy Number':['Policy No','Policy Number'],
 'Insured Name':['Insured Name', 'Name of Insured', 'Insured\'s Name'],
 'Policyholder Name':['Policyholder Name','Name of the Policyholder','Customer Name'],
 'Insured Address':['Insured Add.', 'Insured Address','Insured\'s Address','Address of Insured'],
 'Insurer Name':['Servicing Office of Insurer', 'Insurer Name','Name of Insurer'],
 'Policy Start Date':['Period of Own Damage','Period of Insurance','Period of Liability Cover','Policy Period','Tenure','Risk Period'],
 'Policy End Date':['Period of Own Damage','Period of Insurance','Period of Liability Cover','Policy Period','Tenure','Risk Period'],
 'Total Premium':['Total Premium (A+B)','Total Premium Payable','Total Premium','Premium Paid'],
 'Gross Premium Paid':['Gross Premium Paid','Gross Premium'],
 'Sum Insured':['Sum Insured','Total Sum Insured','Total IDV','Vehicle IDV'],
 'Policy Issued On':['Policy Issued On','Issue Date','Date of Issue'],
 'Proposal Number':['Proposal No.', 'Proposal Number'],
 'Previous Policy Number':['Previous Policy No.', 'Previous Policy Number'],
 'Previous Insurer':['Previous Insurer'],
 'Nominee Name':['Nominee Name'], 
}
def make(field,value,page,evidence,status='found'):
    return dict(Field=field,Value=str(value).strip(),Page=page,Evidence=evidence[:250],Person='',Method='schedule geometry')

def row_words(words,rect,page_width):
    # Same baseline as searched label. Page-relative horizontal distance.
    return [w for w in words if abs(w[1]-rect.y0)<3.5 and w[0]>=rect.x1-0.5 and w[0]<page_width-10]

def fragment(words,rect,width,limit=None):
    row=sorted(row_words(words,rect,width),key=lambda z:z[0])
    if limit is None:limit=width
    return ' '.join(w[4] for w in row if w[0]<limit).strip()

def schedule_records(pdf_bytes):
    records=[]; seen=set()
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as doc:
        for pi,page in enumerate(doc):
            # Long policy wordings, legal clauses, and annexures are not primary policy schedules.
            if pi>12:break
            words=page.get_text('words')
            if not words:continue
            width=page.rect.width
            half=width*.5
            # Native page schedule normally has two column blocks. Avoid crossing them.
            for field,aliases in LABELS.items():
                for alias in aliases:
                    occurrences=page.search_for(alias)
                    for rect in occurrences[:5]:
                        if rect.y0>page.rect.height*.80:continue
                        # Reject labels occurring inside a longer label (Previous Policy No.)
                        # or within policy wording rather than the policy schedule header.
                        if field in ('Policy Number','Insured Name','Insured Address'):
                            if rect.y0>page.rect.height*.36:continue
                            preceding=[w[4].lower().strip('.:') for w in words if abs(w[1]-rect.y0)<3.5 and w[2]<=rect.x0+1 and rect.x0-w[2]<48]
                            if field=='Policy Number' and 'previous' in preceding:continue
                            if field=='Insured Name' and (rect.x0>page.rect.width*.35):continue
                        limit=half-5 if rect.x0<half*.70 else width-8
                        # A label near half may still be right column.
                        if rect.x0>half*.70:limit=width-8
                        value=fragment(words,rect,width,limit)
                        if field in ('Policy Start Date','Policy End Date'):
                            m=RANGE_RE.search(value)
                            if not m:continue
                            value=m.group(1) if field=='Policy Start Date' else m.group(2)
                        elif field in ('Total Premium','Gross Premium Paid'):
                            m=re.search(r'(?:Rs\.?\s*)?[\d,]+(?:\.\d{1,2})?',value)
                            if not m:continue
                            value=m.group().strip()
                        elif field=='Sum Insured':
                            if alias in ('Total IDV','Vehicle IDV'):
                                # These are motor vehicle declared values, not universal sum insured.
                                continue
                            if not re.search(r'\d',value):continue
                        elif field=='Insured Address':
                            if len(value)<6:continue
                            xstart=rect.x1+1
                            # Address continuation lines must begin at same value column;
                            # stop before next named field.
                            vals=[value]
                            for j in range(1,4):
                                y=rect.y0+8.4*j
                                c=[w for w in words if abs(w[1]-y)<3.4 and xstart-5 <= w[0]<limit]
                                if c:
                                    extra=' '.join(w[4] for w in sorted(c,key=lambda z:z[0]))
                                    if re.search(r'(?i)\b(?:policy no|period of|nominee|premium|mobile|tel\.|previous insurer)\b',extra):break
                                    # A new left-column label means the address has ended.
                                    labels=[w for w in words if abs(w[1]-y)<3.4 and w[0]<xstart-15]
                                    if labels:break
                                    vals.append(extra)
                            value=' '.join(vals)
                        elif field=='Policy Number':
                            value=value.strip(' :,;')
                            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9/-]{5,}',value):continue
                        elif field=='Insurer Name':
                            # "Servicing Office of Insurer" describes office, not company identity.
                            if alias=='Servicing Office of Insurer':continue
                            value=value[:110]
                        elif field=='Policy Issued On':
                            m=re.search(DATE+r'(?:\s*\(\d{1,2}:\d{2}\))?',value,re.I)
                            if not m:continue
                            value=m.group()
                        elif field=='Proposal Number':
                            value=re.sub(r'(?i)^\s*(?:&\s*date\s*)','',value)
                            value=value.split(',')[0].strip()
                        elif field in ('Previous Policy Number','Previous Insurer','Nominee Name'):
                            value=value.split('  ')[0].strip()
                        elif field=='Insured Name':
                            value=re.split(r'(?i)\b(?:previous insurer|period of|policy number)\b',value)[0]
                        if not value or len(value)>190:continue
                        if field in ('Insured Name','Policyholder Name') and (len(value)<3 or len(value)>95):continue
                        key=(field,value.lower(),pi+1)
                        if key not in seen:
                            seen.add(key);records.append(make(field,value,pi+1,f'{alias}: {value}'))
            # If a date range is printed as a single "Tenure ..." line,
            # catch it even when words break the nearby bounding box.
            for line in page.get_text('text',sort=True).splitlines():
                if re.match(r'(?i)^\s*(?:tenure|period of own damage|period of liability cover|period of insurance)\b',line):
                    m=RANGE_RE.search(line)
                    if m:
                        for f,v in [('Policy Start Date',m.group(1)),('Policy End Date',m.group(2))]:
                            key=(f,v.lower(),pi+1)
                            if key not in seen:seen.add(key);records.append(make(f,v,pi+1,line))
            # Multi-column table: header row followed by its values.
            # Works for vehicle make/model/engine number and other unknown columns.
            try:
                for rows in table_rows(page,30):
                    for i in range(len(rows)-1):
                        head=[' '.join(str(v or '').split()) for v in rows[i]]
                        vals=[' '.join(str(v or '').split()) for v in rows[i+1]]
                        if len(head)<4 or len(head)!=len(vals):continue
                        # Avoid using premium explanatory tables as field-name rows.
                        if sum(bool(v) for v in head)<3 or sum(bool(v) for v in vals)<3:continue
                        if any(len(x)>60 for x in head):continue
                        # Header labels are descriptive, next row should have
                        # at least two values/IDs; no formatting assumptions.
                        if sum(bool(re.search(r'\d',v)) for v in vals)<2:continue
                        if sum(bool(v) and len(v.split())>=8 for v in vals)>1:continue
                        if sum(bool(re.search(r'\d',v)) for v in head)>1:continue
                        for h,v in zip(head,vals):
                            if not h or not v or len(h)>55 or len(v)>95:continue
                            if len(h.split())>8 or h.lower() in ('age of the vehicle','% of depreciation'):continue
                            if h.lower()==v.lower():continue
                            key=(h.lower(),v.lower(),pi+1)
                            if key not in seen:
                                seen.add(key)
                                records.append(make(h,v,pi+1,f'Table column {h}: {v}'))
            except Exception:
                pass
            # Select issuer only from a document header, not office mailing address.
            top=[w[4] for w in words if w[1]<page.rect.height*.09]
            toptext=' '.join(top)
            m=re.search(r'(?i)(?:The New India Assurance Co\.?\s*Ltd\.?|Life Insurance Corporation of India|United India Insurance Company Limited|Oriental Insurance Company Limited)',toptext)
            if m:
                value=m.group()
                key=('Insurer Name',value.lower(),pi+1)
                if key not in seen:
                    seen.add(key);records.append(make('Insurer Name',value,pi+1,'Document header: '+value))
    return records
