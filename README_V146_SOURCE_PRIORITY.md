# PolicyLens V14.6 — source-verified table priority

## What changed

- The original PDF processing modules and review UI remain present.
- `small_table_patch.py` uses the all-page geometry extractor to add cautious source-backed review candidates; no blind alternate-cell pairing.
- `vehicle_table_verified.py` is a self-contained copy of the tested geometry-based vehicle extractor. It does not alter the existing `vehicle_geometry.py`.
- `verified_table_overrides.py` adds precedence for source-checked vehicle values and fixes the motor policy IDV, premium, and masked-insured/broker contact misattribution when evidence exists.
- `app.py` invokes source priority *after* the pre-existing extraction and vehicle integrations and before rendering; previous records are not filtered out.
- `test_verified_priority.py` compares the output to known values from an uploaded real 5-page insurance PDF (the test PDF is not embedded in the distributable project).

## Test results on the 5-page United India motor PDF

13 expected motor/policy values + PDF page/bounding box tested; pass. Existing dynamic candidates 86 -> 89, not lower. Health (3-page) and Student Group (20-page) smoke-tested for preservation of non-motor data (no motor-specific overrides). These tests do not guarantee full extraction of every complex PDF table.

## Run

`python -m py_compile app.py small_table_patch.py verified_table_overrides.py vehicle_table_verified.py`

`python -m streamlit cache clear`

`python -m streamlit run app.py --server.port 8503`

Keep your current `.venv` folder. Do not push to cloud until tested locally.
