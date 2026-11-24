"""Page-complete table-field association from native PDF geometry.

Every page is inspected. Confident label/value associations are emitted with
source-cell rectangles. Uncertain or unpaired cells are kept separately for
review instead of being manufactured into misleading field names.
"""
import re
import pymupdf

DATE_HINT=re.compile(r'^(?:date|dob|birth|expiry|expiration|renewal|commencement)',re.I)
BAD={'','-', '–','na','n/a','nil','none','not applicable'}
LABEL_WORDS=re.compile(r'(?i)\b(?:policy|certificate|customer|insured|insurance|insurer|address|name|date|time|office|code|contact|telephone|mobile|phone|email|occupation|business|period|premium|tax|gst|cgst|sgst|igst|stamp|receipt|invoice|paid|payable|amount|number|no\.?|registration|rta|engine|chassis|vehicle|make|model|body|fuel|cubic|capacity|manufacture|year|gvw|carrying|financier|nominee|relation|age|appointee|declared|value|idv|trailer|electrical|accessor|cng|lpg|total|sub\s*total|cover|liability|deductible|discount|addon|additional|geographical|extension|sac|effective|start|end|proposal|sum\s*insured|title|description|claim|exclusions|warranties|obligations|benefit|interest|payment|mode|channel|agent|broker|document|product|uin|section|scope|depreciation|rate|component|gender|marital|pan|aadhaar|member|dependent|occupation|age\s*of)\b')
INVALID_LABEL_START=re.compile(r'(?i)^(?:the|this|there|such|provided|under|as per|for the|a\)|b\)|c\)|\d{4,})\b')
MONEY=re.compile(r'(?<!\w)(?:Rs\.?\s*|₹\s*)?-?\(?\d[\d,]*(?:\.\d{1,2})?\)?(?:\s*%)?(?!\w)')
DATE=re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b')


def tidy(value):
    return ' '.join(str(value or '').replace('\u00a0',' ').split()).strip(' :|')

def normalized(value):
    return re.sub('[^a-z0-9]+','',tidy(value).lower())

def valid_value(value):
    v=tidy(value)
    return bool(v and v.lower() not in BAD and len(v)<12000 and re.search(r'[a-zA-Z0-9]',v))

def label_like(value):
    s=tidy(value)
    if not (2<=len(s)<=96) or s.lower() in BAD or s.lower() in {'no','yes','none'}:return False
    if not re.search(r'[A-Za-z]',s) or len(s.split())>14:return False
    if INVALID_LABEL_START.match(s):return False
    if len(s)>56 and s.count(',')>1:return False
    # No free-text paragraphs masquerading as a short field label.
    if re.search(r'(?i)\b(?:is subject to|shall be|please contact|should be|which|provided that)\b',s):return False
    return bool(LABEL_WORDS.search(s))

def bbox(table,r,c):
    try:
        x=table.rows[r].cells[c]
        return [round(float(y),2) for y in x] if x else None
    except (AttributeError,IndexError,TypeError,ValueError):return None

