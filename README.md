# PolicyLens V14 — Universal Insurance Extraction + Fast Mode

**Full Streamlit project** based on V13.5. Default profile is **General**,
with **Common / Explicit Fields** and **Dynamic / Discovered From PDF**.
The same system works on any supported PDF category (Motor, Health,
Life, Group/Student, Property, Consultancy); no category restricts uploads.

## Speed improvements

1. Native PDF tables are detected once per page per extraction instead of
   being detected repeatedly by index, dynamic and schedule extractors.
   `table_cache.py` uses a bounded-per-processing context and releases
   page table data when the document finishes.
2. Index passes its extracted OCR/native text to dynamic discovery, avoiding
   a second OCR pass for pages already indexed.
3. Default `auto` OCR uses embedded PDF text first, then **Tesseract only
   when needed**. Heavy PaddleOCR is an explicit engine option.
4. Default **Fast** mode resolves all visible fields from one indexed
   document instead of reopening/re-scanning the PDF for each missing
   field. The sidebar **Deep recheck missing common fields (slower)**
   option can run one extra batched table search when needed.
5. Streamlit caches processed PDF bytes, so manual editing / navigating
   does not repeat document extraction.

## Safety and scope

- The PDF preview, common explicit cards, discovered field cards, manual
  edits, source pages and Excel/CSV/JSON export are retained.
- No Qwen, Ollama, generative APIs or QR scanner.
- Never treat a "previous policy number" on a proposal-only document as
  a current policy number without independent evidence.
- Values without reliable document evidence remain absent and editable.
- Dynamic discovery is heuristic, not a fine-tuned model. New complex
  scanned document types can still require verification.
- Specific category selection is informational; default General accepts
  any supported insurance PDF.

## Verified benchmark (this environment, warm-free samples)

| PDF | Old V13.5 indexing | V14 indexing |
|---|---:|---:|
| Car (3 pages) | ~4.4 sec | ~2.5 sec |
| Health / Oriental (2 pages) | ~1.9 sec | ~1.1 sec |
| Health / New India (3 pages) | ~4.6 sec | ~2.5 sec |
| Group / LIC (20 pages) | ~11.4 sec | ~7.3 sec |
| Proposal / Arogya (10 pages) | ~37.4 sec | ~20.0 sec |

Numbers are local measurements, not guaranteed Windows timings. OCR scanned
pages may take longer. `python test_universal_fast.py` passes 17 assertions
on the five matching PDF files, if they are in `/mnt/data` for this
development environment (users should change the paths in that test
script for Windows).

## Windows setup

1. Backup your existing `Insurance_Streamlit` folder.
2. Extract the ZIP and copy **the contents** of
   `policylens_v14_universal_fast` into `Insurance_Streamlit`.
   Keep your existing `.venv`.
3. Stop the previous Streamlit server with `Ctrl+C`.
4. Run these commands in VS Code PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit cache clear
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

5. Open `http://localhost:8503`, confirm **V14 — UNIVERSAL + FASTER**,
   select **General**, keep `auto` OCR and the Deep recheck toggle OFF.
   Upload a PDF and compare its result to the source page.

For scanned PDFs with heavy OCR needs, install/configure Tesseract as
documented in the previous project. You can choose PaddleOCR separately
if installed. For a specific missed field, use the QA source lookup or
turn on Deep recheck.

---
# PolicyLens V13.5 — Motor Schedule Accuracy

This update fixes the reported `car insurance 1.pdf` extraction failure while
preserving the General-first UI, 12 common explicit fields, dynamic discoveries,
manual-edit controls, page view and exports.

## New behavior
- `schedule_geometry.py`: reads nearby values using native PDF word coordinates,
  left/right columns, header-value grids, and dates including DD-MON-YYYY.
- Correctly distinguishes `Insured Name` from `Previous Insurer`, primary
  `Policy No` from `Previous Policy No`, insured address from the servicing
  office address, and `Total Premium` from `Gross Premium Paid`.
- Auto-extracts dynamically named vehicle fields such as Make, Model,
  Registration No., Engine No., Chassis No., Total IDV, and individual premium
  components from multi-column tables.
- Reduces irrelevant boilerplate candidates from insurance policy-wording
  pages (still a heuristic, not a trained document model).
- PDF values never fabricated: the PDF has no clearly labeled insured email,
  insured mobile or phone, and no separate universal Sum Insured; those common
  fields remain empty. The broker contact phone is not an insured mobile.
- New build V13.5 with fresh Streamlit editing state.

## Verified motor policy results (PAGE 2)
- Policy Number: 11300031210301872580
- Insurer Name: The New India Assurance Co. Ltd.
- Insured Name: MRS. SUBHASHINI P
- Insured Address: 10 JEYAM NAGAR TVS NAGAR ROAD,
  KAVUNDAMPALAYAM, COIMBATORE, TAMIL NADU-641030
- Policy Start Date: 04-JAN-2022
- Policy End Date: 03-JAN-2023
- Total Premium (A+B): 10,080
- Gross Premium Paid: 11,895
- Vehicle Total IDV: 373,766
- IGST: 1815

## Run on Windows
1. Back up your `Insurance_Streamlit` folder.
2. Extract the ZIP and copy the CONTENTS of `policylens_v13_5_motor_fixed`
   to `Insurance_Streamlit` replacing matching Python files; keep `.venv`.
