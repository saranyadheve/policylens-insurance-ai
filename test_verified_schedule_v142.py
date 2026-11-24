from pathlib import Path
from app_pipeline import process_document
from unified_fields import unified_fields
from vehicle_geometry import vehicle_records

PDF = Path(__file__).resolve().parent / 'test_input_uiic.pdf'


def test_uiic_schedule():
    raw=PDF.read_bytes()
    data=process_document(raw)
    explicit,dynamic,res=unified_fields(data,raw,deep_search=False)
    expected={
        'Policy Number':'1005023126P113249760',
        'Insurer Name':'UNITED INDIA INSURANCE COMPANY LIMITED',
        'Policy Start Date':'24/11/2026',
        'Policy End Date':'23/11/2027',
        'Insured Name':'MR VISHNU VV',
        'Total Premium':'50,541.00',
        'Sum Insured':'2470741',
    }
    for label,want in expected.items():
        r=res[label]
        assert r['value']==want,(label,r)
        assert r.get('bbox') and len(r['bbox'])==4,(label,r)
    assert 'PRAVEEN BHAVAN' in res['Insured Address']['value']
    assert '695523' in res['Insured Address']['value']
    assert 'POLICY ISSUING' not in res['Insured Address']['value'].upper()
    for field in ('Email','Mobile Number','Phone Number'):
        assert res[field]['status']=='not_found',(field,res[field])
    vehicle={r['Field']:r for r in data['vehicle_records']}
    expected_vehicle={
        'Registration Number':'KL - 01 - DG - 1911',
        'Engine Number':'TMS4B24077',
        'Chassis Number':'MA1HB2TMHS3C11794',
        'Year of Manufacture':'2025',
        'Registration Date':'29/08/2025',
        'Cubic Capacity':'2523',
        'Carrying Capacity':'19',
        'GVW':'6100',
        'Fuel Type':'Diesel',
        'Vehicle IDV':'2470741',
        'Total IDV':'2470741',
    }
    for f,want in expected_vehicle.items():
        assert vehicle[f]['Value']==want,(f,vehicle.get(f))
        assert vehicle[f]['Page']==2,(f,vehicle[f])
        assert vehicle[f]['BBox'] and len(vehicle[f]['BBox'])==4,(f,vehicle[f])
    assert len(dynamic)<55,len(dynamic)
    return len(dynamic),len(data['vehicle_records'])

if __name__=='__main__':print('UIIC verified:',test_uiic_schedule())
