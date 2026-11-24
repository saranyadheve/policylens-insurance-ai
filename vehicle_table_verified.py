"""Source-backed motor vehicle field extraction for native PDF tables.

Works with alternating label/value table rows and horizontal header/value tables.
All values are read from the PDF, never fixed. Stores a PDF-point BBox for
precise highlighting. Does not run on policy wording/depreciation tables.
"""
from __future__ import annotations
import re
import pymupdf

NORM = lambda s: re.sub(r'[^a-z0-9]+', '', str(s or '').lower())

ALIASES = {
    'registrationnumber': 'Registration Number',
    'registrationno': 'Registration Number',
    'registrationmarkno': 'Registration Number',
    'regno': 'Registration Number',
    'registrationdate': 'Registration Date',
    'rtaname': 'RTA Name',
    'engine number': 'Engine Number',
    'enginenumber': 'Engine Number',
    'obsoletevehicleenginenumber': 'Engine Number',
    'engineno': 'Engine Number',
    'chassisnumber': 'Chassis Number',
    'chassisno': 'Chassis Number',
    'vehiclemakemodel': 'Vehicle Make & Model',
    'makemodel': 'Vehicle Make & Model',
    'make': 'Make',
    'model': 'Model',
    'yearofmanufacture': 'Year of Manufacture',
    'manufacturingyear': 'Year of Manufacture',
    'cubiccapacity': 'Cubic Capacity',
    'hp cubiccapacity': 'Cubic Capacity',
    'carryingcapacity': 'Carrying Capacity',
    'seatingcapacity': 'Seating Capacity',
    'gvw': 'GVW',
    'typeofbodyfueltypebustype': 'Type of Body / Fuel Type / Bus Type',
    'fueltype': 'Fuel Type',
    'bodytype': 'Body Type',
    'totalidv': 'Total IDV',
    'vehicle': 'Vehicle IDV',
    'total': 'Total IDV',
    'vehicleidv': 'Vehicle IDV',
    'insureddeclaredvalue': 'Vehicle IDV',
    'trailer': 'Trailer IDV',
    'electricalelectronicaccessories': 'Electrical Accessories IDV',
    'nonelectricalaccessories': 'Non-Electrical Accessories IDV',
    'cngkit': 'CNG Kit IDV',
    'lpgkit': 'LPG Kit IDV',
    'coinsurancedetails': 'Co-Insurance Details',
}
ALIASES = {NORM(k):v for k,v in ALIASES.items()}
VEHICLE_KEYWORDS = ('registration number','registration no','engine no','engine number','chassis no',
                    'chassis number','vehicle make','make/model','vehicle idv','insured declared value')


def clean(s):
    return ' '.join(str(s or '').split()).strip(' :')


def value_bbox(page, table, row_no, col_no, value):
    """Keep the entire source cell as reliable fallback for multiline values.
    Prefer the actual text bounds within that cell when available.
    """
    try:
        rect = pymupdf.Rect(table.rows[row_no].cells[col_no])
        matches = page.search_for(value)
        inside = [m for m in matches if rect.intersects(m)]
        if inside:
            combined = pymupdf.Rect(inside[0])
            for m in inside[1:]: combined |= m
            return [round(float(x),2) for x in combined]
        # Native table provides defensible cell boundaries even for a value spanning lines.
        return [round(float(x),2) for x in rect]
    except (IndexError, TypeError, ValueError):
        return None


def record(label, value, page_no, bbox, context):
    return {
        'Field': label, 'Value': clean(value), 'Page': page_no,
        'Evidence': f'{context}: {label} = {clean(value)}'[:250],
        'Person': '', 'Method': 'vehicle table geometry', 'BBox': bbox,
    }


def output_pair(page, table, pageno, rowno, label_col, value_col, label, value, context):
    field = ALIASES.get(NORM(label))
    if not field or not clean(value): return []
    value = clean(value)
    if value.upper() in {'N/A','NA','NIL','NONE','-'}:return []
    bbox = value_bbox(page,table,rowno,value_col,value)
    result = []
    if 'obsolete' in NORM(label) and 'engine' in NORM(label):
        # This particular combined header has 'No & <engine>' in its cell.
        # Keep only source-backed engine number, and not 'No &'.
        m = re.search(r'\b([A-Z0-9]{7,24})\s*$', value, re.I)
        if m:
            val = m.group(1)
            b = page.search_for(val)
            if b:bbox = [round(float(x),2) for x in b[0]]
            result.append(record('Engine Number',val,pageno,bbox,context))
            return result
    result.append(record(field,value,pageno,bbox,context))
    if field == 'Type of Body / Fuel Type / Bus Type':
        pieces=[clean(x) for x in value.split('/')]
        if len(pieces)>1 and pieces[1]:
            fr=page.search_for(pieces[1]); fb=[round(float(x),2) for x in fr[0]] if fr else bbox
            result.append(record('Fuel Type',pieces[1],pageno,fb,context))
        if pieces and pieces[0]:
            br=page.search_for(pieces[0]); bb=[round(float(x),2) for x in br[0]] if br else bbox
            result.append(record('Body Type',pieces[0],pageno,bb,context))
    return result


def vehicle_records(pdf_bytes, max_pages=20):
    """Read vehicle details from relevant policy schedule tables only.

    Preserves exact page and PDF source cell coordinates; no fixed vehicle values.
    """
    result=[]; seen=set()
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as doc:
        for pi,page in enumerate(doc):
            if pi >= max_pages:break
            # Cheap page-level gate; skip policy wording and generic depreciation tables.
            text = page.get_text('text')
            tnorm = text.lower()
            if not any(k in tnorm for k in VEHICLE_KEYWORDS):continue
            try: tables=page.find_tables().tables
            except Exception: continue
            for table in tables:
                try: rows=table.extract()
                except Exception:continue
                if not rows or table.col_count < 2: continue
                preview=' '.join(clean(c).lower() for r in rows[:4] for c in r)
                if not any(k in preview for k in ('registration number','registration no','engine number','chassis number','vehicle make','vehicle idv','insur', 'electrical/electronic accessories')):
                    continue
                header = [clean(c) for c in rows[0]]
                second = [clean(c) for c in rows[1]] if len(rows)>1 else []
                heading_count = sum(bool(ALIASES.get(NORM(h))) for h in header)
                second_heading_count = sum(bool(ALIASES.get(NORM(h))) for h in second)
                is_header_table = (heading_count >= 2 and second_heading_count == 0
                                   and len(header) == len(second))
                # Layout A: label | value | label | value | ... within each row
                # 2,4,6,8-column native PDF tables all supported.
                for i,row in enumerate(rows):
                    if is_header_table:break
                    cells=[clean(c) for c in row]
                    if len(cells)>=2:
                        for col in range(0,len(cells)-1,2):
                            if ALIASES.get(NORM(cells[col])):
                                result += output_pair(page,table,pi+1,i,col,col+1,cells[col],cells[col+1],'Vehicle details table')
                # Layout B: column headings followed by one or more value rows
                if is_header_table:
                    head=header
                    if heading_count>=2:
                        for r_i in range(1,min(3,len(rows))):
                            values=[clean(x) for x in rows[r_i]]
                            for col,(label,value) in enumerate(zip(head,values)):
                                if ALIASES.get(NORM(label)) and value:
                                    result += output_pair(page,table,pi+1,r_i,col,col,label,value,'Vehicle value table')
    for r in result:
        key=(r['Field'].lower(),r['Value'].lower(),r['Page'])
        if key not in seen:
            seen.add(key);yield r
