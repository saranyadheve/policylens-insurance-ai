"""Second-pass, layout-independent evidence retrieval.

Returns text passages with page provenance, NEVER an ungrounded field value.
New PDF fields need not appear in a predefined schema.
"""
from __future__ import annotations
import re, math
from collections import Counter

STOP={'the','of','a','an','is','are','was','were','what','which','who','where','when','does','do','tell','give','show','find','get','me','please','i','you','my','this','that','pdf','document','field','value','number','no','name','for','in','to','and','it','on','from','about','details'}

def words(s):return re.findall(r'[a-z0-9]+',str(s).lower())

def query_terms(question):
    return [x for x in words(question) if x not in STOP]

def make_passages(extracted,window=2):
    chunks=[]
    for pi,source in enumerate(extracted.get('pages',[]),1):
        lines=[line.strip() for line in source.splitlines() if line.strip()]
        for i,line in enumerate(lines):
            if len(line)>600:continue
            neighborhood='\n'.join(lines[max(0,i-window):min(len(lines),i+window+1)])
            chunks.append({'Page':pi,'Text':neighborhood,'Focus':line})
    # Table-derived field/value evidence can carry more reliable relationship than flattened text.
    for rec in extracted.get('indexed_records',[]):
        field=rec.get('Field','');value=rec.get('Value','');pg=rec.get('Page')
        if field and value and pg:
            chunks.append({'Page':int(pg),'Text':f'{field}: {value}','Focus':field,'Record':rec})
    return chunks

def retrieve(question,extracted,k=12):
    query=query_terms(question)
    if not query:return []
    docs=make_passages(extracted)
    corpus=[Counter(words(d['Text'])) for d in docs]
    n=len(corpus)
    df=Counter()
    for c in corpus:
        for term in set(query):
            if term in c:df[term]+=1
    scored=[]
    for i,(c,d) in enumerate(zip(corpus,docs)):
        nterms=sum(c.values()) or 1
        score=0.0
        for term in query:
            tf=c[term]
            if tf:
                idf=math.log(1+(n-df[term]+0.5)/(df[term]+0.5))
                score+=idf * tf * 2.2/(tf+1.2*(0.25+0.75*nterms/65))
        focus=set(words(d['Focus']))
        if all(x in focus for x in query):score+=7
        if d.get('Record') and all(x in set(words(d['Record']['Field'])) for x in query):score+=15
        # At least one field-defining term must be present. For ID/tax queries
        # this prevents 'GST amount' matching an unrelated 'Claimed Amount'.
        critical={'gst','gstin','cgst','sgst','igst','pan','aadhaar','aadhar','ifsc','abha'}
        required=set(query)&critical
        if required and not required.issubset(set(c)):
            continue
        if score>0:scored.append((score,i,d))
    scored.sort(key=lambda x:(-x[0],x[1]))
    used=set();out=[]
    for score,i,d in scored:
        key=(d['Page'],d['Text'])
        if key in used:continue
        used.add(key)
        out.append({**d,'Score':round(score,3),'SourceID':f'P{d["Page"]}-E{i}'})
        if len(out)>=k:break
    return out
