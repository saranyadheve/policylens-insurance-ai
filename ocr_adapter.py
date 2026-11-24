"""OCR engines: embedded text > PaddleOCR PP-OCRv5 (optional) > Tesseract.
Coordinates are in original PDF points. No invented text or values.
"""
from __future__ import annotations
import io
from PIL import Image
import pymupdf


def page_text(page, engine='auto', dpi=180, min_chars=75):
    native=page.get_text('text',sort=True)
    if len(native.strip())>=min_chars:
        return native,'Embedded PDF text',[]
    if engine == 'paddle':
        try:
            text,words=paddle_ocr(page,dpi)
            if text.strip():return text,'PaddleOCR PP-OCRv5',words
        except Exception as exc:
            if engine=='paddle': return '',f'PaddleOCR unavailable: {str(exc)[:120]}',[]
    try:
        import pytesseract
        im=Image.open(io.BytesIO(page.get_pixmap(dpi=dpi,alpha=False).tobytes('png')))
        scale=72.0/dpi
        data=pytesseract.image_to_data(im,output_type=pytesseract.Output.DICT)
        words=[]
        for i,t in enumerate(data['text']):
            if str(t).strip():
                words.append({'text':str(t).strip(),'bbox':[data['left'][i]*scale,data['top'][i]*scale,(data['left'][i]+data['width'][i])*scale,(data['top'][i]+data['height'][i])*scale]})
        return pytesseract.image_to_string(im),'Tesseract OCR',words
    except Exception as exc:
        return '',f'OCR unavailable: {str(exc)[:100]}',[]


def paddle_ocr(page,dpi=180):
    # V3 PaddleOCR API. Load lazily and cache model per Python process.
    from functools import lru_cache
    import numpy as np
    from paddleocr import PaddleOCR
    @lru_cache(maxsize=1)
    def create():
        return PaddleOCR(lang='en',ocr_version='PP-OCRv5',use_doc_orientation_classify=False,
                         use_doc_unwarping=False,use_textline_orientation=False)
    # Keep a module level cache as the decorator of a nested function resets each call.
    global _PADDLE_MODEL
    if _PADDLE_MODEL is None:_PADDLE_MODEL=create()
    pix=page.get_pixmap(dpi=dpi,alpha=False)
    im=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    results=_PADDLE_MODEL.predict(np.array(im))
    scale=72.0/dpi; words=[]
    for r in results:
        data=r.json if hasattr(r,'json') else r
        if isinstance(data,dict) and 'res' in data:data=data['res']
        if not isinstance(data,dict):continue
        texts=data.get('rec_texts',[]); boxes=data.get('rec_polys',data.get('dt_polys',[]))
        for i,t in enumerate(texts):
            if not str(t).strip():continue
            if i < len(boxes):
                poly=np.asarray(boxes[i],dtype=float).reshape(-1,2)
                x0,y0=poly.min(axis=0);x1,y1=poly.max(axis=0)
                bbox=[float(x0)*scale,float(y0)*scale,float(x1)*scale,float(y1)*scale]
            else:bbox=None
            words.append({'text':str(t).strip(),'bbox':bbox})
    words.sort(key=lambda a:((a['bbox'] or [0,0])[1],(a['bbox'] or [0])[0]))
    return '\n'.join(w['text'] for w in words),words

_PADDLE_MODEL=None