def extract_geometry_all_pages(pdf_bytes, max_pages=None):
    records=[];unpaired=[];seen=set()
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as pdf:
        for pi,page in enumerate(pdf):
            if max_pages is not None and pi>=max_pages:break
            try:tables=page.find_tables().tables
            except Exception:tables=[]
            for ti,table in enumerate(tables):
                try:raw_rows=table.extract()
                except Exception:continue
                if not raw_rows or table.col_count<2:continue
                rows=[[tidy(v) for v in row] for row in raw_rows]
                cols=max(map(len,rows));used=set()
                def add(field,value,ri,ci,method,person='',review=False):
                    field=tidy(field);value=tidy(value)
                    if not label_like(field) or not valid_value(value):return False
                    if normalized(field)==normalized(value):return False
                    if label_like(value) and not (re.search(r'\d',value) or len(value)>60):return False
                    if DATE_HINT.search(field) and re.search(r'[0-9]',value) and re.search(r'\d{1,2}/\d{1,2}/',value) and not DATE.search(value):return False
                    ident=(pi,ti,normalized(field),normalized(value),normalized(person))
                    if ident in seen:return False
                    seen.add(ident)
                    records.append(dict(Field=field,Value=value,Person=person,Page=pi+1,
                        BBox=bbox(table,ri,ci),Evidence=f'Page {pi+1}, table {ti+1}, row {ri+1}, column {ci+1}: {field} = {value}'[:450],
                        Method=method,Review=review))
                    used.add((ri,ci))
                    return True
                # Person sheets: headers name persons, other rows are field names.
                person_header=None
                for hi,row in enumerate(rows[:6]):
                    if any(re.search(r'(?i)(?:\d+(?:st|nd|rd|th)\s*)?(?:insured\s*person|dependent\s*\d+|member\s*\d+|life\s*assured)',v) for v in row[1:]):
                        person_header=hi;break
                if person_header is not None:
                    headers=rows[person_header]
                    for ri in range(person_header+1,len(rows)):
                        row=rows[ri];label=row[0] if row else ''
                        if not label_like(label):continue
                        for ci in range(1,min(len(row),len(headers))):
                            if headers[ci] and valid_value(row[ci]):
                                add(label,row[ci],ri,ci,'person-column',person=headers[ci])
                    continue
                # Numbered summary tables: serial | title | description | clause.
                numbered=sum(bool(len(row)>=3 and re.fullmatch(r'(?:\d{1,3}[.]?|[A-E])',row[0]) and label_like(row[1])) for row in rows)
                if cols in (3,4) and numbered>=2 and numbered >= max(2,len(rows)//2):
                    for ri,row in enumerate(rows):
                        if len(row)>=3 and re.fullmatch(r'(?:\d{1,3}[.]?|[A-E])',row[0]):
                            add(row[1],row[2],ri,2,'numbered-field-description')
                            if len(row)>3 and row[3] and label_like(row[3]) is False:
                                # Policy clause is a separate column, not part of description.
                                add(row[1]+' — Policy Clause',row[3],ri,3,'numbered-clause',review=True)
                    continue
                # Header over value grids (including tiny 2-row tables).
                if len(rows)>=2 and cols>=3:
                    for hi in range(min(len(rows)-1,8)):
                        hdr=rows[hi];vals=rows[hi+1]
                        labels=[c for c,v in enumerate(hdr) if label_like(v)]
                        if len(labels)<2:continue
                        matching=[c for c in labels if c<len(vals) and valid_value(vals[c]) and not label_like(vals[c])]
                        # Header-row/value-row shape, not two normal form rows.
                        is_grid=(len(rows)==2 or cols>=8 or (len(labels)>=3 and len(matching)>=2 and not label_like(vals[0])))
                        if is_grid and len(matching)>=2:
                            for ci in matching:add(hdr[ci],vals[ci],hi+1,ci,'column-heading-value')
                # Row-wise with two or three field/value pairs, including sparse 19 cols.
                for ri,row in enumerate(rows):
                    if len(row)<2:continue
                    nonempty=[ci for ci,v in enumerate(row) if v]
                    if not nonempty:continue
                    # For compact 2,4,6-col tables labels at even indices.
                    if cols<=8 and cols%2==0:
                        # A table's all-heading row is not a label/value row.
                        if ri==0 and sum(label_like(x) for x in row)>=3 and not any(re.search(r'\d{2,}',x) for x in row):continue
                        for ci in range(0,len(row)-1,2):
                            if (ri,ci+1) in used:continue
                            add(row[ci],row[ci+1],ri,ci+1,'row-label-value')
                    # Handle sparse tables: use first value to right, stopping at next field label.
                    if cols>8:
                        for pos,ci in enumerate(nonempty):
                            field=row[ci]
                            if not label_like(field):continue
                            next_index=nonempty[pos+1] if pos+1<len(nonempty) else None
                            if next_index is None or next_index-ci>5:continue
                            value=row[next_index]
                            if label_like(value) and not re.search(r'\d',value):continue
                            add(field,value,ri,next_index,'sparse-row-label-value')
                    # Compact three-column form with label at 1 + value at 2.
                    if cols==3 and re.fullmatch(r'(?:\d{1,3}[.)]?|[A-E])',row[0]):
                        add(row[1],row[2],ri,2,'serial-label-value')
                    # Premium table may have multi-line label + value in same cell.
                    for ci,v in enumerate(row):
                        if not v:continue
                        for line in raw_rows[ri][ci].splitlines() if isinstance(raw_rows[ri][ci],str) else []:
                            line=tidy(line)
                            m=re.match(r'^(.{3,70}?)\s+((?:Rs\.?\s*)?\(?\d[\d,]*(?:\.\d{1,2})?\)?%?)$',line)
                            if m:add(m.group(1),m.group(2),ri,ci,'multiline-cell',review=True)
                # Any potentially meaningful source cell not confidently associated
                # is retained in a separate diagnostic review section, NOT faked as field.
                for ri,row in enumerate(rows):
                    for ci,v in enumerate(row):
                        if valid_value(v) and (ri,ci) not in used and len(v)<=240:
                            unpaired.append(dict(Page=pi+1,Table=ti+1,Row=ri+1,Column=ci+1,
                                Text=v,BBox=bbox(table,ri,ci)))
    return records,unpaired
