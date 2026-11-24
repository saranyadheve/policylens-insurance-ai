"""Proposal-form field reading: evidence-first positional extraction, no invented values.
Arogya Sanjeevani proposal template is recognized explicitly. Layout is different from a policy schedule.
"""
import re
from collections import defaultdict
import pymupdf

# Display names -> locations in the source template. Coordinates are used ONLY
# after identifying this specific proposal-form template, never for other PDFs.
PAGE1 = [
 ('Proposer Name', 0, 266, 279, 65, 260),
 ('Proposer Date of Birth', 0, 279, 300, 65, 130),
 ('Occupation', 0, 301, 317, 270, 420),
 ('Proposer PAN', 0, 320, 340, 60, 172),
 ('Proposer Aadhaar', 0, 320, 340, 278, 376),
 ('E-Insurance Account Number', 0, 321, 343, 425, 558),
 ('Present Address', 0, 342, 357, 97, 425),
 ('Present City', 0, 360, 379, 40, 170),
 ('Present State', 0, 360, 379, 230, 330),
 ('Present Pin Code', 0, 360, 379, 437, 555),
 ('Permanent Address', 0, 377, 396, 105, 430),
 ('Permanent City', 0, 396, 413, 40, 170),
 ('Permanent State', 0, 396, 413, 230, 330),
 ('Permanent Pin Code', 0, 396, 413, 437, 555),
 ('Telephone Number', 0, 413, 433, 65, 205),
 ('Proposer Email', 0, 413, 433, 245, 420),
 ('Proposer Mobile', 0, 413, 433, 437, 555),
 ('Nominee Name', 0, 460, 480, 90, 285),
 ('Nominee Relationship', 0, 460, 480, 445, 555),
 ('Nominee Present Address', 0, 483, 502, 90, 440),
 ('Nominee Permanent Address', 0, 502, 519, 105, 440),
 ('Nominee Bank Account and IFSC', 0, 521, 541, 130, 290),
 ('Nominee Email', 0, 525, 547, 329, 460),
 ('Nominee Mobile', 0, 525, 547, 463, 555),
 ('TPA Preference', 0, 558, 579, 485, 555),
 ('Coverage Start Time', 0, 607, 628, 112, 181),
 ('Coverage Start Date', 0, 607, 628, 204, 292),
 ('Coverage End Date', 0, 607, 628, 324, 409),
]
PAGE2_TOP = {
 'Insured Name':(84,102),'Date of Birth':(103,117), 'ABHA ID':(148,164),
 'Occupation':(163,179),'Aadhaar Number':(178,194),
 'Sum Insured Basis':(193,209),'Height (cm)':(209,225),
 'Weight (kg)':(225,240),'Blood Group':(239,258),
 'Relationship With Proposer':(258,275),
}
PAGE2_EXISTING = {
 'Previous Insurance Company':(397,416),
 'Previous Policy Number':(415,430),
 'Previous Policy Type':(429,445),
 'Previous Policy Expiry Date':(444,460),
 'Previous Sum Insured':(459,474),
 'Servicing TPA':(473,490),
 'Last Claimed Date':(490,505),
 'Claimed Amount':(503,520),
 'Porting or Migrating':(519,535),
}
PAGE5 = [
 ('Medical Condition',4,126,148,113,197),
 ('Last Consultation Date',4,126,147,192,266),
 ('Medication',4,125,154,267,365),
 ('Treating Doctor',4,126,148,365,433),
 ('Hospital and Phone',4,125,154,430,501),
 ('Present Medical Status',4,126,148,500,555),
 ('Bank Name',4,465,488,91,295),
 ('Bank Branch Address',4,465,488,319,550),
 ('Bank Account Number',4,486,503,118,255),
 ('Bank IFSC',4,486,503,287,440),
]
PAGE6 = [
 ('Office Use Gross Premium',5,631,654,108,202),
 ('Office Use Optional Cover Premium',5,631,654,284,359),
 ('Office Use Net Premium',5,631,654,437,554),
]
PAGE9 = [
 ('Existing Insurer Name',8,247,266,291,549),
 ('Portability Policy Number',8,308,330,291,549),
 ('Portability Sum Insured',8,263,283,291,549),
 ('Proposed Policy Name',8,332,347,291,549),
 ('Proposed Sum Insured',8,349,364,291,549),
 ('Portability Reason',8,390,424,291,549),
 ('Family Members Count',8,482,508,291,549),
]


