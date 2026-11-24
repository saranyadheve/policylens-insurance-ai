"""Quick regression tests on supplied insurance sample PDFs (if available)."""
from pathlib import Path
from priority_fields import extract_priority_fields
from field_resolver import resolve_fields

ROOT=Path(__file__).resolve().parent.parent
CASES={
 'health insurance.pdf':{'Policy Start Date':'13/03/2026','Policy End Date':'12/03/2027','Email':'registrar@nitpy.ac.in'},
 'health insurance 2.pdf':{'Policy Start Date':'29/12/2020','Policy End Date':'28/12/2021'},
 'Student-Group-Insurance-Policy-2026.pdf':{'Policy Start Date':'22/01/2026','Policyholder Name':'DYAL SINGH COLLEGE'},
 'Arogya_Sanjeevani_Neat_Filled_Fictional_Test.pdf':{'Policy Start Date':'01/12/2026','Policy End Date':'30/11/2027','Mobile Number':'9000000001'},
}

def test_regression():
    passed=0
    for filename,expected in CASES.items():
        path=ROOT/filename
        if not path.exists():
            print('SKIPPED (sample not included):', filename)
            continue
        rows=extract_priority_fields(path.read_bytes())
        got=resolve_fields(list(expected),{'priority_records':rows})
        for key,val in expected.items():
            assert got[key]['value']==val,(filename,key,got[key]['value'],val)
            passed+=1
    print('Priority regression checks passed:', passed)

if __name__=='__main__':test_regression()
