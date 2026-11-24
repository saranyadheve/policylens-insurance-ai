"""Exhaustive, source-grounded PDF table cells for PolicyLens.

No insurance-type-specific layout restriction, page filter or arbitrary field cap.
Returns a candidate only when a real source table contains a label and value;
records retain page and source-cell PDF coordinates for review/highlighting.
"""
from __future__ import annotations
import re
import pymupdf
from table_cache import table_rows

BAD_VALUES={'','na','n/a','nil','none','not applicable','-','--'}
BAD_FIELDS={'','-', 'yes','no','na','n/a'}
PERSON=re.compile(r'(?:\d+(?:st|nd|rd|th)\s*)?(?:insured\s*person|member|dependent|life\s*assured)\b',re.I)
DATE_LABEL=re.compile(r'(date of birth|\bdob\b)',re.I)
DATE=re.compile(r'(?<!\d)\d{1,2}[/-]\d{1,2}[/-]\d{4}(?!\d)')


def tidy(x):
    return ' '.join(str(x or '').replace('\u00a0',' ').split()).strip(' :')


def norm(x):
    return re.sub(r'[^a-z0-9]', '', tidy(x).lower())


def valid_label(label):
    label=tidy(label)
    if not (2<=len(label)<=100):return False
    if label.lower() in BAD_FIELDS:return False
    if not re.search('[A-Za-z]',label):return False
    if len(label.split())>15:return False
    if len(label)>60 and re.search(r'(?i)\b(?:the|shall|would|should|provided|whose|under|for the|as per)\b',label):return False
    return True


def valid_value(value):
    value=tidy(value)
    return bool(value and value.lower() not in BAD_VALUES and len(value)<=12000 and not re.fullmatch(r'[,;:.]+',value))


def cell_box(table,ri,ci):
    try:
        rect=table.rows[ri].cells[ci]
        if rect:
            return [round(float(v),2) for v in rect]
    except (IndexError,ValueError,TypeError,AttributeError):pass
    return None