3. Stop running Streamlit terminals. Run:
```
.\.venv\Scripts\python.exe -m streamlit cache clear
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```
4. Re-upload the PDF. Sidebar build should read V13.5.
5. `General` profile and "Show discovered fields" ON.

No Qwen, Ollama, QR decoding or paid API required. Native PyMuPDF,
optional PaddleOCR/Tesseract, geometry and validated field rules only.
No claim of universal bug-free extraction: review source evidence for
new layouts.

---
# PolicyLens V13.4 — Common Explicit + Dynamic Fields

## What changed
- Only 12 cross-insurance common fields are fixed/explicit: Policy Number,
  Policyholder Name, Insurer Name, Policy Start Date, Policy End Date,
  Insured Name, Insured Address, Email, Mobile Number, Phone Number,
  Sum Insured, Total Premium.
- All other supported PDF label/value candidates appear under
  **DYNAMIC / DISCOVERED FROM PDF** automatically, regardless of whether
  they appear in a prebuilt profile. No value is invented.
- One unified source-backed resolver handles both sections; exact aliases
  (e.g. Policy No. vs Policy Number, Proposal No vs Proposal Number)
  are deduplicated. Dynamic candidates may also fill common cards.
- General remains the default. Other categories are available as
  classification/organizational context, not restrictive schemas.
- Same PDF preview, status review, manual edits, source page links and exports.
- No Qwen, Ollama, QR code reading or generative API dependency.

## Verified
`test_unified_registry.py` passed against
`Student-Group-Insurance-Policy-2026.pdf`: Name of the Scheme,
Proposal Number and Policy Term from page 3; synthetic tests verified
alias deduplication and common-field reuse.

## Installation (Windows)
1. Back up your Insurance_Streamlit folder.
2. Extract this ZIP. Copy the CONTENTS of
   `policylens_v13_4_common_dynamic` into your Insurance_Streamlit
   folder, replacing old project files. Keep `.venv`.
3. Stop your existing Streamlit terminal (Ctrl+C), then run:

```powershell
.\.venv\Scripts\python.exe -m streamlit cache clear
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

Re-upload the PDF to refresh its indexed data. Check sidebar build V13.4.

## Limitations
Dynamic discovery is layout/text based, not model fine-tuning; it
cannot promise extraction of every unseen field from every PDF.
`Not Found` means no reliable candidate was produced, not that the PDF
definitively lacks that information. Source review remains available.

---

# PolicyLens V13.3 — Contact, Address & Field Accuracy Update

This release builds on the user's installed **V13.1 OCR PATH FIX** project and keeps the existing General-first, two-panel Streamlit UI.

## Changes

- Added `geometry_contacts.py`: source-backed **left vs right column** parsing for text-based insurance policy schedules.
- Separates the *insured/customer* contact from the insurer's *issuing office* contact, even if both share a `Tel. /Fax /Email` row.
- Extracts insured address (including continuation lines), email(s), mobile(s), and landline as separate fields. A phone number with extensions such as `080-23160532/33/35` is retained exactly as printed.
- Joins two **insured email addresses** when both appear, and flags the result as `Needs Review`.
- A **masked phone** (such as `XXXXXX5232//XXXXXX7770`) remains masked and is flagged for review. No missing digits are inferred.
- Improves names that wrap onto more than one line without accidentally appending GSTIN or the next section.
- Keeps `Present Address` and `Permanent Address` separate. If the PDF contains only `Address`, show it as **Insured Address**, not as a fabricated permanent address.
- Sets **Recheck missing fields against PDF tables = ON** by default.
- Uses V13.3-specific field widget state keys so stale empty fields from V13.1 don't mask newly extracted values.
- Retains existing PDF/OCR extraction, optional Tesseract/Paddle OCR, QA, checkbox detection and exports; no Qwen, Ollama or QR model.

## Windows installation

1. Stop Streamlit (`Ctrl + C`) in each active VS Code terminal.
2. Extract the ZIP, then copy its **contents** into `C:\Users\Saranyadheve\Desktop\Insurance_Streamlit`, overwriting matching files. Keep `.venv` unchanged.
3. Launch:

```powershell
.\.venv\Scripts\python.exe -m streamlit cache clear
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

4. Verify sidebar text **V13.3 — CONTACT & FIELD ACCURACY**, select **General**, and re-upload PDFs. The Tesseract executable auto-configuration from the previous hotfix is retained.

## Tests

Run `python test_contacts_v13_3.py` with the sample `health insurance 2.pdf` and `health insurance.pdf` in the parent folder. The test includes 13 field checks. The LIC Student Group policy's table-related fields were also directly checked.

## Important limitations

- This is rule- and layout-based extraction, not a trained document-understanding model. Some unseen layouts need more training/validation or separate layout parsers.
- Source-backed *Insured Address* does not prove a *Permanent Address* or *Present Address* exists. Those are left blank unless explicitly specified.
- Scanned pages rely on OCR quality; geometric extraction is primarily for native-text PDFs.
- If a PDF has masked phone numbers, show their printed masked representation and flag for review rather than guessing the digits.
- Review high-risk or ambiguous fields against source pages before relying on them.
