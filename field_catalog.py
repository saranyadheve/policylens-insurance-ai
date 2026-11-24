"""Editable display profiles. These are desired output labels, NOT hard-coded answers.
Unknown fields found by dynamic parsing are displayed in a separate section.
"""
PROFILES = {
 'Motor': {
  'POLICY & CUSTOMER': ['Policy Number','Insurer Name','Customer Name','Mobile Number','Phone Number','Email','Insured Address','GSTIN'],
  'VEHICLE': ['Make','Model','Registration Number','Registration Year','Engine Number','Chassis Number','Fuel Type','Seating Capacity','CC','GVW','IDV'],
  'POLICY PERIOD': ['Policy Start Date','Policy End Date','OD Start Date','OD End Date','TP Start Date','TP End Date'],
  'PREMIUM & COVER': ['Own Damage Premium','Third Party Premium','Net Premium','GST Amount','Total Premium','Sum Insured'],
 },
 'Health': {
  'POLICY & CUSTOMER': ['Policy Number','Insurer Name','Insured Name','Proposer Name','Email','Mobile Number','Phone Number','Insured Address','GSTIN'],
  'HEALTH COVER': ['Policy Type','Sum Insured','TPA Name','Number of Members','Pre Existing Disease','Waiting Period','Room Rent Limit'],
  'POLICY PERIOD': ['Policy Start Date','Policy End Date','Date of Issue','Renewal Date'],
  'PREMIUM & TAX': ['Gross Premium','CGST Amount','SGST Amount','IGST Amount','GST Amount','Total Premium'],
  'PERSONAL DETAILS': ['Date of Birth','Gender','Marital Status','Aadhaar Number','PAN Number','Nominee Name'],
 },
 'Life': {
  'POLICY & CUSTOMER': ['Policy Number','Policyholder Name','Insurer Name','Name of the Scheme','Plan Name','Email','Phone Number','Insured Address'],
  'LIFE COVER': ['Sum Assured','Death Benefit','Maturity Benefit','Nominee Name','Premium Payment Frequency','Policy Term'],
  'POLICY PERIOD': ['Date of Commencement of Policy','Policy End Date','Annual Renewal Date','Proposal Date'],
  'PREMIUM': ['Annual Premium','Gross Premium','Total Premium','GST Amount'],
 },
 'Group / Student': {
  'POLICY & GROUP': ['Master Policy Number','Proposal Number','Name of the Master Policyholder','Name of the Scheme','Type of Group','Insurer Name','Email','Phone Number','Insured Address'],
  'GROUP COVER': ['Number of Members Covered','Total Sum Assured','Death Benefit','Entry Age','Maximum Cover Ceasing Age'],
  'POLICY PERIOD': ['Date of Commencement of Policy','Policy Term','Annual Renewal Date','Premium Due Date','Proposal Date'],
  'PREMIUM': ['Frequency of Premium Payment','Total Premium Received','GST Amount'],
 },
 'Property': {
  'POLICY & CUSTOMER': ['Policy Number','Insured Name','Insurer Name','Risk Address','Property Type','Email','Mobile Number','Phone Number'],
  'PROPERTY COVER': ['Building Sum Insured','Contents Sum Insured','Total Sum Insured','Deductible','Policy Start Date','Policy End Date'],
  'PREMIUM': ['Gross Premium','GST Amount','Total Premium'],
 },
 'Consultancy': {
  'POLICY / ENGAGEMENT': ['Policy Number','Certificate Number','Insurer Name','Policyholder Name','Consultancy Name','Consultant Name','Client Name','Professional Indemnity Limit','Email','Mobile Number','Phone Number','Insured Address'],
  'SERVICES & LIABILITY': ['Service Description','Scope of Work','Professional Liability','Limit of Indemnity','Territorial Limit','Retroactive Date','Deductible'],
  'TERM & PREMIUM': ['Policy Start Date','Policy End Date','Policy Term','Gross Premium','GST Amount','Total Premium'],
 },
 'General': {
  'DOCUMENT DETAILS': ['Policy Number','Master Policy Number','Policyholder Name','Insured Name','Insurer Name','Name of the Scheme','Proposal Number','Customer Name','Email','Mobile Number','Phone Number','Insured Address','Present Address','Permanent Address'],
  'COVERAGE': ['Sum Insured','Policy Type','Policy Term','Policy Start Date','Policy End Date','Renewal Date','Date of Commencement of Policy','Date of Issue','Date of Birth','Marital Status','Registration Number','Number of Members Covered'],
  'PREMIUM': ['Gross Premium','GST Amount','Total Premium'],
 },
}
# Separate menu choices use the same field schema but never constrain the document parser.
PROFILES['Student'] = {k:list(v) for k,v in PROFILES['Group / Student'].items()}
PROFILES['Group'] = {k:list(v) for k,v in PROFILES['Group / Student'].items()}
# Alternative labels are used for ranking; none of these are populated values.
ALIASES={
 'Policy Number':['policy no','policy no.','policy number','policy id'],
 'Master Policy Number':['master policy number','master policy no','master policy no.'],
 'Proposal Number':['proposal no','proposal no.','proposal number'],
 'Name of the Scheme':['name of the scheme','scheme name'],
 'Type of Group':['type of group'],
 'Insurer Name':['name of insurer','insurer','insurance company','company name'],
 'Customer Name':['customer','customer name','name of insured'],
 'Insured Name':['insured name','name of insured','name of the insured'],
 'Proposer Name':['proposer name','name of proposer'],
 'Policyholder Name':['name of the policyholder','policyholder name','name of master policyholder'],
 'Name of the Master Policyholder':['name of the master policyholder','master policyholder'],
 'Number of Members Covered':['number of members covered as on the date of commencement of master policy','number of members covered','number of members','no of members covered'],
 'Total Premium Received':['total premium received towards assured benefit on date of commencement of policy','total premium received','total premium'],
 'Total Sum Assured':['total sum assured','sum assured'],
 'Frequency of Premium Payment':['frequency of premium payment','premium payment frequency'],
 'Policy Start Date':['start date','date of commencement of policy','period of insurance from','policy inception date','period from','coverage start date','inception date'],
 'Policy End Date':['policy expiry date','expiry date','end date','period of insurance to','period to','coverage end date','valid upto','valid till'],
 'Annual Renewal Date':['annual renewal date','renewal date'],
 'Date of Commencement of Policy':['date of commencement of policy','commencement date'],
 'Registration Number':['registration mark & no.','registration number','reg no','vehicle registration number'],
 'Make':['make','vehicle make'], 'Model':['model','vehicle model'],
 'CC':['cc','cubic capacity'], 'GVW':['gvw','gross vehicle weight'],
 'IDV':['idv of vehicle','idv','insured declared value'],
 'Total Premium':['total premium','premium payable','net premium incl tax'],
 'GST Amount':['gst amount','total gst','goods and services tax'],
 'PAN Number':['pan','pan no','pan number','proposer pan'],
 'Aadhaar Number':['aadhaar no','aadhaar number','aadhar number','proposer aadhaar'],
 'Mobile Number':['mobile','mobile number','contact number','phone number'],
 'Email':['email','email id','e-mail','e-mail/fax'],
 'Phone Number':['telephone','telephone no','phone no','phone number','tel no'],
 'Insured Address':['insured address','policyholder address','present address','permanent address','risk address'],
 'Present Address':['present address'],
 'Permanent Address':['permanent address'],
 'Renewal Date':['annual renewal date','renewal date'],
 'Date of Birth':['date of birth','dob'],
 'Marital Status':['marital status'],
 'TPA Name':['tpa','tpa preference','servicing tpa'],
}

def detect_type(text):
 t=text.lower()[:60000]
 if ('motor vehicle' in t or 'vehicle registration' in t or 'engine no.' in t) and ('insurance' in t):return 'Motor'
 if ('group term assurance' in t or 'master policyholder' in t or 'group term insurance' in t):return 'Group / Student'
 if 'arogya sanjeevani' in t or ('health insurance' in t or 'mediclaim' in t):return 'Health'
 if 'life insurance' in t and ('sum assured' in t or 'premium' in t):return 'Life'
 if 'property insurance' in t or 'fire and allied' in t:return 'Property'
 if any(x in t for x in ('professional indemnity','consultancy services','consultant liability','consulting firm','consultancy agreement')):return 'Consultancy'
 return 'General'


# Universal fixed fields ONLY. Everything else comes from PDF-discovered labels.
COMMON_EXPLICIT_FIELDS = [
    "Policy Number", "Policyholder Name", "Insurer Name",
    "Policy Start Date", "Policy End Date",
    "Insured Name", "Insured Address",
    "Email", "Mobile Number", "Phone Number",
    "Sum Insured", "Total Premium",
]
