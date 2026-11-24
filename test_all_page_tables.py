"""Regression checks for the supplied insurance sample PDFs.
Run: python test_all_page_tables.py
"""
import os
from pathlib import Path
from app_pipeline import process_document
from unified_fields import unified_fields

SAMPLES=Path(os.environ.get('POLICYLENS_SAMPLES','/mnt/data'))


def inspect(name):
    b=(SAMPLES/name).read_bytes()
    data=process_document(b)
    common,dyn,resolved=unified_fields(data,b)
    return data,common,dyn,resolved


def test_uiic():
    d,c,dyn,r=inspect('de59e47f-69e9-4b90-8437-82f70d0dfa93.pdf')
    assert {1,2,3,4,5}.issubset({x['Page'] for x in d['comprehensive_table_records']})
    assert len(dyn)>66, f'Expected >66 distinct fields, got {len(dyn)}'
    assert r['Insurer Name']['value'].startswith('UNITED INDIA INSURANCE')
    assert r['Insured Name']['value']=='MR VISHNU VV'
    assert r['Policy Start Date']['value']=='24/11/2026'
    assert r['Policy End Date']['value']=='23/11/2027'
    assert r['Total Premium']['value']=='50,541.00'
    assert r['Sum Insured']['value']=='2470741'
    assert r['Mobile Number']['status']=='not_found'
    assert r['Email']['status']=='not_found'
    expected={'Registration Number':'KL - 01 - DG - 1911',
              'Engine Number':'TMS4B24077',
              'Chassis Number':'MA1HB2TMHS3C11794',
              'Vehicle Make & Model':'MAHINDRA & MAHINDRA LIMITED & CRUZIO 3370WB OBD2 18+D REG',
              'Total IDV':'2470741',
              'CGST(9%)':'3,855.00',
              'Gross Assessed Liability':'Rs.10,000/-'}
    for field,value in expected.items():
        record=r[field]
        assert record['value']==value,(field,record)
        assert record['page'] in range(1,6)
        assert record.get('bbox'),(field,'missing highlight rectangle')
    for field in ('Product Name','Major Exclusions','Obligations of the Policyholder'):
        assert field in dyn,(field,'missing from source tables')
    print('UIIC 5-page all-field test passed:',len(dyn),'dynamic cards')


def test_agroya():
    _,_,dyn,r=inspect('Arogya_Sanjeevani_Neat_Filled_Fictional_Test.pdf')
    assert r['Name — 1st Insured Person']['value']=='ARUN KUMAR'
    assert r['Name — 2nd Insured Person']['value']=='MEERA ARUN'
    assert len(dyn)>50
    print('Arogya 10-page person-table test passed:',len(dyn),'dynamic cards')


def test_health():
    _,_,dyn,r=inspect('health insurance 2.pdf')
    assert r['Policy Number']['value']=='421900/48/2021/4021'
    assert dyn
    print('Oriental Health test passed:',len(dyn),'dynamic cards')

if __name__=='__main__':
    test_uiic()
    test_agroya()
    test_health()
