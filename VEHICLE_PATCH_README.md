# PolicyLens V14 — Vehicle Table + Exact Source Highlight Patch

Tested source: United India 5-page motor PDF, vehicle details on Page 2.

## Files changed
- `vehicle_geometry.py` **NEW** — extract alternating label/value cells and header/value tables with PDF coordinates
- `app_pipeline.py` — add `vehicle_records` to the existing document extraction pipeline
- `field_resolver.py` — allow vehicle records to enter Common/Dynamic field registry and carry `bbox`
- `app.py` — highlight the exact source value when clicking `View page`, preserve the original layout and all exports; fix the optional `deep_search` switch.
- `test_vehicle_page2.py` — test the specific supplied PDF.

## Installation
1. Back up your `Insurance_Streamlit` folder.
2. Copy the four modified/new files from the PATCH zip into the same folder as `app.py` (replace the three existing files).
3. Keep other Python modules and your `.venv` unchanged.
4. In VS Code PowerShell run:
   `\.venv\Scripts\python.exe -m streamlit cache clear`
   `\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503`
5. Upload the supplied motor insurance PDF again. Find the vehicle fields under `DYNAMIC / DISCOVERED FROM PDF`, click `View page 2` for source highlighting.

## Verified on the supplied Page 2 PDF
Registration Number, Engine Number, Chassis Number, Vehicle Make & Model, Year of Manufacture, Cubic Capacity (display alias `CC`), Registration Date, Carrying Capacity, GVW, Fuel Type, Vehicle IDV, Total IDV; all with page number and `BBox` coordinates.

## Known limits
- This is a tested fix for native selectable-text tables. Scanned/image-only vehicle tables still require OCR and coordinate alignment, and other new layouts can need further validation.
- Additional legacy PDF table candidates may still appear in the Dynamic panel; this patch prefers the verified vehicle geometry record when resolving fields.
- If GitHub/Streamlit Cloud is already deployed, push the four updated source files and redeploy/reboot to activate.