def extract_every_table(pdf_bytes,max_pages=None,max_tables_per_page=100):
    output=[];seen=set()
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as pdf:
        for pi,page in enumerate(pdf):
            if max_pages is not None and pi>=max_pages:break
            # One table discovery per page; surrounding content, not insurance type,
            # controls how each table is interpreted.
            try: tables=page.find_tables().tables[:max_tables_per_page]
            except Exception:tables=[]
            for ti,table in enumerate(tables):
                try:rows=table.extract()
                except Exception:continue
                if not rows or table.col_count<2:continue
                rows=[[tidy(c) for c in row] for row in rows]
                col_n=max(len(row) for row in rows)
                header_row=next((i for i,r in enumerate(rows[:5]) if sum(bool(PERSON.search(v)) for v in r)>=1),None)
                def add(field,value,row_idx,val_col,method,person='',review=False):
                    field=tidy(field);value=tidy(value)
                    if not valid_label(field) or not valid_value(value):return
                    if norm(field)==norm(value):return
                    # Never present damaged DOB as a real date.
                    if DATE_LABEL.search(field) and re.search(r'\d',value):
                        m=DATE.search(value)
                        if not m:return
                        if len(value)<32:value=m.group(0)
                    identity=(pi+1,ti,norm(field),norm(value),norm(person))
                    if identity in seen:return
                    seen.add(identity)
                    output.append({'Field':field,'Value':value,'Person':tidy(person),
                        'Page':pi+1,'BBox':cell_box(table,row_idx,val_col),
                        'Evidence':f'Table {ti+1}, {person+" | " if person else ""}{field}: {value}'[:450],
                        'Method':method,'Review':review})
                # Form tables: row name in first column, persons in columns 2..N.
                if header_row is not None:
                    headers=rows[header_row]
                    for ri in range(header_row+1,len(rows)):
                        row=rows[ri]
                        if not row:continue
                        label=row[0]
                        if not valid_label(label):continue
                        for ci in range(1,min(len(row),len(headers))):
                            person=headers[ci]
                            if PERSON.search(person):
                                add(label,row[ci],ri,ci,'verified person table',person=person)
                    # A second header can occur in the same table; other table methods
                    # deliberately don't process insured-person data again.
                    continue
                # Serial-numbered information sheet: [serial, field, description, clause].
                # It must not be read as [name,value,name,value].
                numbered=sum(bool(r and re.fullmatch(r'(?:\d{1,3}[.)]?|[A-E])',r[0]) and len(r)>=3 and valid_label(r[1])) for r in rows)
                if numbered>=1 and col_n>=3 and numbered>=max(1,len(rows)-2):
                    for ri,row in enumerate(rows):
                        if row and re.fullmatch(r'(?:\d{1,3}[.)]?|[A-E])',row[0]):
                            add(row[1],row[2],ri,2,'numbered table record')
                    continue

                def header_value_row(hi,vi):
                    """Detect columns where a header is directly over a cell value."""
                    h=rows[hi];v=rows[vi]
                    same=[i for i in range(min(len(h),len(v)))
                          if valid_label(h[i]) and valid_value(v[i])]
                    if len(same)<2:return False
                    # Values generally differ in shape/meaning from headers;
                    # do not mistake repeated row-wise label/value pairs for headers.
                    if len(h)<=8 and len(rows)>2:
                        return False
                    for ci in same:
                        add(h[ci],v[ci],vi,ci,'source column header')
                    return True

                # 2-row grids with multiple column headings (e.g. Motor IDV
                # 8-column table), or sparse/merged table sections (15 columns).
                matrix_rows=set()
                if len(rows)==2 and col_n>=3:
                    if header_value_row(0,1):matrix_rows.update({0,1})
                elif col_n>=9:
                    for hi in range(len(rows)-1):
                        h=rows[hi];v=rows[hi+1]
                        nheads=sum(valid_label(x) for x in h)
                        # Sparse, merged-cell header row with labels only in a few
                        # columns and values in matching columns directly below.
                        if nheads>=2 and (sum(bool(x) for x in h)<=6):
                            if header_value_row(hi,hi+1):
                                matrix_rows.update({hi,hi+1})

                # Alternating [field, value, field, value, ...] across every row.
                # No insurance category is assumed. Handle tiny 2-cell boxes.
                for ri,row in enumerate(rows):
                    if ri in matrix_rows:continue
                    if len(row)>=3 and re.fullmatch(r'\d{1,3}[.)]?',row[0]):
                        add(row[1],row[2],ri,2,'numbered table record')
                        continue
                    for ci in range(0,len(row)-1,2):
                        label,value=row[ci],row[ci+1]
                        if not valid_label(label) or not valid_value(value):continue
                        # Header-on-header pair with no data (e.g. 'Age of Vehicle'
                        # paired with '% of Depreciation'). Skip only these headings.
                        if ri==0 and len(rows)>1 and len(row)==2:
                            if valid_label(value) and re.search(
                                r'(?i)(?:age of|\bdescription\b|\bvalue\b|\brate\b|\btitle\b|\bpolicy clause\b|% of)',
                                label+' '+value):
                                continue
                        if ri==0 and len(row)>=4 and all(
                            valid_label(x) for x in row if x
                        ) and len(row)>2:
                            continue
                        add(label,value,ri,ci+1,'source cell pair')

                # Independent records inside a large multiline cell (e.g. the
                # three-column premium schedule). Extract printed label/amount
                # pairs without relying on neighbouring unrelated columns.
                money=re.compile(r'^\s*([A-Za-z][A-Za-z0-9+/% .()&\-]{2,85}?)\s+'+
                    r'((?:₹|Rs\.?\s*)?\d[\d,]*(?:\.\d{1,2})?%?)\s*$',re.I)
                for ri,row in enumerate(rows):
                    for ci,value in enumerate(row):
                        if not value or '\n' not in value:continue
                        for line in str(value).split('\n'):
                            line=tidy(line)
                            if len(line)>110:continue
                            m=money.match(line)
                            if m:
                                add(m.group(1),m.group(2),ri,ci,'multiline table cell',review=True)
    return output
