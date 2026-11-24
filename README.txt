INSURANCE DOCUMENT EXPLORER V8 — DYNAMIC FIELD CANDIDATES

This version keeps V7 validated extraction and adds a new dynamic extraction layer:
  * extracts embedded PDF text (and OCR fallback when needed)
  * detects candidate "Label: Value" sequences and PDF table key/value cells
  * identifies user requested fields by full words; GST != GSTIN
  * shows evidence and page number; never fabricates a missing value

Install (Windows PowerShell, from extracted project folder):
    py -m pip install -r requirements.txt
    py -m streamlit cache clear
    py -m streamlit run app.py

Choose single or multiple PDFs; click Extract documents. Ask "PAN", "Aadhaar",
"Previous Policy Number", "GSTIN", "Date of Issue", etc.
Use "Browse dynamically discovered PDF label/value pairs" to inspect candidates.

IMPORTANT:
This is an evidence-first rule/geometry/table method, NOT a fine-tuned
LayoutLMv3 or generative document QA model. Text-based PDF tables work best;
scans/handwriting and complex layouts can miss values. Dynamic candidates
MUST be checked against the source PDF for high-stakes use.

Documents should be processed locally; do not upload confidential insurance
or identity files to untrusted web services. Supports PDF files, not password-
protected files.

V9 CHANGE: checkbox_fields.py detects selected choices using existing PDF vector X marks
and associates them with printed options and persons. It does not use a trained model.
The new functionality is particularly relevant for form fields like marital status,
gender, dependent and policy type; unrecognized handwritten/raster checkbox forms
need an image classifier or human review. The included fictional sample PDF
contains a contradictory second-insured gender mark; app reads marked option,
not a gender inferred from the name.

To install: py -m pip install -r requirements.txt
To run: py -m streamlit cache clear && py -m streamlit run app.py
Replace ALL files including checkbox_fields.py.
