# PolicyLens V14.4 — all-page geometry validation

This build fixes the earlier situation where legacy `indexed_records` and loose PDF text-linearization supplied incorrect label/value pairs and a small number of dynamic cards. The UI shows its build stamp, a per-page table candidate count, and an unpaired-cells review table. The extractor processes all native PDF pages (no insurance-profile page filter).

## Changed
- `geometry_all_pages.py`: inspect each page's native tables; handle alternating label/value rows, sparse boxes, multi-column header/value grids, numbered description tables, person-column forms, and long multi-line premium cells. Store source `BBox`/page and keep ambiguous cells separate.
- `app_pipeline.py`: supply `geometry_records` and `unpaired_cells` to the UI.
- `unified_fields.py`: prioritise geometry and verified records, suppress poorly paired legacy index records on pages having geometry candidates; avoid arbitrary 350-field cap.
- `app.py`: display build **V14.4 — GEOMETRY ALL-PAGES · 2026-11-24**, show per-page candidate diagnostics, keep unpaired source cells visible for review. Existing navigation/highlights/export UI remains.
- `test_v144_all_pages.py`: data-grounded regression assertions on the submitted 5-page United India PDF.

## Important limitation
No rule-based PDF parser can guarantee that every field in every unseen scanned, nested, or irregularly drawn table is correctly paired. Unpaired source cells are **not** incorrectly described as Found fields. Source highlights rely on native PDF coordinates; OCR-only values may require OCR box mapping. The count of correctly identified fields varies with layout.

## Install / redeploy
1. Back up your current project. Extract this ZIP; copy the files from its `Insurance_Streamlit/` folder into your project's root. Do not replace `.venv`.
2. Run `python -m streamlit cache clear` then `python -m streamlit run app.py --server.port 8503` using your virtualenv Python.
3. In the Streamlit sidebar confirm the **V14.4** build text. If it still says V14.3, **old files are being run**.
4. On GitHub push changed `.py` files (`app.py`, `app_pipeline.py`, `unified_fields.py`, `geometry_all_pages.py`), wait for Cloud rebuild/reboot, check V14.4 in cloud sidebar.
5. Open the uploaded policy PDF; inspect “Extraction diagnostics — every page” and “Browse unpaired source cells — all PDF pages”.

Test locally: `python test_v144_all_pages.py "path/to/de59e47f-69e9-4b90-8437-82f70d0dfa93.pdf"`

The uploaded insurance samples are **not included** in this ZIP to avoid publishing user documents to GitHub.
