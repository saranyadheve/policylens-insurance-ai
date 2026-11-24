"""Quick smoke checks for OCR executable discovery and graceful missing-OCR behavior."""
import os, tempfile
from pathlib import Path
import pymupdf
import pytesseract
from ocr_runtime import configure_tesseract
from app_pipeline import process_document

with tempfile.TemporaryDirectory() as tmp:
    exe=Path(tmp)/'Tesseract-OCR'/'tesseract.exe'
    exe.parent.mkdir()
    exe.write_bytes(b'placeholder test binary')
    before=os.environ.get('LOCALAPPDATA')
    os.environ['LOCALAPPDATA']=tmp
    try:
        found=configure_tesseract()
        assert found==str(exe), (found,str(exe))
        assert pytesseract.pytesseract.tesseract_cmd==str(exe)
    finally:
        if before is None: os.environ.pop('LOCALAPPDATA',None)
        else: os.environ['LOCALAPPDATA']=before
print('PASS: user-local Tesseract path discovered')

with pymupdf.open() as pdf:
    page=pdf.new_page()
    pdf_data=pdf.tobytes()
# A blank scan must not crash when OCR executable is unavailable.
pytesseract.pytesseract.tesseract_cmd='tesseract-that-does-not-exist-for-testing'
processed=process_document(pdf_data,ocr_engine='tesseract')
assert processed.get('page_count')==1
print('PASS: missing Tesseract returns an empty OCR result, not an application exception')