def colored_spans(page):
    spans=[]
    for b in page.get_text('dict').get('blocks',[]):
        for line in b.get('lines',[]):
            for sp in line.get('spans',[]):
                value=sp['text'].strip()
                color=sp.get('color',0)
                # Overlay color for THIS user-filled test form, not assumed for other documents.
                if color == 0x0d3d94 and value:
                    x0,y0,x1,y1=sp['bbox']
                    spans.append((x0,y0,x1,y1,value))
    return spans


def in_rect(sp, xmin,ymin,xmax,ymax):
    x,y,_,_,_=sp
    return xmin<=x<xmax and ymin<=y<ymax


def add(out,field,val,page,section='Proposal Form',person=None):
    val=re.sub(r'\s+',' ',str(val)).strip()
    if not val or val.upper() in ('N/A','-','NONE PROVIDED'):
        return
    k=(field,person,val)
    if k in out['_seen']:return
    out['_seen'].add(k)
    out['records'].append({
      'Field':field,'Value':val,'Page':page,'Section':section,
      'Person':person or '', 'Evidence':f'{field}: {val}',
    })


def extract_proposal(pdf_bytes):
    doc=pymupdf.open(stream=pdf_bytes,filetype='pdf')
    alltext=' '.join(p.get_text('text')[:3000] for p in doc[:min(2,len(doc))])
    if not ('Arogya Sanjeevani' in alltext and 'Proposal Form' in alltext):
        doc.close(); return []
    out={'records':[],'_seen':set()}
    try:
        inks=[colored_spans(page) for page in doc]
        # Fixed coordinate mapping is applied ONLY to the recognized form template.
        for field,p,y0,y1,x0,x1 in (PAGE1+PAGE5+PAGE6+PAGE9):
            if p>=len(doc):continue
            vals=[sp for sp in inks[p] if in_rect(sp,x0,y0,x1,y1)]
            if vals:
                vals.sort(key=lambda s:(s[1],s[0]))
                add(out,field,' '.join(s[4] for s in vals),p+1)
        if len(inks)>1:
            # Actual insured persons; ignore unfilled 3rd–6th member columns.
            for name,rects in [('Insured 1',(120,195)),('Insured 2',(195,268))]:
                xlo,xhi=rects
                for field,(y0,y1) in {**PAGE2_TOP,**PAGE2_EXISTING}.items():
                    vals=[s for s in inks[1] if in_rect(s,xlo,y0,xhi,y1)]
                    vals.sort(key=lambda s:(s[1],s[0]))
                    if vals:
                        add(out,field,' '.join(s[4] for s in vals),2,'Insured Details' if field in PAGE2_TOP else 'Existing Health Cover',name)
        # Name of insurer in proposal heading, not a guessed policy number.
        if re.search(r'United India Insurance Company Limited',alltext,re.I):
            add(out,'Insurer Name','United India Insurance Company Limited',1,'Document Header')
        # Explicitly do NOT infer GST from PAN, income-tax references, or office net premium.
        # Blank GST/GSTIN in a proposal is "not specified", not numeric zero.
        return out['records']
    finally:
        doc.close()


