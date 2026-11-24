import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from unified_fields import unified_fields

def test_registry_synthetic():
    sample={"indexed_records":[
        {"Field":"Policy No.","Value":"POL-2026-123","Page":1},
        {"Field":"Name of the Scheme","Value":"New Group Assurance","Page":3},
        {"Field":"Proposal No","Value":"202600004457","Page":3},
        {"Field":"Policy Term","Value":"Annually renewable","Page":3},
        {"Field":"Email Id","Value":"contact@example.org","Page":2},
    ]}
    fixed, dynamic, resolved=unified_fields(sample,deep_search=False)
    assert "Policy Number" in fixed
    assert "Name of the Scheme" not in fixed
    assert "Name of the Scheme" in dynamic
    assert "Proposal Number" in dynamic
    assert "Policy No." not in dynamic
    assert resolved["Policy Number"]["value"]=="POL-2026-123"
    assert resolved["Name of the Scheme"]["value"]=="New Group Assurance"
    assert resolved["Proposal Number"]["value"]=="202600004457"
    assert resolved["Email"]["value"]=="contact@example.org"
    print("PASS: explicit/dynamic separation, alias dedupe, shared source lookup")

def test_real_lic(path):
    from app_pipeline import process_document
    b=Path(path).read_bytes()
    data=process_document(b,"auto")
    fixed,dynamic,resolved=unified_fields(data,deep_search=False)
    assert "Name of the Scheme" in dynamic
    assert resolved["Name of the Scheme"]["page"]==3
    assert "New One Year Renewable" in resolved["Name of the Scheme"]["value"]
    assert resolved["Proposal Number"]["value"]=="202600004457"
    assert resolved["Policy Term"]["value"]=="Annually renewable"
    print("PASS: real LIC Page 3 scheme, proposal, policy term")

if __name__=="__main__":
    test_registry_synthetic()
    if len(sys.argv)>1: test_real_lic(sys.argv[1])
