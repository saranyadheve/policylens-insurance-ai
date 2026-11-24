"""Cross-layout source-grounded extraction for high-value insurance fields.
All values are copied from PDF/OCR source. No fabricated values; ambiguous contacts get a
review status via the field resolver. This module is not a generative model.
"""
import re
import pymupdf
from dynamic_fields import add

D = r'(?<!\d)(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2}(?!\d)'
DR = re.compile(D)
EMAIL = re.compile(r'(?i)[\w.+-]+@[a-z0-9.-]+\.[a-z]{2,}')
MOBILE = re.compile(r'(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)')
PHONE = re.compile(r'(?<!\d)(?:0\d{2,4}[\s-]?)?\d{6,8}(?!\d)')
STOPDATE = re.compile(r'(?i)\b(?:date of birth|dob|proposal date|date of proposal|issue date|date of issue|signature|last claimed|last consultation|date of diagnosis)\b')
DATE_RANGE_LABEL = re.compile(r'(?i)\b(?:period of insurance|policy period|period of cover|policy validity|coverage required|insurance period|period of policy|risk period|period of risk)\b')
START_LABEL = re.compile(r'(?i)^\s*(?:policy start date|start date|policy inception date|inception date|risk start date|effective date|date of commencement(?: of (?:policy|risk|cover))?|commencement date|coverage start date|insurance start date|od start date|tp start date)\s*[:\-]?\s*')
END_LABEL = re.compile(r'(?i)^\s*(?:policy end date|end date|expiry date|policy expiry date|expiration date|policy expiration date|risk end date|date of expiry|valid upto|valid up to|valid till|coverage end date|insurance end date|od end date|tp end date)\s*[:\-]?\s*')


def record(out, seen, field, value, page, evidence, kind):
    v = ' '.join(str(value).split()).strip(' ,:;')
    if v:
        add(out,seen,field,v,page,evidence[:260],kind)


