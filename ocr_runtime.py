"""Find the Windows Tesseract executable before OCR is called.
No installation privileges or PATH edits required; works with user-local installs.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path


def configure_tesseract() -> str | None:
    try:
        import pytesseract
    except ImportError:
        return None
    candidates = []
    override = os.environ.get('TESSERACT_CMD')
    if override:
        candidates.append(Path(override.strip('"')))
    existing = getattr(pytesseract.pytesseract, 'tesseract_cmd', '')
    if existing and (Path(existing).is_absolute() or '/' in existing or '\\' in existing):
        candidates.append(Path(existing))
    local_appdata = os.environ.get('LOCALAPPDATA')
    if local_appdata:
        candidates.append(Path(local_appdata) / 'Tesseract-OCR' / 'tesseract.exe')
    for var in ('ProgramFiles', 'ProgramFiles(x86)'):
        if os.environ.get(var):
            candidates.append(Path(os.environ[var]) / 'Tesseract-OCR' / 'tesseract.exe')
    for path in (r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                 r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
        candidates.append(Path(path))
    found = shutil.which('tesseract')
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return str(candidate)
    return None
