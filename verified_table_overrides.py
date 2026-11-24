"""Add source-checked motor policy schedule values without replacing the pipeline.

This is a narrow trust/priority layer. The original extractor continues to run
first and its unrelated records stay untouched. Page and BBox are retained.
"""
import re
from vehicle_table_verified import vehicle_records
from policy_schedule_verified import policy_schedule_records


def norm(text):
    return re.sub(r'[^a-z0-9]+', '', str(text or '').lower())


def checked(field, value):
    v = str(value or '').strip()
    if not v:
        return False
    if field == 'Engine Number':
        return (bool(re.fullmatch(r'[A-Za-z0-9-]{7,24}', v))
                and len(v) != 17 and bool(re.search('[A-Za-z]', v))
                and bool(re.search(r'\d', v)))
    if field == 'Chassis Number':
        return bool(re.fullmatch(r'[A-HJ-NPR-Za-hj-npr-z0-9]{17}', v))
    if field == 'Registration Number':
        return bool(re.search(r'\b[A-Z]{2}\s*-?\s*\d{1,2}\s*-?\s*[A-Z]{1,3}\s*-?\s*\d{3,4}\b',v,re.I))
    if field in {'Vehicle Make & Model'}:
        return len(v) > 8 and bool(re.search(r'[A-Za-z]{3,}', v)) and len(v.split()) >= 2
    if field in {'Year of Manufacture'}:
        return bool(re.fullmatch(r'(?:19|20)\d{2}',v))
    if field in {'Cubic Capacity','GVW','Carrying Capacity','Vehicle IDV','Total IDV'}:
        return bool(re.fullmatch(r'\d{1,10}',v))
    if field == 'Registration Date':
        return bool(re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}',v))
    return True


def as_result(record):
    return {
        'value': record['Value'], 'page': record.get('Page'),
        'bbox': record.get('BBox'), 'person': record.get('Person', ''),
        'evidence': record.get('Evidence', ''),
        'status': 'found' if record.get('BBox') else 'review',
    }


def apply_source_priority(pdf_bytes, common_fields, dynamic_fields, resolved):
    """Returns names to display as vehicle cards and an audit of corrected fields."""
    valid = []
    for item in vehicle_records(pdf_bytes, max_pages=100000):
        if checked(item['Field'], item['Value']):
            valid.append(item)
    if not valid:
        return [], []
    by_field = {}
    for record in valid:
        by_field.setdefault(record['Field'], record)

    updates = []
    names = []
    common = {norm(x) for x in common_fields}
    for field, source in by_field.items():
        if norm(field) in common:
            continue
        old = resolved.get(field)
        if not old or str(old.get('value')) != str(source['Value']):
            updates.append((field, old.get('value') if old else None, source['Value']))
        resolved[field] = as_result(source)
        if field not in dynamic_fields:
            dynamic_fields.append(field)
        names.append(field)

    # Correct familiar aliases from the same verified source, without
    # changing the original extraction algorithms.
    for alias, canonical in {
        'Make/Model': 'Vehicle Make & Model',
        "Insured'sDeclaredValue": 'Vehicle IDV',
        'Registration Authority': 'RTA Name',
    }.items():
        if alias in resolved and canonical in by_field:
            old = resolved[alias].get('value')
            source = by_field[canonical]
            if str(old) != str(source['Value']):
                updates.append((alias, old, source['Value']))
            resolved[alias] = as_result(source)

    # Report impossible header/header matches as uncertain, not verified.
    for name in ('Obsolete Vehicle', 'Description'):
        if name in resolved and norm(resolved[name].get('value')) in {'engineno','policyclause'}:
            resolved[name]['status'] = 'review'
            resolved[name]['evidence'] = 'A header was paired with another header; source review required.'

    # Explicit fields use verified underwriter/insured schedule values.
    for rec in policy_schedule_records(pdf_bytes, max_pages=100000):
        field = rec['Field']
        if field not in common_fields:
            continue
        if field == 'Sum Insured' and 'Total IDV' not in by_field:
            continue
        old = resolved.get(field)
        if not old or str(old.get('value')) != rec['Value']:
            updates.append((field, old.get('value') if old else None, rec['Value']))
        resolved[field] = as_result(rec)

    # Some motor policy PDFs mask insured phone but show the broker's number.
    # Do not misattribute a broker contact as insured's mobile.
    if any(rec['Field'] == 'Insured Mobile (masked)' for rec in policy_schedule_records(pdf_bytes, max_pages=100000)):
        old = resolved.get('Mobile Number', {})
        if old.get('value'):
            updates.append(('Mobile Number', old.get('value'), '[not attributable to insured]'))
        resolved['Mobile Number'] = {'value':'', 'page':None,'bbox':None,
                                     'evidence':'Insured mobile is masked in the source PDF; broker contact excluded.',
                                     'person':'','status':'not_found'}

    # Prevent known bad generic guesses from being shown as "FOUND".
    for field, entry in resolved.items():
        if not isinstance(entry,dict) or field in names:
            continue
        v = str(entry.get('value',''))
        if ((norm(field) in {'registrationnumber','enginenumber','chassisnumber','makemodel','vehiclemakemodel'}
             and (norm(v) in {'vehicle','engineno','chassisno','geographicalarea'} or 'yT py ep e' in v))
            or (norm(field) == 'suminsured' and norm(v) == 'policyschedule')):
            entry['status'] = 'review'
            entry['evidence'] = 'Unreliable generic label/value match: '+entry.get('evidence','')

    return names, updates
