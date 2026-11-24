"""Optional trained LayoutLMv3 token classifier, never base model as extractor.
Compatible label vocab example: O, B-KEY, I-KEY, B-VALUE, I-VALUE.
Use only a locally fine-tuned directory. Produces unl inked spans requiring verification.
"""
from __future__ import annotations
from functools import lru_cache
import io
import pymupdf

@lru_cache(maxsize=2)
def _model(checkpoint):
    from transformers import AutoProcessor,LayoutLMv3ForTokenClassification
    processor=AutoProcessor.from_pretrained(checkpoint,apply_ocr=False)
    model=LayoutLMv3ForTokenClassification.from_pretrained(checkpoint)
    model.eval()
    return processor,model

def predict_page(page,checkpoint):
    """Return token classification spans with bbox and confidence. Requires trained checkpoint."""
    from PIL import Image
    import torch
    processor,model=_model(checkpoint)
    words=page.get_text('words',sort=True)
    if not words:return []
    page_w=max(float(page.rect.width),1);page_h=max(float(page.rect.height),1)
    raw_words=[w[4] for w in words]
    boxes=[[max(0,min(1000,int(w[0]/page_w*1000))),max(0,min(1000,int(w[1]/page_h*1000))),
            max(0,min(1000,int(w[2]/page_w*1000))),max(0,min(1000,int(w[3]/page_h*1000)))] for w in words]
    im=Image.open(io.BytesIO(page.get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False).tobytes('png')))
    encoded=processor(im,raw_words,boxes=boxes,return_tensors='pt',truncation=True,padding='max_length')
    with torch.no_grad():logits=model(**encoded).logits[0]
    confidences=logits.softmax(-1).max(-1).values
    pred=logits.argmax(-1).tolist()
    word_ids=encoded.word_ids(batch_index=0)
    perword={}
    for token_idx,wid in enumerate(word_ids):
        if wid is None or wid in perword:continue
        lab=model.config.id2label[int(pred[token_idx])]
        perword[wid]=(lab,float(confidences[token_idx]))
    spans=[];current=None
    for i,word in enumerate(raw_words):
        lab,conf=perword.get(i,('O',0.))
        typ=lab.split('-',1)[-1] if '-' in lab else None
        if lab.startswith('B-') or (lab.startswith('I-') and (current is None or current['Label']!=typ)):
            if current:spans.append(current)
            current={'Label':typ,'Text':word,'BBox':list(words[i][:4]),'Confidence':conf,'PageWordStart':i}
        elif lab.startswith('I-') and current and current['Label']==typ:
            current['Text']+=' '+word
            current['BBox']=[min(current['BBox'][0],words[i][0]),min(current['BBox'][1],words[i][1]),
                             max(current['BBox'][2],words[i][2]),max(current['BBox'][3],words[i][3])]
            current['Confidence']=min(conf,current['Confidence'])
        else:
            if current:spans.append(current);current=None
    if current:spans.append(current)
    return spans

def recognize_document(pdfbytes,checkpoint,max_pages=50):
    output=[]
    with pymupdf.open(stream=pdfbytes,filetype='pdf') as doc:
        for i,page in enumerate(doc):
            if i>=max_pages:break
            for span in predict_page(page,checkpoint):
                span['Page']=i+1
                output.append(span)
    return output
