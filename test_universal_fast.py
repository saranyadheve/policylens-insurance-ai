
import sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from app_pipeline import process_document
from unified_fields import unified_fields

ROOT = Path("/mnt/data")
CASES = [
 ("car insurance 1.pdf",
  {"Policy Number":"11300031210301872580","Insured Name":"MRS. SUBHASHINI P",
   "Policy Start Date":"04-JAN-2022","Policy End Date":"03-JAN-2023",
   "Total Premium":"10,080"}),
 ("health insurance 2.pdf",
  {"Policy Number":"421900/48/2021/4021",
   "Policy Start Date":"29/12/2020","Policy End Date":"28/12/2021",
   "Email":"financeofficer@nls.ac.in"}),
 ("health insurance.pdf",
  {"Policy Number":"73090164250400000013",
   "Policy Start Date":"13/03/2026","Policy End Date":"12/03/2027"}),
 ("Student-Group-Insurance-Policy-2026.pdf",
  {"Name of the Scheme":"LIC's New One Year Renewable Group Term Assurance Plan-I",
   "Proposal Number":"202600004457","Policy Term":"Annually renewable"}),
 ("Arogya_Sanjeevani_Neat_Filled_Fictional_Test.pdf",
  {"Policy Start Date":"01/12/2026","Policy End Date":"30/11/2027"}),
]
total = 0
for fname, expected in CASES:
    path=ROOT/fname
    if not path.exists():
        print("SKIP",fname)
        continue
    t=time.perf_counter()
    pdf=path.read_bytes()
    data=process_document(pdf,"auto")
    common,dynamic,results=unified_fields(data,pdf,deep_search=False)
    for field,needle in expected.items():
        actual=results.get(field,{}).get("value","")
        assert needle.lower() in actual.lower(),f"{fname} / {field} = {actual!r}, expected {needle}"
        total += 1
    assert set(common).isdisjoint(set(dynamic)),f"duplicate labels in {fname}"
    assert len(dynamic)>0
    print("PASS",fname,f"{time.perf_counter()-t:.1f}s",f"{len(dynamic)} dynamic fields",flush=True)
print("Assertions:",total)