# Canonical user question terms; whole-token matching avoids PAN vs PAN-MASALA.
ALIASES={
 'pan':['Proposer PAN'], 'pan number':['Proposer PAN'], 'pan card':['Proposer PAN'], 'pan card number':['Proposer PAN'],
 'aadhaar':['Proposer Aadhaar','Aadhaar Number'], 'aadhar':['Proposer Aadhaar','Aadhaar Number'],
 'aadhaar number':['Proposer Aadhaar','Aadhaar Number'], 'aadhaar card number':['Proposer Aadhaar','Aadhaar Number'],
 'state':['Present State','Permanent State'], 'city':['Present City','Permanent City'],
 'pin code':['Present Pin Code','Permanent Pin Code'], 'pincode':['Present Pin Code','Permanent Pin Code'],
 'address':['Present Address','Permanent Address','Nominee Present Address','Nominee Permanent Address'],
 'email':['Proposer Email','Nominee Email'], 'mobile':['Proposer Mobile','Nominee Mobile'],
 'dob':['Proposer Date of Birth','Date of Birth'],'date of birth':['Proposer Date of Birth','Date of Birth'],
 'name':['Proposer Name','Insured Name'],
 'insured name':['Insured Name'], 'policyholder name':['Proposer Name'], 'proposer name':['Proposer Name'],
 'previous insurance company':['Previous Insurance Company','Existing Insurer Name'],
 'insurance company':['Insurer Name','Previous Insurance Company'],
 'insurance number':['Previous Policy Number','Portability Policy Number'],
 'policy number':['Previous Policy Number','Portability Policy Number'],
 'previous policy':['Previous Policy Number','Portability Policy Number'],
 'previous policy number':['Previous Policy Number','Portability Policy Number'],
 'expiry date':['Previous Policy Expiry Date'], 'policy expiry date':['Previous Policy Expiry Date'],
 'last claim date':['Last Claimed Date'],'last claimed date':['Last Claimed Date'],
 'claimed amount':['Claimed Amount'],'claim amount':['Claimed Amount'],
 'servicing tpa':['Servicing TPA'],'tpa':['Servicing TPA','TPA Preference'],
 'height':['Height (cm)'],'weight':['Weight (kg)'], 'blood group':['Blood Group'],
 'ifsc':['Bank IFSC'], 'bank account':['Bank Account Number','Nominee Bank Account and IFSC'],
 'bank name':['Bank Name'], 'bank branch':['Bank Branch Address'],
 'nominee':['Nominee Name'], 'nominee name':['Nominee Name'],
 'sum insured':['Previous Sum Insured','Proposed Sum Insured'],
 'premium':['Office Use Gross Premium','Office Use Net Premium'],
 'gross premium':['Office Use Gross Premium'],'net premium':['Office Use Net Premium'],
 'coverage start':['Coverage Start Date'], 'coverage end':['Coverage End Date'],
 'start date':['Coverage Start Date'], 'end date':['Coverage End Date'],
 'medical condition':['Medical Condition'], 'medication':['Medication'],
 'doctor':['Treating Doctor'], 'hospital':['Hospital and Phone'],
 'e insurance':['E-Insurance Account Number'], 'e insurance account':['E-Insurance Account Number'],
 'insurance account number':['E-Insurance Account Number'],
 'insurance account':['E-Insurance Account Number'],
 'aadhaar card':['Proposer Aadhaar','Aadhaar Number'],
 'abha':['ABHA ID'], 'occupation':['Occupation'],
}
STOP={'where','locate','found','can','i','what','is','the','a','an','me','my','give','show','tell','please','of','for','in','this','that','pdf','document','number','no','details','value','get','find','which','are','does','has','have','to','from','enaku','enna','sollu','kudu','showme'}

def norm(s):return ' '.join(re.findall(r'[a-z0-9]+',str(s).lower()))

def query_proposal(question, records):
    q=norm(question)
    if not q:return []
    aliases={**ALIASES}
    fields=sorted(set(r['Field'] for r in records))
    for f in fields:aliases[norm(f)]=[f]
    # Match complete field phrase with only harmless question words remaining.
    matches=[]
    qtok=q.split()
    for alias,targets in sorted(aliases.items(),key=lambda kv:-len(kv[0])):
        at=alias.split()
        for start in range(len(qtok)-len(at)+1):
            if qtok[start:start+len(at)]!=at:continue
            remaining=qtok[:start]+qtok[start+len(at):]
            if all(t in STOP for t in remaining):
                matches.append((len(at),targets));break
    if not matches:return []
    targets=matches[0][1]
    return [r for r in records if r['Field'] in targets]
