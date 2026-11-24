"""Conservative supplemental table discovery on every PDF page.

Preserves original pipeline output; never assumes alternating cells are
field/value pairs. Uncertain associations are emitted as review candidates.
"""
from geometry_all_pages import extract_geometry_all_pages


def extract_small_table_fields(pdf_bytes):
    rows, _ = extract_geometry_all_pages(pdf_bytes)
    results = []
    seen = set()
    for row in rows:
        field = str(row.get('Field', '')).strip()
        value = str(row.get('Value', '')).strip()
        if not field or not value:
            continue
        k = (field.casefold(), value.casefold(), row.get('Page'))
        if k in seen:
            continue
        seen.add(k)
        rec = dict(row)
        # A table-cell box alone does not make a label/value match verified.
        rec['Review'] = True
        results.append(rec)
    return results
