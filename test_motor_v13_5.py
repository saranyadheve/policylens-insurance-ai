from pathlib import Path
from app_pipeline import process_document
from unified_fields import unified_fields

def check(pdf_path):
    raw=Path(pdf_path).read_bytes()
    data=process_document(raw,'auto')
    common,dynamic,result=unified_fields(data,deep_search=False)
    assert result['Policy Number']['value']=='11300031210301872580'
    assert result['Insurer Name']['value']=='The New India Assurance Co. Ltd.'
    assert result['Insured Name']['value']=='MRS. SUBHASHINI P'
    assert result['Policy Start Date']['value']=='04-JAN-2022'
    assert result['Policy End Date']['value']=='03-JAN-2023'
    assert '641030' in result['Insured Address']['value']
    assert result['Total Premium']['value']=='10,080'
    assert result['Gross Premium Paid']['value']=='11,895'
    assert result['Model']['value']=='GRAND I10'
    assert result['Total IDV']['value']=='373,766'
    assert result['Proposal Number']['value']=='P46209991'
    assert not result['Email']['value']
    assert not result['Mobile Number']['value']
    assert 'Name of the Scheme' not in common
    assert len(dynamic)>15
    print('PASS: 15 Motor policy / unified registry assertions')

if __name__=='__main__':
    import sys
    check(sys.argv[1])
