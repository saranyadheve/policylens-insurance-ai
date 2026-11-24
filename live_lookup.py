"""On-question PDF source lookup, independent of cached extraction results.

Searches real table cell geometry rather than relying on a pre-built index or
searching PDF policy-definition prose. No field-specific answer values.
"""
from __future__ import annotations
import re
import pymupdf

QUESTION_WORDS = {'what','which','where','who','when','is','are','was','were','please','tell','show','give','find','me','the','of','a','an','this','that','pdf','document','field','value','values','in','from','for','my','does','do','can','you','i'}
NUM_WORDS={'no':'number','num':'number','nos':'number'}

def terms(s):
    toks=re.findall(r'[a-z0-9]+',str(s).lower())
    return [NUM_WORDS.get(t,t) for t in toks if t not in QUESTION_WORDS]

def clean(s):
    return ' '.join(str(s or '').split()).strip(' :|')

def has_value(v):
    v=clean(v)
    return bool(v and not re.fullmatch(r'[\s.,:/;\-]+',v) and len(v)<350 and not re.search(r'^(?:dd/mm/yyyy|n/a|na)$',v,re.I))

def label_score(question,label):
    q=terms(question); l=terms(label)
    if not q or not l:return -1
    if q==l:return 100
    # 'what is the scheme name' ~ 'name of the scheme'
    if len(q)==len(l) and set(q)==set(l):return 95
    # Requested field terms all must occur in the label (avoids scheme rules matches).
    if set(q).issubset(set(l)):
        return 70 - 4*(len(l)-len(q))
    # One-word specific query can match 'Name of the Scheme' but not 'scheme rules'
    if len(q)==1 and q[0] in l:return 40-3*(len(l)-1)
    return -1

def direct_table_answer(pdf_bytes,question,max_pages=100):
    """Return high-confidence row label/adjacent value pairs with 1-indexed page.

    No model hallucinations; actual table extraction only. If uncertain, empty list.
    """
    matches=[]
    with pymupdf.open(stream=pdf_bytes,filetype='pdf') as doc:
        # First visit pages containing the exact requested label, not pages that
        # merely discuss related terms in definitions or policy conditions.
        requested=' '.join(terms(question))
        searchable=[]
        for pi in range(min(len(doc),max_pages)):
            text=doc[pi].get_text('text').lower()
            joined=' '.join(terms(text))
            raw_question=' '.join(re.findall(r'[a-z0-9]+',question.lower()))
            keyterms=terms(question)
            relevance=(10 if requested and requested in joined else 0) + sum(t in joined for t in keyterms)
            searchable.append((relevance,pi))
        searchable.sort(key=lambda pair:(-pair[0],pair[1]))
        for relevance,page_idx in searchable:
            if relevance==0:continue
            page=doc[page_idx]
            try:tables=page.find_tables().tables
            except Exception:continue
            for table in tables[:40]:
                try:rows=table.extract()
                except Exception:continue
                for row in rows[:400]:
                    if not row or len(row)<2:continue
                    cells=[clean(c) for c in row]
                    # Numeric serial number is not a field label.
                    offset=1 if len(cells)>2 and re.fullmatch(r'\d{1,3}[.)]?',cells[0]) else 0
                    for col in range(offset,len(cells)-1):
                        label=cells[col]
                        if not label or len(label)>170:continue
                        score=label_score(question,label)
                        if score<60:continue
                        # Data usually follows immediately; for several value columns only
                        # use the first populated cell to avoid unrelated columns.
                        value=next((c for c in cells[col+1:] if has_value(c)),None)
                        if not value:continue
                        # A line of generic question text is not a field answer.
                        if len(value.split())>45:continue
                        matches.append((score,{'Field':label,'Value':value,'Person':'','Page':page_idx+1,
                                               'Evidence':f'Table row: {label} = {value}','Method':'live table source lookup'}))
            if any(score>=95 for score,record in matches):
                break
    if not matches:return []
    best=max(sc for sc,_ in matches)
    out=[]; seen=set()
    for sc,record in sorted(matches,key=lambda x:(-x[0],x[1]['Page'])):
        if sc<best-3:continue
        key=(record['Field'].lower(),record['Value'].lower(),record['Page'])
        if key not in seen:seen.add(key);out.append(record)
    return out[:12]

def batch_table_answers(pdf_bytes, questions, max_pages=100):
    """Resolve multiple absent common fields with ONE native table scan.

    Only actual adjacent cells are returned. Never reads narrative text as an
    answer. Keeps page evidence. Unmatched questions remain absent.
    """
    wanted = list(dict.fromkeys(str(q) for q in questions if str(q).strip()))
    if not wanted:
        return {}
    found = {}
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for pi, page in enumerate(doc):
            if pi >= max_pages:
                break
            try:
                tables = page.find_tables().tables
            except Exception:
                continue
            for tab in tables[:40]:
                try:
                    rows = tab.extract()
                except Exception:
                    continue
                for row in rows[:400]:
                    if not row or len(row)<2:
                        continue
                    cells = [clean(c) for c in row]
                    offset = 1 if len(cells)>2 and re.fullmatch(r"\d{1,3}[.)]?",cells[0]) else 0
                    for col in range(offset,len(cells)-1):
                        label = cells[col]
                        if not label or len(label)>170:
                            continue
                        value = next((v for v in cells[col+1:] if has_value(v)),None)
                        if not value or len(value.split())>45:
                            continue
                        for question in wanted:
                            score = label_score(question,label)
                            if score<80:
                                continue
                            current = found.get(question)
                            if current is None or score>current[0]:
                                found[question]=(score,{
                                    "Field":label,"Value":value,"Person":"","Page":pi+1,
                                    "Evidence":f"Table row: {label} = {value}",
                                    "Method":"batch table lookup"
                                })
    return {k:v[1] for k,v in found.items()}
