"""Qwen optional *answer synthesis* with strict provenance checks.
Remote APIs not called. Local Ollama only. Model's answer must occur in source evidence.
"""
from __future__ import annotations
import json, urllib.request, re
from evidence_retrieval import retrieve,words

def query_ollama(question,passages,model='qwen2.5:3b',url='http://127.0.0.1:11434',timeout=75):
    if not passages:return None
    excerpts=[{'id':p['SourceID'],'page':p['Page'],'text':p['Text'][:1100]} for p in passages[:9]]
    system='''Extract factual answers only from the supplied PDF evidence. Return ONE JSON object with keys answer, source_id, quote. If the answer is missing or ambiguous, return {"answer":"","source_id":"","quote":""}. Never guess. Do not use knowledge not in the evidence. For a field answer, copy the exact value, NOT the label; preserve punctuation and numerals. quote must be copied verbatim from the cited evidence.'''
    prompt=system+'\nQUESTION: '+question+'\nEVIDENCE:\n'+json.dumps(excerpts,ensure_ascii=False)
    req=urllib.request.Request(url.rstrip('/')+'/api/generate',data=json.dumps({'model':model,'prompt':prompt,'stream':False,'format':'json','options':{'temperature':0}}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as resp: raw=json.load(resp)
    try:out=json.loads(raw.get('response','{}'))
    except (ValueError,TypeError):return None
    answer=str(out.get('answer','')).strip();source_id=str(out.get('source_id','')).strip();quote=str(out.get('quote','')).strip()
    source=next((p for p in passages if p['SourceID']==source_id),None)
    if not source or not answer or not quote:return None
    def norm(s):return ' '.join(str(s).split()).lower()
    # Verbatim evidence checks: avoid hallucinating values and misattributed page numbers.
    if norm(quote) not in norm(source['Text']) or norm(answer) not in norm(quote):return None
    if len(answer)>260 or answer.lower() in {'not found','unknown','none','n/a'}:return None
    return {'Field':question,'Value':answer,'Person':'','Page':source['Page'],'Evidence':quote,'Method':'grounded Qwen / verified quote'}

def ask_with_retrieval(question,extracted,use_qwen=False,model='qwen2.5:3b',url='http://127.0.0.1:11434'):
    passages=retrieve(question,extracted)
    if use_qwen:
        try:
            answer=query_ollama(question,passages,model,url)
            if answer:return {'status':'found','answers':[answer],'note':'Verbatim answer checked against PDF source quote','passages':passages}
        except Exception as e:
            return {'status':'needs_review','answers':[],'note':f'Local Ollama unavailable ({type(e).__name__})','passages':passages}
    return {'status':'needs_review' if passages else 'not_found','answers':[], 'note':'Relevant source passages found; no verified value inferred automatically.' if passages else 'No matching source passage','passages':passages}
