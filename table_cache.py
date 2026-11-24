"""Process-scoped native table extraction reuse.

A PDF is opened by multiple legacy extractors, but its native tables are
detected once per page during a single process_document call.
The cache is freed after processing and is isolated per execution context.
"""
from contextvars import ContextVar
from contextlib import contextmanager

_ACTIVE = ContextVar("policylens_pdf_table_cache", default=None)

@contextmanager
def table_session():
    token = _ACTIVE.set({})
    try:
        yield
    finally:
        _ACTIVE.reset(token)

def table_rows(page, max_tables=40):
    cache = _ACTIVE.get()
    page_id = int(page.number)
    if cache is not None and page_id in cache:
        return cache[page_id][:max_tables]
    try:
        found = page.find_tables()
        extracted = [table.extract() for table in found.tables[:40]]
    except Exception:
        extracted = []
    if cache is not None:
        cache[page_id] = extracted
    return extracted[:max_tables]
