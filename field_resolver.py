"""Resolve configurable fields from source-backed records, without assuming a particular form.
Unverified candidates are flagged for review, never described as guaranteed facts.
"""
import re
from field_catalog import ALIASES
from live_lookup import direct_table_answer

SW={'the','a','an','of','in','for','and','to','on','from','with','as','at','is'}

def norm(s):return [t for t in re.findall(r'[a-z0-9]+',str(s).lower()) if t not in SW]

def score(label,wanted):
 a=norm(label);b=norm(wanted)
 if not a or not b:return -1
 if a==b:return 120
 if set(a)==set(b):return 110
 if set(b).issubset(set(a)):
  return 85 - 5*(len(a)-len(b))
 return -1

def looks_bad(field,value):
 v=str(value or '').strip()
 if not v or v.lower() in {'n/a','na','dd/mm/yyyy','-','none'}:return True
 if len(v)>240:return True
 if re.search(r'[☐□]',v):return True
 if field.lower() in {'pan number','pan'} and not re.fullmatch(r'[A-Z]{5}\d{4}[A-Z]',v.replace(' ',''),re.I):return True
 if field.lower() in {'gst amount','gst'} and not re.search(r'\d',v):return True
 if field in {'Policy Start Date','Policy End Date','Date of Commencement of Policy','Renewal Date','Annual Renewal Date'} and not re.fullmatch(r'(?:\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{1,2}-[A-Za-z]{3}-\d{4})',v):return True
 if field == 'Mobile Number' and not re.fullmatch(r'[6-9]\d{9}',re.sub(r'\D','',v)):return True
 if field == 'Email' and not re.fullmatch(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',v):return True
 return False

def records_for(data):
 out=[]
 for r in data.get('verified_schedule_records',[]):out.append(r)
 for r in data.get('comprehensive_table_records',[]):out.append(r)
 for r in data.get('vehicle_records',[]):out.append(r)
 for r in data.get('schedule_records',[]):out.append(r)
 for r in data.get('contact_records',[]):out.append(r)
 for r in data.get('priority_records',[]):out.append(r)
 for r in data.get('indexed_records',[]):out.append(r)
 for r in data.get('proposal_records',[]):out.append(r)
 for r in data.get('checkbox_records',[]):out.append(r)
 for k,x in data.get('fields',{}).items():
  if x.get('value') is not None:
   out.append({'Field':k,'Value':str(x['value']),'Page':x.get('page'),'Person':'','Evidence':x.get('evidence',''),'Method':'structured'})
 return out

def resolve_one(field,data,records=None):
 candidates=[]
 aliases=[field]+ALIASES.get(field,[])
 # Contact and date labels are validated before matching.
 for r in (records if records is not None else records_for(data)):
  label=str(r.get('Field',''));value=str(r.get('Value','')).strip()
  if looks_bad(field,value):continue
  ss=max(score(label,a) for a in aliases)
  is_priority = r.get('Method') in {'policy-period evidence','explicit date label','explicit renewal','table period','table start','table end','explicit identity label','table identity','email regex','labeled contact regex','labeled phone regex','qualified address label','insured address geometry','insured email geometry','insured mobile geometry','insured phone geometry','insured masked phone geometry','insured name geometry','schedule geometry','vehicle table geometry'}
  if is_priority and ss>=60: ss+=35
  if ss<60:continue
  # no 'GST' matching GSTIN or 'PAN' matching pan masala
  if field in ('GST Amount','PAN Number','Aadhaar Number'):
   bad={'GST Amount':['gstin','igst','cgst','sgst'],'PAN Number':['pan masala'], 'Aadhaar Number':['consent','declaration']}
   if any(b in label.lower() for b in bad[field]):continue
  # exact requested label outranks a broader term (e.g. master policy number vs policy number)
  if field=='Policy Number' and 'master' in label.lower():ss-=35
  if field=='Policy Term' and 'renewal' in label.lower():ss-=30
  if field=='Policy Number' and re.search(r'(?i)\b(?:previous|prev|old|proposal|master)\b',label):ss-=65
  if field == 'Policy Number' and re.search(r'(?i)previous policy',str(r.get('Evidence',''))):ss-=65
  if field in {'Policy End Date','Policy Start Date'} and re.search(r'(?i)\b(?:previous|prev|renewal|proposal|birth|issued|issue)\b',label):ss-=70
  if field=='Email' and not re.fullmatch(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}',value,re.I):continue
  if field=='Phone Number' and not (re.search(r'\d{7,}',value) or (re.search(r'(?i)X{3,}',value) and re.search(r'\d{4}',value))):continue
  if field=='Mobile Number' and not re.fullmatch(r'[6-9]\d{9}',re.sub(r'\D','',value)):continue
  if field=='Insurer Name' and label.lower().startswith('company') and 'address' in label.lower():continue
  if field in {'Email','Phone Number','Mobile Number','Insured Address','Insured Name'} and r.get('Method','').startswith('insured '):ss+=75
  if field in {'Email','Phone Number','Mobile Number','Insured Address'} and ('office' in label.lower() or 'tpa' in label.lower()):ss-=90
  if ss<60:continue
  candidates.append((ss,r))
 if not candidates:
  return {'value':'','page':None,'evidence':'','status':'not_found','person':''}
 candidates.sort(key=lambda x:(-x[0], x[1].get('Page') or 999))
 top=candidates[0][0]
 same=[r for s,r in candidates if s>=top-3]
 # Distinguish multiple different values vs repeated occurrences.
 unique=[]
 for r in same:
  if not any(str(r['Value']).lower()==str(p['Value']).lower() for p in unique):unique.append(r)
 r=unique[0]
 # When multiple source-backed insured emails exist in the same column, display
 # all rather than silently hiding the second email or picking the office one.
 if field=='Email' and len(unique)>1 and all(x.get('Method')=='insured email geometry' for x in unique):
  return {'value':'; '.join(x['Value'] for x in unique),'page':r.get('Page'),
          'evidence':r.get('Evidence',''),'person':'','bbox':r.get('BBox'),'status':'review'}
 return {'value':str(r['Value']),'page':r.get('Page'),'evidence':r.get('Evidence',''),
         'person':r.get('Person',''),'bbox':r.get('BBox'),'status':'found' if len(unique)==1 and top>=100 and not re.search(r'(?i)X{3,}',str(r['Value'])) else 'review'}

def resolve_fields(fields,data,raw_pdf=None,deep_search=False):
 recs=records_for(data)
 results={}
 for field in fields:
  result=resolve_one(field,data,recs)
  # Opt-in slow path for missing fields; otherwise indexing is O(fields x records).
  if deep_search and result['status']=='not_found' and raw_pdf is not None:
   try:
    hits=direct_table_answer(raw_pdf,field)
    if hits:
     h=hits[0]
     result={'value':h['Value'],'page':h['Page'],'evidence':h.get('Evidence',''), 'person':h.get('Person',''),'status':'found'}
   except Exception:pass
  results[field]=result
 return results
