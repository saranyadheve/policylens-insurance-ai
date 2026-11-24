"""Run: python test_v144_all_pages.py <path-to-united-india-pdf>"""
import sys
from collections import Counter
from app_pipeline import process_document
from unified_fields import unified_fields


def run(path):
    raw=open(path,'rb').read()
    data=process_document(raw)
    common,dynamic,resolved=unified_fields(data,raw_pdf=raw)
    geo=data['geometry_records']
    pages=Counter(r['Page'] for r in geo)
    assert all(pages.get(page,0)>0 for page in range(1,6)),pages
    assert len(set(dynamic))==len(dynamic)
    for field,want in [('Policy Number','1005023126P113249760'),
                       ('Insurer Name','UNITED INDIA INSURANCE COMPANY LIMITED'),
                       ('Policy Start Date','24/11/2026'),
                       ('Policy End Date','23/11/2027'),
                       ('Insured Name','MR VISHNU VV'),
                       ('Total Premium','50,541.00'),('Sum Insured','2470741')]:
        assert want in resolved[field]['value'],(field,resolved[field])
    for field,want in [('Registration Number','KL - 01 - DG - 1911'),
                       ('Chassis Number','MA1HB2TMHS3C11794'),
                       ('Engine Number','TMS4B24077'),
                       ('GVW','6100'),('Year of Manufacture','2025')]:
        assert any(r['Field']==field and want in r['Value'] and r.get('BBox') for r in data['vehicle_records']),field
    for field in ('Email','Mobile Number'):
        assert resolved[field]['status']=='not_found',field
    assert not any(x['Field']=='No' and x['Value']=='TMS4B24077' for x in geo)
    print('PASS: 5-page geometry, common data, vehicle fields, contact-safety, no bogus No=Engine')
    print('Geometry-by-page:',dict(sorted(pages.items())))
    print('Dynamic:',len(dynamic),'Unpaired:',len(data.get('unpaired_cells',[])))

if __name__=='__main__':run(sys.argv[1])
