"""Local regression check for policy source-priority table corrections."""
import sys
from pathlib import Path
from app_pipeline import process_document
from unified_fields import unified_fields
from verified_table_overrides import apply_source_priority


def run(pdf_path, verify_motor=False):
    raw=Path(pdf_path).read_bytes()
    data=process_document(raw)
    common, dynamic, resolved=unified_fields(data,raw_pdf=raw)
    before=len(dynamic)
    names,changes=apply_source_priority(raw,common,dynamic,resolved)
    assert len(dynamic)>=before, (pdf_path,before,len(dynamic))
    assert data.get('pages'),pdf_path
    if verify_motor:
        expected={
            'Registration Number':'KL - 01 - DG - 1911',
            'Engine Number':'TMS4B24077',
            'Chassis Number':'MA1HB2TMHS3C11794',
            'Vehicle Make & Model':'MAHINDRA & MAHINDRA LIMITED & CRUZIO 3370WB OBD2 18+D REG',
            'Registration Date':'29/08/2025',
            'Year of Manufacture':'2025',
            'Cubic Capacity':'2523',
            'Carrying Capacity':'19',
            'GVW':'6100',
            'Fuel Type':'Diesel',
            'Total IDV':'2470741',
            'Sum Insured':'2470741',
            'Total Premium':'50,541.00',
        }
        for field,value in expected.items():
            assert resolved.get(field,{}).get('value')==value,(field,resolved.get(field))
            r=resolved[field]
            assert r['page'] in range(1,len(data['pages'])+1),(field,'page')
            assert r.get('bbox') is not None,(field,'bbox')
        assert resolved['Mobile Number']['status']=='not_found'
        print('MOTOR PASS',len(expected),'expected values / pages / coordinates verified')
    print('PASS',Path(pdf_path).name,'pages',len(data['pages']),'dynamic',before,'->',len(dynamic),'verified motor',len(names),'changes',len(changes))

if __name__=='__main__':
    run(sys.argv[1],True)
    for path in sys.argv[2:]: run(path)
