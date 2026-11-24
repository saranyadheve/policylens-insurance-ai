"""Run: python test_vehicle_page2.py /path/to/policy.pdf"""
import sys
from pathlib import Path
from vehicle_geometry import vehicle_records
from app_pipeline import process_document
from unified_fields import unified_fields

EXPECTED={
    'Registration Number':'KL - 01 - DG - 1911',
    'Engine Number':'TMS4B24077',
    'Chassis Number':'MA1HB2TMHS3C11794',
    'Vehicle Make & Model':'MAHINDRA & MAHINDRA LIMITED & CRUZIO 3370WB OBD2 18+D REG',
    'Year of Manufacture':'2025',
    'Cubic Capacity':'2523',
    'Registration Date':'29/08/2025',
    'Carrying Capacity':'19',
    'GVW':'6100',
    'Fuel Type':'Diesel',
    'Vehicle IDV':'2470741',
    'Total IDV':'2470741',
}

def run(path):
    raw=Path(path).read_bytes()
    records=list(vehicle_records(raw))
    by_name={r['Field']:r for r in records}
    for key,val in EXPECTED.items():
        assert key in by_name, f'Missing {key}'
        r=by_name[key]
        assert r['Value']==val, f'Wrong {key}: {r["Value"]!r}'
        assert r['Page']==2, f'Wrong page for {key}'
        assert r.get('BBox') and len(r['BBox'])==4, f'Missing coordinates for {key}'
        print('PASS',key, val)
    d=process_document(raw)
    assert d['vehicle_records']
    _, dynamic, resolved=unified_fields(d,raw,deep_search=False)
    for field in ['Registration Number','Engine Number','Chassis Number','Vehicle Make & Model','Year of Manufacture','Fuel Type','GVW','Vehicle IDV','Total IDV']:
        assert resolved[field]['status'] in ('found','review'), f'{field} not resolved'
        assert resolved[field]['bbox'], f'{field} has no UI highlight coordinates'
        assert field in dynamic, f'{field} missing from dynamic panel'
    assert resolved['CC']['value']=='2523', 'Cubic capacity should be presented through existing CC alias'
    print('PASS - full pipeline, source bounding boxes, UI registry')

if __name__=='__main__':
    run(sys.argv[1] if len(sys.argv)>1 else '/mnt/data/de59e47f-69e9-4b90-8437-82f70d0dfa93.pdf')