def extract_priority_fields(pdf_bytes, texts=None, max_pages=100):
    out=[]; seen=set()
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as doc:
        for pi,p in enumerate(doc):
            if pi>=max_pages: break
            text=(texts[pi] if texts and pi<len(texts) else p.get_text('text',sort=True)) or ''
            lines=text.splitlines()
            # Dates: same-row FROM ... TO; or next line for a wrapped policy period.
            for i,line in enumerate(lines):
                if DATE_RANGE_LABEL.search(line) and not STOPDATE.search(line):
                    block=' '.join(lines[i:i+3])[:420]
                    # Prefer labelled FROM / TO dates. A range with two dates is also valid.
                    dates=DR.findall(block)
                    if len(dates)>=2:
                        record(out,seen,'Policy Start Date',dates[0],pi+1,block,'policy-period evidence')
                        record(out,seen,'Policy End Date',dates[1],pi+1,block,'policy-period evidence')
                        continue
                # Dates on separate labelled lines. Do not confuse proposal, DOB or printed time.
                if START_LABEL.search(line):
                    m=DR.search(line)
                    if m: record(out,seen,'Policy Start Date',m.group(),pi+1,line,'explicit date label')
                if END_LABEL.search(line):
                    m=DR.search(line)
                    if m: record(out,seen,'Policy End Date',m.group(),pi+1,line,'explicit date label')
                if re.search(r'(?i)\b(?:annual renewal date|renewal date)\b',line):
                    m=DR.search(line)
                    if m: record(out,seen,'Renewal Date',m.group(),pi+1,line,'explicit renewal')
                # Named primary policyholder/person: don't take a whole mixed multi-column line.
                for label,field in [(r'(?i)^\s*(?:insured(?:\x27s)? name|name of insured|proposer name|name of proposer)\s*:', 'Insured Name'),
                                    (r'(?i)^\s*(?:name of the master policyholder|master policyholder name)\s*:?', 'Policyholder Name'),
                                    (r'(?i)^\s*(?:policy holder name|policyholder name|customer name|name of the policyholder)\s*:', 'Policyholder Name')]:
                    m=re.search(label,line)
                    if m:
                        value=line[m.end():].split('    ')[0].strip(' :')
                        if 3<=len(value)<=95 and not re.search(r'(?i)\b(?:address|phone|code|email|office)\s*:',value):
                            record(out,seen,field,value,pi+1,line,'explicit identity label')
                # Company and customer contacts must be source-backed, not inferred from arbitrary digits.
                for mail in EMAIL.findall(line):
                    if re.search(r'(?i)\b(?:email|e-mail|mail id|e-mail/fax)\b',line) or (len(lines)<80 and len(mail)>5):
                        record(out,seen,'Email',mail,pi+1,line,'email regex')
                # Only extract mobile number from an explicitly labeled mobile/contact field.
                if re.search(r'(?i)\b(?:mobile|contact\s*(?:no|number)|phone\s*(?:no|number)|tel\.?\s*no|telephone)\b',line):
                    for number in MOBILE.findall(line):
                        num=re.sub(r'\D','',number)
                        if len(num)==12 and num.startswith('91'):num=num[2:]
                        if len(num)==10: record(out,seen,'Mobile Number',num,pi+1,line,'labeled contact regex')
                    # Landline should not become a mobile number.
                    for number in PHONE.findall(line):
                        num=re.sub(r'\D','',number)
                        if 9<=len(num)<=12 and not re.fullmatch(r'[6-9]\d{9}',num):
                            record(out,seen,'Phone Number',number,pi+1,line,'labeled phone regex')
                # A standard two-column schedule may print two different Address labels.
                # Use the first address only when it appears in the insured-details section;
                # never promote the issuing office's second address to the customer's.
                if re.match(r'(?i)^\s*address\s*:',line) and len(line.split('Address'))>1:
                    fragments=re.split(r'(?i)\baddress\s*:',line)
                    first=fragments[1].strip(' :') if len(fragments)>1 else ''
                    if len(first)>7 and not re.search(r'(?i)\b(?:please|should|refer|terms|policy document)\b',first):
                        record(out,seen,'Insured Address',first,pi+1,line,'first policyholder address column')
                # Address: prioritize explicitly qualified insured/present/permanent labels.
                m=re.search(r'(?i)^\s*((?:present|permanent|insured(?:\x27s)?|policyholder|risk|correspondence|residential|registered)\s+address)\s*:\s*(.*)$',line)
                if m:
                    v=m.group(2).split('     ')[0].strip()
                    if v and len(v)>8:
                        field=('Present Address' if 'present' in m.group(1).lower() else
                               'Permanent Address' if 'permanent' in m.group(1).lower() else
                               'Risk Address' if 'risk' in m.group(1).lower() else 'Insured Address')
                        record(out,seen,field,v,pi+1,line,'qualified address label')
            # Look for clear two-column policy scheduling lines in spatial table cells.
            if len(text.strip())>=50:
                try:
                    for tab in p.find_tables().tables[:24]:
                        for row in tab.extract()[:200]:
                            if not row or len(row)<2:continue
                            cells=[' '.join(str(c or '').split()) for c in row]
                            if len(cells)>=3 and re.fullmatch(r'\d{1,3}[.)]?',cells[0]):cells=cells[1:]
                            label=cells[0].lower().strip(' :')
                            if not label:continue
                            value=' '.join(cells[1:]).strip()
                            ds=DR.findall(value)
                            if (label in {'period of insurance','policy period','coverage period','period of cover','policy validity'} and len(ds)>=2):
                                record(out,seen,'Policy Start Date',ds[0],pi+1,f'{label}: {value}','table period')
                                record(out,seen,'Policy End Date',ds[1],pi+1,f'{label}: {value}','table period')
                            elif re.fullmatch(r'(?:date of commencement of policy|policy start date|policy inception date|start date)',label) and ds:
                                record(out,seen,'Policy Start Date',ds[0],pi+1,f'{label}: {value}','table start')
                            elif re.fullmatch(r'(?:expiry date|policy expiry date|policy end date|end date)',label) and ds:
                                record(out,seen,'Policy End Date',ds[0],pi+1,f'{label}: {value}','table end')
                            elif label in {'name of the master policyholder','name of the policyholder'} and value and len(value)<120:
                                record(out,seen,'Policyholder Name',value,pi+1,f'{label}: {value}','table identity')
                except Exception:pass
    return out
