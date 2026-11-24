"""Coordinates, extraction evidence and generic label-value candidates.
Compatible with both digital PDFs and image-only OCR pages.
"""
from __future__ import annotations
import re
from collections import defaultdict
import pymupdf
from dynamic_fields import dynamic_candidates, tidy, field_name_ok, value_ok, add, tokens
from ocr_adapter import page_text
from table_cache import table_rows

PLACEHOLDERS={'dd/mm/yyyy','yyyy-mm-dd','yes no','single married','male female','m f o'}

def extract_index(data,ocr_engine='auto',max_pages=100):
    pages=[]; fulltext=[]; modes=[]; records=[]; seen=set(); words_by_page=[]
    with pymupdf.open(stream=data,filetype='pdf') as pdf:
        for n,page in enumerate(pdf):
            if n>=max_pages:break
            t,mode,ocrwords=page_text(page,ocr_engine)
            modes.append(mode);fulltext.append(t)
            words=[]
            if mode=='Embedded PDF text':
                for w in page.get_text('words',sort=True):
                    words.append({'text':w[4],'bbox':[round(float(z),2) for z in w[:4]],'block':w[5],'line':w[6]})
            else:
                words=[{'text':w['text'],'bbox':w.get('bbox'),'block':-1,'line':-1} for w in ocrwords]
            words_by_page.append(words)
            pages.append({'number':n+1,'mode':mode,'text':t,'words':words})
            # Extract LABEL:VALUE from OCR text too; cannot claim native PDF positioning.
            for line in t.splitlines():
                line=line.strip()
                if len(line)>230:continue
                pairs=list(re.finditer(r'(?<!\w)([A-Za-z][A-Za-z0-9()./\- ]{1,48}?)\s*:\s*',line))
                for j,m in enumerate(pairs):
                    field=tidy(m.group(1)); end=pairs[j+1].start() if j+1<len(pairs) else len(line)
                    val=tidy(line[m.end():end])
                    if field_name_ok(field) and value_ok(val) and val.lower() not in PLACEHOLDERS:
                        add(records,seen,field,val,n+1,line,'OCR or text label:value')
            if mode=='Embedded PDF text':
                # Native PDF table detection: associate row label with successive cells.
                try:
                    for cells in table_rows(page,30):
                        if not cells:continue
                        # New PDFs use many table shapes, including [serial number, field label, value].
                        # Do not assume the first cell is the field name or first row is a header.
                        first=[tidy(x or '') for x in cells[0]]
                        table_has_header=any(re.search(r'^(?:field|description|particulars|insured person|member)$',x,re.I) for x in first)
                        data_rows=cells[1:] if table_has_header else cells
                        for row in data_rows[:250]:
                            if not row or len(row)<2:continue
                            entries=[tidy(x or '') for x in row]
                            label_i=0
                            if len(entries)>=3 and re.fullmatch(r'\d{1,3}\s*[.)]?',entries[0]):
                                label_i=1
                            label=entries[label_i]
                            if not field_name_ok(label):continue
                            vals=entries[label_i+1:]
                            for vi,val in enumerate(vals,label_i+1):
                                if not value_ok(val):continue
                                # Disallow a bare punctuation as a supposed value.
                                if re.fullmatch(r'[,;./-]+',val):continue
                                heading=first[vi] if table_has_header and vi<len(first) else ''
                                person=heading if re.search(r'insured|person|member|proposer',heading,re.I) else ''
                                before=len(records)
                                add(records,seen,label,val,n+1,f'Table: {label} = {val}', 'table row/column')
                                if len(records)>before: records[-1]['Person']=person
                except Exception:pass
    # Native dynamic candidate extraction catches additional page text structure.
    try:
        for r in dynamic_candidates(data,max_pages,text_pages=fulltext):
            add(records,seen,r['Field'],r['Value'],r['Page'],r['Evidence'],r.get('Method','dynamic'))
    except Exception: pass
    return {'pages':pages,'records':records,'modes':modes,'text_pages':fulltext,'words_by_page':words_by_page}


def locate_evidence(data,page_number,text):
    """Return PDF rectangle of an exact phrase, or None; never approximate a highlight."""
    try:
        with pymupdf.open(stream=data,filetype='pdf') as doc:
            page=doc[page_number-1]
            matches=page.search_for(str(text))
            if matches:return [float(a) for a in matches[0]]
    except Exception:pass
    return None


def highlight_evidence(data,answers):
    doc=pymupdf.open(stream=data,filetype='pdf'); count=0
    try:
        for a in answers:
            p=a.get('Page'); val=a.get('Value') or a.get('Answer')
            if not p or not val or not 1<=int(p)<=len(doc):continue
            rects=doc[int(p)-1].search_for(str(val))
            if not rects: continue
            for rect in rects[:6]:
                doc[int(p)-1].add_highlight_annot(rect);count+=1
        if not count:return None,0
        return doc.tobytes(garbage=4,deflate=True),count
    finally:doc.close()
