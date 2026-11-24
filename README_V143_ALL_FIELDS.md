# PolicyLens V14.3 — ALL-PAGE TABLE DISCOVERY

## What changed
- `comprehensive_tables.py` (new): scans **every PDF page** for native tables, including tiny 2-cell tables, 6-column alternating label/value rows, 8-column header/value rows, 15-column merged-cell grids, numeric/letter numbered tables, and person-wise multi-column forms. Saves page number and PDF cell BBox for value highlighting.
- `app_pipeline.py`: adds the comprehensive table records to the document pipeline.
- `field_resolver.py`: includes those records in common/dynamic resolution.
- `unified_fields.py`: no 66/350-card limit or policy-schedule-page restriction. Source-backed cells from all pages are included; different people/values remain separate. Verified schedule fields continue to determine critical common fields when available. Known malformed native table text guesses are suppressed when source geometry is available. Metadata and uncertainty are kept.
- `app.py`: refreshes Streamlit's processing cache revision; retains viewer, yellow highlight, cards, editing, custom fields, OCR setting, QA, CSV/Excel/JSON export.

## Installation
1. Back up existing `Insurance_Streamlit` folder.
2. Extract this ZIP and copy all files in `Insurance_Streamlit/` into your existing project (or use entire extracted source folder). Keep your local `.venv/` separate.
3. `python -m pip install -r requirements.txt`
4. `python -m streamlit cache clear`
5. `python -m streamlit run app.py --server.port 8503`
6. Clear browser session and upload the policy PDF again. Confirm `V14.3 — ALL-PAGE TABLE DISCOVERY` on the sidebar.
7. Update changed files to GitHub for Streamlit Cloud redeployment.

## Tested examples
- United India 5-page policy: **85 dynamic cards** and source table candidates on all five pages, plus 12 common cards. Engine, chassis, registration, IDV, premiums and insurer/insured are checked.
- Arogya proposal 10 pages: **196 dynamic cards**; `Name — 1st Insured Person` and `Name — 2nd Insured Person` remain distinct.
- Oriental Health and LIC Student Group basic regression checks pass.

## Accuracy / scope
A PDF may contain plain text, scanned text, merged boxes, complex nested tables, repeated labels, or illegible fields. No rule-based parser can promise literally every field in every unseen file. Actual native PDF table labels/values are extracted where detectable; some text-only candidates are marked REVIEW and should be checked against the source. Scanned tables depend on OCR accuracy and may need deeper table structure analysis. No generative model or QR processing is used.

Do not upload private real insurance policy PDFs, `.venv`, `.env`, or `secrets.toml` to public GitHub.
