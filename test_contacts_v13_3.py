"""Regression tests on local supplied PDFs; skip missing PDFs."""
from pathlib import Path
from app_pipeline import process_document
from field_resolver import resolve_fields

CASES={
 'health insurance 2.pdf': {
    'Email':'financeofficer@nls.ac.in',
    'Phone Number':'080-23160532/33/35',
    'Mobile Number':'9731015834',
    'Insured Name':'NATIONAL LAW SCHOOL OF INDIA UNIVERSITY',
    'Insured Address':'PB No. 7201, Nagarbhavi, Bengaluru BANGALORE 560072',
    'Policy Start Date':'29/12/2020',
    'Policy End Date':'28/12/2021',
    'Permanent Address':'',
 },
 'health insurance.pdf': {
    'Email':'registrar@nitpy.ac.in; abhide.nitpy@gmail.com',
    'Phone Number':'XXXXXX5232//XXXXXX7770',
    'Insured Name':'NATIONAL INSTITUTE OF TECHNOLOGY  PUDUCHERRY',
    'Insured Address':'THIRUVETTAKUDY KARAIKAL PUDUCHERRY KOTTUCHERRY ,PONDICHERRY, 609609',
    'Permanent Address':'',
 },
}

def test():
  n=0
  for filename,fields in CASES.items():
    source=Path(__file__).parent.parent/filename
    if not source.is_file(): print('SKIP missing',filename);continue
    raw=source.read_bytes()
    d=process_document(raw)
    output=resolve_fields(fields,d,raw,deep_search=True)
    for field,expected in fields.items():
      actual=output[field]['value']
      assert actual==expected,f'{filename}: {field} expected {expected!r} got {actual!r}'
      n+=1
      print('PASS',filename,field,repr(actual))
  print('Checks passed:',n)

if __name__=='__main__':test()
