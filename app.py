import hashlib
import io
import json
import re

import pandas as pd
import pymupdf
import streamlit as st
from PIL import Image

from ocr_runtime import configure_tesseract
from app_pipeline import process_document
from vehicle_geometry import vehicle_records
from field_catalog import PROFILES, detect_type
from field_resolver import resolve_fields
from unified_fields import unified_fields
from qa_engine import ask
from live_lookup import direct_table_answer
from document_index import highlight_evidence
from ui_style import install
from small_table_patch import extract_small_table_fields
from ui_priority_bridge import apply_ui_source_priority

# =====================================================
# 1. APPLICATION CONFIGURATION
# =====================================================

BUILD = "PolicyLens V14.7 - UI Source-Priority Diagnostics"

PIPELINE_REVISION = "v147-ui-priority-20261124"

st.set_page_config(
    page_title="PolicyLens | Insurance Extraction",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)

install()


# ======================================================
# POLICYLENS - LIVE WEBSITE CONTRAST FIX
# ======================================================

st.markdown("""
<style>

/* Main page */
.stApp {
    background: #F8FAFC !important;
    color: #172033 !important;
}

[data-testid="stMain"] {
    color: #172033 !important;
}

/* Main labels, help text and captions */
[data-testid="stMain"] label,
[data-testid="stMain"] p,
[data-testid="stMain"] small,
[data-testid="stMain"] .stCaption,
[data-testid="stWidgetLabel"] {
    color: #263548 !important;
    opacity: 1 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #EAF1F4 !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption {
    color: #243447 !important;
    opacity: 1 !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #12283D !important;
}

/* Dropdowns */
[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #94A3B8 !important;
}

[data-baseweb="select"] span,
[data-baseweb="select"] input {
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
}

/* File uploader */
[data-testid="stFileUploader"] label {
    color: #172033 !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 1.5px dashed #94A3B8 !important;
    border-radius: 12px !important;
}

[data-testid="stFileUploaderDropzone"] * {
    color: #334155 !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] button {
    background: #155E75 !important;
    color: #FFFFFF !important;
    border: 1px solid #155E75 !important;
}

[data-testid="stFileUploaderDropzone"] button * {
    color: #FFFFFF !important;
}

/* Normal buttons */
.stButton button {
    background: #FFFFFF !important;
    color: #164E63 !important;
    border: 1px solid #94A3B8 !important;
    font-weight: 650 !important;
}

.stButton button p {
    color: inherit !important;
}

/* Form fields */
.stTextInput input,
.stTextArea textarea {
    background: #FFFFFF !important;
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
    border-radius: 8px !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #64748B !important;
    -webkit-text-fill-color: #64748B !important;
    opacity: 1 !important;
}

/* Text and headings inside cards */
[data-testid="stAlert"] {
    opacity: 1 !important;
}

/* Existing dark information cards */
.stApp [style*="background-color: rgb(30, 41, 59)"] {
    color: #FFFFFF !important;
}

/* Hero - retain attractive original styling */
.hero {
    opacity: 1 !important;
}

.hero-title {
    color: #13343D !important;
    opacity: 1 !important;
}

.hero-caption {
    color: #456773 !important;
    opacity: 1 !important;
}

.eyebrow {
    color: #A3482C !important;
    opacity: 1 !important;
}

/* Field section headers */
.section-pill {
    color: #075985 !important;
    background: #E0F2FE !important;
    font-weight: 800 !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #D4E0E8 !important;
    border-radius: 12px !important;
}

[data-testid="stMetricLabel"] * {
    color: #334155 !important;
}

[data-testid="stMetricValue"] {
    color: #0F766E !important;
}

/* Footer */
.footer-note {
    color: #475569 !important;
    opacity: 1 !important;
}

/* ==========================================
   POLICYLENS - FINAL TEXT VISIBILITY FIX
   ========================================== */

/* Success / diagnostic alerts: readable
   dark text on a light background */
[data-testid="stAlert"] {
    background-color: #E8F7EE !important;
    color: #14532D !important;
    border: 1px solid #86CDA4 !important;
    border-radius: 10px !important;
}

[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] svg {
    color: #14532D !important;
    opacity: 1 !important;
}

/* Uploaded filename and details */
[data-testid="stFileUploaderFile"] {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 9px !important;
}

[data-testid="stFileUploaderFile"] span,
[data-testid="stFileUploaderFile"] p,
[data-testid="stFileUploaderFileName"] {
    color: #172033 !important;
    opacity: 1 !important;
}

/* File list controls */
[data-testid="stFileUploaderFile"] button {
    color: #172033 !important;
}

/* Keep selected PDF readable */
[data-baseweb="select"] {
    color: #172033 !important;
}

</style>
""", unsafe_allow_html=True)


OCR_EXECUTABLE = configure_tesseract()


# =====================================================
# 2. EXISTING PIPELINE - PRESERVED
# =====================================================

@st.cache_data(
    show_spinner="Processing PDF and indexing fields...",
    max_entries=7,
)
def load_pdf(
    pdf_bytes,
    engine="auto",
    revision=PIPELINE_REVISION,
):
    return process_document(pdf_bytes, engine)


@st.cache_data(
    show_spinner=False,
    max_entries=80,
)
def page_image(
    pdf_bytes,
    page_number,
    scale=1.45,
    bbox=None,
):
    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf",
    ) as document:

        page = document[page_number - 1]

        if bbox and len(bbox) == 4:

            try:
                rect = pymupdf.Rect(bbox)

                if (
                    not rect.is_empty
                    and page.rect.intersects(rect)
                ):
                    page.draw_rect(
                        rect + (-2, -2, 2, 2),
                        color=(1, 0.57, 0),
                        fill=(1, 1, 0),
                        fill_opacity=0.36,
                        width=2.2,
                        overlay=True,
                    )

            except (TypeError, ValueError):
                pass

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(
                scale,
                scale,
            ),
            alpha=False,
        )

        return pix.tobytes("png")


def source_box(pdf_bytes, result):

    bbox = (
        result.get("bbox")
        or result.get("BBox")
    )

    if bbox and len(bbox) == 4:

        try:
            return tuple(
                float(number)
                for number in bbox
            )
        except (TypeError, ValueError):
            pass

    try:
        page_number = int(
            result.get("page") or 0
        )

        with pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf",
        ) as document:

            if not (
                1 <= page_number <= len(document)
            ):
                return None

            value = str(
                result.get("value", "")
            ).strip()

            if not value:
                return None

            matches = document[
                page_number - 1
            ].search_for(value)

            if matches:
                return tuple(
                    float(number)
                    for number in matches[0]
                )

    except (ValueError, TypeError):
        pass

    return None


def normkey(value):

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).lower(),
    ).strip("_")


def local_field_key(doc_id, field):

    # Preserve historical widget keys so previous
    # edits are not unnecessarily disturbed.
    return (
        f"edit_verified_v142_"
        f"{doc_id}_{normkey(field)}"
    )


def heading(value):

    st.markdown(
        (
            '<div class="section-pill">'
            f"{value.upper()}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def reset_fields(doc_id):

    prefix = (
        "edit_verified_v142_"
        + doc_id
        + "_"
    )

    for key in list(st.session_state):

        if key.startswith(prefix):
            del st.session_state[key]


def manual_rows(doc_id, resolved):

    rows = []

    for field, record in resolved.items():

        original_value = record.get(
            "value",
            "",
        )

        value = st.session_state.get(
            local_field_key(
                doc_id,
                field,
            ),
            original_value,
        )

        edited = value != original_value

        rows.append({
            "Field": field,
            "Value": value,
            "Status": (
                "Manually edited"
                if edited
                else record.get(
                    "status",
                    "review",
                )
            ),
            "Page": record.get("page") or "",
            "Person": record.get(
                "person",
                "",
            ),
            "Evidence": record.get(
                "evidence",
                "",
            ),
        })

    return rows


# =====================================================
# 3. SUPPLEMENTAL EXTRACTION INTEGRATION
# =====================================================

def merge_supplemental_fields(raw, common_fields, discovered_fields, resolved):
    """Add supplemental candidates without removing original extraction."""
    extra_table_records = extract_small_table_fields(raw)
    common_keys = {normkey(name) for name in common_fields}
    used_names = set(resolved)
    for record in extra_table_records:
        field = str(record.get("Field", "")).strip()
        value = str(record.get("Value", "")).strip()
        if not field or not value or normkey(field) in common_keys:
            continue
        if any(normkey(k) == normkey(field) and
               str(r.get("value", "")).strip() == value
               for k, r in resolved.items() if isinstance(r, dict)):
            continue
        display_field = field
        if display_field in used_names:
            display_field = f"{field} — source page {record.get('Page', '?')}"
        base = display_field
        suffix = 2
        while display_field in used_names:
            display_field = f"{base} ({suffix})"
            suffix += 1
        used_names.add(display_field)
        bbox = record.get("BBox")
        method = record.get("Method", "")
        # Presence of a bbox alone is not evidence of correct label/value pairing.
        verified_methods = {"motor-source-pattern", "premium-source-geometry"}
        resolved[display_field] = {
            "value": value,
            "status": "found" if bbox and method in verified_methods else "review",
            "page": record.get("Page"),
            "bbox": bbox,
            "evidence": record.get("Evidence", ""),
            "person": record.get("Person", ""),
        }
        discovered_fields.append(display_field)
    return discovered_fields, resolved, extra_table_records


def extract_engine_from_vehicle_row(pdf_bytes):
    """Find engine token directly left of chassis token on the same PDF row.

    Conservative recovery: each value has its own PDF word box. Does not
    depend on PDF text extraction order and avoids assigning chassis as engine.
    """
    results = []
    chassis_pattern = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.I)
    engine_pattern = re.compile(r"^(?=.*[A-Z])(?=.*\d)[A-Z0-9-]{7,20}$", re.I)
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_index, page in enumerate(doc):
            words = page.get_text("words")
            if not any("ENGINE" in str(w[4]).upper() for w in words):
                continue
            for ch in words:
                chassis = str(ch[4]).strip(" ,:;.")
                if not chassis_pattern.fullmatch(chassis) or not re.search(r"\d", chassis):
                    continue
                cx0, cy0, cx1, cy1 = ch[:4]
                possibles = []
                for w in words:
                    x0, y0, x1, y1 = w[:4]
                    token = str(w[4]).strip(" ,:;.")
                    if (x1 >= cx0 or cx0 - x1 > 140 or
                        abs((y0+y1)/2-(cy0+cy1)/2) > 6 or
                        not engine_pattern.fullmatch(token) or
                        chassis_pattern.fullmatch(token)):
                        continue
                    possibles.append((cx0-x1, token, (x0, y0, x1, y1)))
                if possibles:
                    possibles.sort(key=lambda item: item[0])
                    _, engine, bbox = possibles[0]
                    results.append({
                        "Field": "Engine Number", "Value": engine,
                        "Page": page_index + 1, "BBox": bbox,
                        "Evidence": f"Engine/chassis same row: {engine}",
                        "Method": "engine-row-geometry", "Person": "",
                    })
                    break
    return results


# =====================================================
# 4. VEHICLE SOURCE INTEGRATION
# =====================================================

def merge_vehicle_fields(
    raw,
    data,
    resolved,
):

    vehicle_sources = data.get(
        "vehicle_records",
        [],
    )

    if not vehicle_sources:

        vehicle_sources = list(
            vehicle_records(raw)
        )

    vehicle_names = []

    for item in vehicle_sources:

        name = str(
            item.get(
                "Field",
                "",
            )
        ).strip()

        value = str(
            item.get(
                "Value",
                "",
            )
        ).strip()

        if not name or not value:
            continue

        if (
            item.get("Method")
            != "vehicle table geometry"
        ):
            continue

        # Preserve the original verified
        # geometry-backed vehicle integration.
        resolved[name] = {
            "value": value,
            "page": item.get(
                "Page"
            ),
            "evidence": item.get(
                "Evidence",
                "",
            ),
            "person": item.get(
                "Person",
                "",
            ),
            "bbox": item.get(
                "BBox"
            ),
            "status": (
                "found"
                if item.get("BBox")
                else "review"
            ),
        }

        if name not in vehicle_names:

            vehicle_names.append(
                name
            )

    return (
        vehicle_names,
        vehicle_sources,
    )


# =====================================================
# 5. SIDEBAR
# =====================================================

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">
            POLICYLENS / DOCUMENT ANALYSIS STUDIO
        </div>
        <div class="hero-title">
            Insurance intelligence, without the clutter.
        </div>
        <div class="hero-caption">
            Read your PDF. Discover fields across changing
            layouts. Review every value alongside its source.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:

    st.markdown(
        "### ◈ PolicyLens"
    )

    st.caption(BUILD)

    st.divider()

    st.markdown(
        "**1 · Upload & extraction**"
    )

    engine = st.selectbox(
        "Text / OCR engine",
        [
            "auto",
            "tesseract",
            "paddle",
        ],
        help=(
            "Auto uses native PDF text, "
            "then optional OCR."
        ),
    )

    deep = st.toggle(
        "Deep recheck missing common fields (slower)",
        value=False,
    )

    st.caption(
        (
            "OCR: Tesseract found at "
            + str(OCR_EXECUTABLE)
        )
        if OCR_EXECUTABLE
        else (
            "OCR: Tesseract not detected; "
            "digital PDFs still supported."
        )
    )

    st.caption(
        "Local PDF parsing + optional OCR only. "
        "No generative models or external APIs."
    )

    st.divider()

    st.markdown(
        "**2 · Insurance coverage**"
    )

    profile_options = list(PROFILES)

    default_index = (
        profile_options.index("General")
        if "General" in profile_options
        else 0
    )

    profile_mode = st.selectbox(
        "Display profile",
        profile_options,
        index=default_index,
    )

    include_discovered = st.toggle(
        "Show discovered fields on the main panel",
        value=True,
    )

    st.divider()

    st.markdown(
        "**3 · Add a custom field**"
    )

    with st.form(
        "custom_field_form",
        clear_on_submit=True,
    ):

        custom_group = st.text_input(
            "Section",
            value="CUSTOM FIELDS",
        )

        custom_name = st.text_input(
            "Field name",
            placeholder="e.g. Add-on cover name",
        )

        add_custom = st.form_submit_button(
            "＋ Add field",
            width="stretch",
        )

    if add_custom and custom_name.strip():

        custom = st.session_state.setdefault(
            "custom_fields",
            [],
        )

        item = (
            custom_group.strip().upper()
            or "CUSTOM FIELDS",
            custom_name.strip(),
        )

        if item not in custom:
            custom.append(item)

    if st.session_state.get(
        "custom_fields"
    ):

        st.caption(
            f"{len(st.session_state['custom_fields'])} "
            "custom field(s)"
        )

        if st.button(
            "Clear custom fields",
            width="stretch",
        ):

            st.session_state[
                "custom_fields"
            ] = []

            st.rerun()

    st.divider()

    st.caption(
        "Manual edits remain in the active session "
        "and exported review files."
    )


# =====================================================
# 6. PDF UPLOAD
# =====================================================

files = st.file_uploader(
    "Upload insurance policy PDFs",
    type=["pdf"],
    accept_multiple_files=True,
)

if not files:
    
    st.markdown("""
    <style>
    .pl-step-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 25px 22px;
        min-height: 165px;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.035);
    }

    .pl-step-number {
        display: inline-block;
        background: #E6F4F1;
        color: #0F766E !important;
        border-radius: 7px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 15px;
    }

    .pl-step-title {
        color: #0F172A !important;
        font-size: 18px;
        font-weight: 750;
        margin-bottom: 9px;
    }

    .pl-step-description {
        color: #475569 !important;
        font-size: 14px;
        line-height: 1.65;
    }

    @media (max-width: 768px) {
        .pl-step-card {
            min-height: auto;
            margin-bottom: 12px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    a, b, c = st.columns(3, gap="medium")

    with a:
        st.markdown("""
        <div class="pl-step-card">
            <div class="pl-step-number">STEP 01</div>
            <div class="pl-step-title">Upload Document</div>
            <div class="pl-step-description">
                Choose an insurance policy PDF to begin
                extracting information.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with b:
        st.markdown("""
        <div class="pl-step-card">
            <div class="pl-step-number">STEP 02</div>
            <div class="pl-step-title">Extract Information</div>
            <div class="pl-step-description">
                Identify policy details, tables and
                available source values.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c:
        st.markdown("""
        <div class="pl-step-card">
            <div class="pl-step-number">STEP 03</div>
            <div class="pl-step-title">Review & Export</div>
            <div class="pl-step-description">
                Review extracted fields, inspect PDF
                evidence and export your results.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.stop()


    a, b, c = st.columns(3)

    with a:
        st.info(
            "**01 · Upload**\n\n"
            "Upload an insurance PDF."
        )

    with b:
        st.info(
            "**02 · Extract**\n\n"
            "Read fields, tables and source values."
        )

    with c:
        st.info(
            "**03 · Review**\n\n"
            "Check sources, edit and export."
        )

    st.stop()


selected_file = st.selectbox(
    "Open document",
    [item.name for item in files],
    label_visibility="collapsed",
)

uploaded_file = next(
    item
    for item in files
    if item.name == selected_file
)

raw = uploaded_file.getvalue()

doc_id = hashlib.sha256(
    raw
).hexdigest()[:12]

if len(raw) > 35 * 1024 * 1024:

    st.error(
        "PDF exceeds 35 MB."
    )

    st.stop()


# =====================================================
# 7. ORIGINAL DOCUMENT PROCESSING
# =====================================================

try:

    data = load_pdf(
        raw,
        engine,
        revision=PIPELINE_REVISION,
    )

except Exception as error:

    st.error(
        "Unable to process this PDF: "
        f"{type(error).__name__}: {error}"
    )

    st.stop()


with pymupdf.open(
    stream=raw,
    filetype="pdf",
) as document:

    pages = len(document)


detected = detect_type(
    " ".join(
        data.get(
            "pages",
            [],
        )[:8]
    )
)

kind = profile_mode


# =====================================================
# 8. ORIGINAL EXPLICIT + DYNAMIC EXTRACTION
# =====================================================

common_fields, discovered_fields, resolved = (
    unified_fields(
        data,
        raw_pdf=raw,
        deep_search=deep,
    )
)

# Convert to mutable containers.
common_fields = list(common_fields)
discovered_fields = list(discovered_fields)
resolved = dict(resolved)


# =====================================================
# 9. SUPPLEMENTAL ALL-PAGE TABLE EXTRACTION
# =====================================================

try:

    (
        discovered_fields,
        resolved,
        extra_table_records,
    ) = merge_supplemental_fields(
        raw,
        common_fields,
        discovered_fields,
        resolved,
    )

except Exception as error:

    # Preserve the original pipeline output
    # if the supplemental extractor fails.
    extra_table_records = []

    st.warning(
        "Supplemental table extraction "
        f"could not complete: {error}"
    )


# =====================================================
# 10. VEHICLE GEOMETRY
# =====================================================

try:

    (
        vehicle_names,
        vehicle_sources,
    ) = merge_vehicle_fields(
        raw,
        data,
        resolved,
    )

except Exception as error:

    vehicle_names = []
    vehicle_sources = []

    st.warning(
        "Vehicle table extraction "
        f"could not complete: {error}"
    )


# -----------------------------------------------------
# Conservative engine correction AFTER vehicle geometry
# -----------------------------------------------------
try:
    chassis_value = str(resolved.get("Chassis Number", {}).get("value", "")).strip().upper()
    for engine_record in extract_engine_from_vehicle_row(raw):
        engine_value = str(engine_record.get("Value", "")).strip().upper()
        if (not engine_value or not engine_record.get("BBox") or
            engine_value == chassis_value or len(engine_value) == 17):
            continue
        resolved["Engine Number"] = {
            "value": engine_value,
            "status": "review",
            "page": engine_record["Page"],
            "bbox": engine_record["BBox"],
            "evidence": engine_record["Evidence"],
            "person": "",
        }
        if "Engine Number" not in discovered_fields:
            discovered_fields.append("Engine Number")
        # Clear old session widget ONLY if it contains the known wrong chassis value.
        edit_key = local_field_key(doc_id, "Engine Number")
        if (edit_key in st.session_state and
            str(st.session_state[edit_key]).strip().upper() == chassis_value):
            del st.session_state[edit_key]
        break
except Exception as error:
    st.warning(f"Engine Number correction issue: {error}")


# =====================================================
# SOURCE-CHECKED VEHICLE + POLICY TABLE PRIORITY
# Runs only when the PDF actually has a motor vehicle table.
# Original pipeline and records remain untouched otherwise.
# =====================================================
verified_ui_report = {"phase": "not executed", "vehicle_count": 0, "error": ""}
try:
    verified_vehicle_names, verified_ui_report = apply_ui_source_priority(
        raw, common_fields, discovered_fields, resolved
    )
    if verified_vehicle_names:
        vehicle_names = list(dict.fromkeys(verified_vehicle_names))
    # Clear session widget values only when they still equal the stale
    # automatically extracted value (preserves independent manual changes).
    for field, old, new in verified_ui_report.get("updates", []):
        edit_key = local_field_key(doc_id, field)
        if edit_key in st.session_state and str(st.session_state[edit_key]) == str(old):
            del st.session_state[edit_key]
    for field, stale_values in {
        "Registration Number": {"vehicle"},
        "Engine Number": {str(resolved.get("Chassis Number", {}).get("value", "")).lower()},
        "Sum Insured": {"policyschedule"},
    }.items():
        edit_key = local_field_key(doc_id, field)
        if edit_key in st.session_state:
            old_display = str(st.session_state[edit_key]).strip().lower().replace(" ", "")
            new_display = str(resolved.get(field, {}).get("value", "")).strip().lower().replace(" ", "")
            if old_display in stale_values and old_display != new_display:
                del st.session_state[edit_key]
except Exception as error:
    verified_ui_report["phase"] = "UI integration failed"
    verified_ui_report["error"] = f"{type(error).__name__}: {error}"
    st.exception(error)


# =====================================================
# 11. CUSTOM FIELD RESOLUTION
# =====================================================

for (
    custom_group,
    custom_name,
) in st.session_state.get(
    "custom_fields",
    [],
):

    if custom_name in resolved:
        continue

    extra = resolve_fields(
        [custom_name],
        data,
        raw,
        deep_search=deep,
    )

    resolved.update(extra)

    discovered_fields.append(
        custom_name
    )


# =====================================================
# 12. BUILD VISIBLE FIELD GROUPS
# =====================================================

seen_labels = {
    normkey(field)
    for field in common_fields
}

dynamic_unique = []

for field in discovered_fields:

    normalized = normkey(field)

    if field not in resolved:
        continue

    if normalized in seen_labels:
        continue

    dynamic_unique.append(
        field
    )

    seen_labels.add(
        normalized
    )


profile = {
    "COMMON / EXPLICIT FIELDS": [
        field
        for field in common_fields
        if field in resolved
    ]
}

common_keys = {
    normkey(field)
    for field in common_fields
}

vehicle_names = [
    name
    for name in vehicle_names
    if name in resolved
    and normkey(name) not in common_keys
]

if vehicle_names:

    profile[
        "VEHICLE DETAILS / VERIFIED PDF TABLE"
    ] = vehicle_names


vehicle_keys = {
    normkey(name)
    for name in vehicle_names
}

if include_discovered:

    visible_dynamic = [
        field
        for field in dynamic_unique
        if (
            normkey(field) not in vehicle_keys
            and field in resolved
        )
    ]

    if visible_dynamic:

        profile[
            "DYNAMIC / DISCOVERED FROM PDF"
        ] = visible_dynamic


all_fields = list(
    dict.fromkeys(
        field
        for fields in profile.values()
        for field in fields
    )
)


# =====================================================
# 13. SUMMARY AND DIAGNOSTICS
# =====================================================

stats = st.columns([
    1.2,
    1,
    1,
    1.4,
])

with stats[0]:
    st.metric(
        "AUTO-DETECTED",
        detected,
    )

with stats[1]:
    st.metric(
        "PAGES",
        pages,
    )

with stats[2]:
    st.metric(
        "FOUND / REVIEW",
        sum(
            record.get("status") != "not_found"
            for record in resolved.values()
        ),
    )

with stats[3]:
    st.metric(
        "VISIBLE FIELDS",
        len(all_fields),
    )


# Always show source-verified integration status (not only in Debug).
if verified_ui_report.get("vehicle_count", 0):
    st.success(
        "Verified vehicle table loaded: "
        f"{verified_ui_report['vehicle_count']} source-backed fields "
        f"({verified_ui_report.get('phase', '')})."
    )
else:
    st.error(
        "Verified vehicle table did not reach the UI. "
        f"Phase: {verified_ui_report.get('phase', 'unknown')}. "
        f"Details: {verified_ui_report.get('error', 'not reported')}"
    )
with st.expander("Source priority diagnostics", expanded=False):
    st.json(verified_ui_report)
    st.write("Engine Number in registry:", resolved.get("Engine Number"))
    st.write("Vehicle field names:", vehicle_names)
    st.write("Dynamic candidates:", len(discovered_fields))

st.caption(
    f"Active display profile: **{kind}** "
    f"· Detected document type: **{detected}** "
    f"· Build: **{BUILD}**"
)


page_counts = {
    number: 0
    for number in range(
        1,
        pages + 1,
    )
}

for record in data.get(
    "geometry_records",
    [],
):

    number = record.get(
        "Page"
    )

    if number in page_counts:
        page_counts[number] += 1


with st.expander(
    "Extraction diagnostics — every page",
    expanded=False,
):

    diagnostics = []

    for page_number in range(
        1,
        pages + 1,
    ):

        supplemental_count = sum(
            1
            for record in extra_table_records
            if record.get("Page") == page_number
        )

        vehicle_count = sum(
            1
            for record in vehicle_sources
            if record.get("Page") == page_number
        )

        diagnostics.append({
            "Page": page_number,
            "Geometry candidates": page_counts[
                page_number
            ],
            "Supplemental candidates": supplemental_count,
            "Vehicle candidates": vehicle_count,
        })

    st.dataframe(
        pd.DataFrame(diagnostics),
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "Unpaired source cells: "
        + str(
            len(
                data.get(
                    "unpaired_cells",
                    [],
                )
            )
        )
        + " · Source fields in registry: "
        + str(len(resolved))
    )


# =====================================================
# 14. PDF PREVIEW + EXTRACTED FIELDS
# =====================================================

left, right = st.columns(
    [0.49, 0.51],
    gap="medium",
)


with left:

    st.markdown(
        "### 01 / Original PDF"
    )

    st.caption(
        "Click a field's View control "
        "to jump to its source page."
    )

    nav = st.columns(
        [0.95, 0.95, 2.2]
    )

    pgkey = (
        "source_page_"
        + doc_id
    )

    choice_key = (
        "page_choice_"
        + doc_id
    )

    markkey = (
        "highlight_value_"
        + doc_id
    )

    pending_key = (
        "pending_source_page_"
        + doc_id
    )

    if pgkey not in st.session_state:

        st.session_state[
            pgkey
        ] = 1

    # Consume pending navigation BEFORE selectbox.
    if pending_key in st.session_state:

        requested = st.session_state.pop(
            pending_key
        )

        requested = max(
            1,
            min(
                pages,
                int(requested),
            ),
        )

        st.session_state[
            pgkey
        ] = requested

        st.session_state[
            choice_key
        ] = requested

    if choice_key not in st.session_state:

        st.session_state[
            choice_key
        ] = st.session_state[
            pgkey
        ]

    with nav[0]:

        if st.button(
            "◀ Previous",
            width="stretch",
        ):

            new_page = max(
                1,
                int(
                    st.session_state[
                        pgkey
                    ]
                ) - 1,
            )

            st.session_state[
                pgkey
            ] = new_page

            st.session_state[
                choice_key
            ] = new_page

            st.session_state.pop(
                markkey,
                None,
            )

            st.rerun()

    with nav[1]:

        if st.button(
            "Next ▶",
            width="stretch",
        ):

            new_page = min(
                pages,
                int(
                    st.session_state[
                        pgkey
                    ]
                ) + 1,
            )

            st.session_state[
                pgkey
            ] = new_page

            st.session_state[
                choice_key
            ] = new_page

            st.session_state.pop(
                markkey,
                None,
            )

            st.rerun()

    with nav[2]:

        chosen = st.selectbox(
            "Page",
            list(
                range(
                    1,
                    pages + 1,
                )
            ),
            key=choice_key,
            format_func=lambda page: (
                f"Page {page} of {pages}"
            ),
            label_visibility="collapsed",
        )

        if chosen != st.session_state[pgkey]:

            st.session_state[
                pgkey
            ] = chosen

            st.session_state.pop(
                markkey,
                None,
            )

    mark = st.session_state.get(
        markkey
    )

    bbox = None

    if mark and (
        mark.get("page")
        == st.session_state[pgkey]
    ):
        bbox = mark.get(
            "bbox"
        )

    with st.container(
        height=720,
        border=True,
    ):

        image_bytes = page_image(
            raw,
            st.session_state[
                pgkey
            ],
            bbox=bbox,
        )

        st.image(
            Image.open(
                io.BytesIO(
                    image_bytes
                )
            ),
            width="stretch",
        )

        if bbox:

            st.caption(
                "🟨 Highlighted source: "
                + str(
                    mark.get(
                        "field",
                        "",
                    )
                )
            )

        elif mark and (
            mark.get("page")
            == st.session_state[pgkey]
        ):

            st.caption(
                "Source page opened; exact "
                "text position not found."
            )

        st.caption(
            f"{selected_file} · "
            f"Page {st.session_state[pgkey]}"
        )

    with st.expander(
        "Read extracted page text"
    ):

        current_page = (
            st.session_state[
                pgkey
            ] - 1
        )

        page_texts = data.get(
            "pages",
            [],
        )

        current_text = (
            page_texts[current_page]
            if current_page < len(page_texts)
            else ""
        )

        st.text_area(
            "Source text",
            current_text,
            height=180,
            label_visibility="collapsed",
        )

    st.download_button(
        "Download original PDF",
        data=raw,
        file_name=selected_file,
        mime="application/pdf",
        width="stretch",
    )


# =====================================================
# 15. EDITABLE FIELD CARDS
# =====================================================

with right:

    st.markdown(
        "### 02 / Extracted & editable fields"
    )

    st.caption(
        "Found = source-backed candidate · "
        "Review = uncertain · "
        "Missing = no reliable value · "
        "Manual = changed by you."
    )

    actions = st.columns(
        [1, 1.25]
    )

    with actions[0]:

        if st.button(
            "↺ Reset manual edits",
            width="stretch",
        ):

            reset_fields(
                doc_id
            )

            st.rerun()

    with actions[1]:

        filter_mode = st.selectbox(
            "Filter",
            [
                "All fields",
                "Found / review",
                "Not found",
            ],
            label_visibility="collapsed",
        )

    with st.container(
        height=730,
        border=True,
    ):

        for group, fields in profile.items():

            display_fields = []

            for field in fields:

                if field not in resolved:
                    continue

                record = resolved[field]

                status_value = record.get(
                    "status",
                    "review",
                )

                if filter_mode == "All fields":

                    display_fields.append(
                        field
                    )

                elif (
                    filter_mode == "Found / review"
                    and status_value != "not_found"
                ):

                    display_fields.append(
                        field
                    )

                elif (
                    filter_mode == "Not found"
                    and status_value == "not_found"
                ):

                    display_fields.append(
                        field
                    )

            if not display_fields:
                continue

            heading(
                group
            )

            for index in range(
                0,
                len(display_fields),
                2,
            ):

                cols = st.columns(
                    2,
                    gap="small",
                )

                batch = display_fields[
                    index:index + 2
                ]

                for column_index, field in enumerate(batch):

                    record = resolved[
                        field
                    ]

                    key = local_field_key(
                        doc_id,
                        field,
                    )

                    original_value = record.get(
                        "value",
                        "",
                    )

                    if key not in st.session_state:

                        st.session_state[
                            key
                        ] = original_value

                    manual = (
                        st.session_state[key]
                        != original_value
                    )

                    status_value = record.get(
                        "status",
                        "review",
                    )

                    if manual:
                        status_text = "MANUALLY EDITED"

                    elif status_value == "found":
                        status_text = "FOUND IN PDF"

                    elif status_value == "review":
                        status_text = "NEEDS REVIEW"

                    else:
                        status_text = "NOT FOUND"

                    if (
                        manual
                        or status_value == "found"
                    ):
                        css_class = "status-good"

                    elif status_value == "review":
                        css_class = "status-review"

                    else:
                        css_class = "status-missing"

                    with cols[column_index]:

                        with st.container(
                            border=True
                        ):

                            st.markdown(
                                (
                                    f'<div class="{css_class}">'
                                    f"{status_text}"
                                    "</div>"
                                ),
                                unsafe_allow_html=True,
                            )

                            page_number = record.get(
                                "page"
                            )

                            evidence = str(
                                record.get(
                                    "evidence",
                                    "",
                                ) or ""
                            )

                            st.text_input(
                                field,
                                key=key,
                                placeholder=(
                                    "Not found — enter manually"
                                ),
                                help=(
                                    f"Source: page "
                                    f"{page_number or 'unknown'} "
                                    f"| {evidence[:180]}"
                                ),
                            )

                            if page_number:

                                button_key = (
                                    "view_"
                                    + doc_id
                                    + "_"
                                    + normkey(field)
                                )

                                if st.button(
                                    f"◉ View page {page_number}",
                                    key=button_key,
                                    width="stretch",
                                ):

                                    target_page = max(
                                        1,
                                        min(
                                            pages,
                                            int(page_number),
                                        ),
                                    )

                                    st.session_state[
                                        pending_key
                                    ] = target_page

                                    st.session_state[
                                        markkey
                                    ] = {
                                        "page": target_page,
                                        "field": field,
                                        "bbox": source_box(
                                            raw,
                                            record,
                                        ),
                                    }

                                    st.rerun()

                            elif manual:

                                st.caption(
                                    "Manually entered · "
                                    "no PDF evidence"
                                )

            st.markdown("")


# =====================================================
# 16. ASK THIS DOCUMENT
# =====================================================

st.divider()

st.markdown(
    "### 03 / Ask this document"
)

question = st.text_input(
    "Ask a question",
    placeholder=(
        "e.g. Engine Number / Policy Term / "
        "GST Amount / Vehicle Registration"
    ),
)

if question.strip():

    try:

        answer = ask(
            question,
            data,
        )

        hits = answer.get(
            "answers",
            [],
        )

        if not hits:

            hits = direct_table_answer(
                raw,
                question,
            )

        if hits:

            show = pd.DataFrame([
                {
                    "Field": item["Field"],
                    "Answer": item["Value"],
                    "Person": item.get(
                        "Person",
                        "",
                    ),
                    "Page": item.get(
                        "Page",
                        "",
                    ),
                }
                for item in hits[:12]
            ])

            st.dataframe(
                show,
                hide_index=True,
                width="stretch",
            )

            highlighted_pdf, count = (
                highlight_evidence(
                    raw,
                    hits,
                )
            )

            if highlighted_pdf:

                st.download_button(
                    "Download highlighted evidence PDF",
                    highlighted_pdf,
                    "highlighted_evidence.pdf",
                    "application/pdf",
                )

        else:

            st.warning(
                "No verified answer extracted. "
                "Check the source PDF."
            )

    except Exception as error:

        st.warning(
            "Question lookup could not complete: "
            + str(error)
        )


# =====================================================
# 17. ADDITIONAL RECORDS
# =====================================================

st.markdown(
    "### 04 / Additional records"
)

st.caption(
    "View additional indexed source records "
    "without changing the main field registry."
)


with st.expander(
    "Browse all extracted label–value pairs"
):

    existing = {
        normkey(field)
        for field in all_fields
    }

    source_records = (
        data.get(
            "contact_records",
            [],
        )
        + data.get(
            "indexed_records",
            [],
        )
    )

    extras = []

    for record in source_records:

        field = str(
            record.get(
                "Field",
                "",
            )
        )

        if normkey(field) in existing:
            continue

        extras.append({
            "Field": field,
            "Value": record.get(
                "Value",
                "",
            ),
            "Person": record.get(
                "Person",
                "",
            ),
            "Page": record.get(
                "Page",
                "",
            ),
        })

    if extras:

        extra_df = (
            pd.DataFrame(extras)
            .drop_duplicates()
            .head(500)
        )

        st.dataframe(
            extra_df,
            hide_index=True,
            width="stretch",
        )

    else:

        st.info(
            "No additional candidates found."
        )


with st.expander(
    "Browse unpaired source cells — all PDF pages"
):

    st.caption(
        "These are not verified field/value pairs. "
        "They are available for manual source review."
    )

    raw_cells = data.get(
        "unpaired_cells",
        [],
    )

    if raw_cells:

        st.dataframe(
            pd.DataFrame(
                raw_cells
            ).drop(
                columns=["BBox"],
                errors="ignore",
            ),
            hide_index=True,
            width="stretch",
        )

    else:

        st.info(
            "No unpaired table cells found."
        )


with st.expander(
    "DEBUG - Supplemental and vehicle fields",
    expanded=False,
):

    st.write(
        "Supplemental candidate count:",
        len(extra_table_records),
    )

    st.write(
        "Vehicle source count:",
        len(vehicle_sources),
    )

    st.dataframe(
        pd.DataFrame(extra_table_records),
        hide_index=True,
        width="stretch",
    )

    st.dataframe(
        pd.DataFrame(vehicle_sources),
        hide_index=True,
        width="stretch",
    )


# =====================================================
# 18. EXPORT REVIEW
# =====================================================

st.markdown(
    "### 05 / Export your review"
)

rows = manual_rows(
    doc_id,
    resolved,
)

export = pd.DataFrame(
    rows
)

export.insert(
    0,
    "Document",
    selected_file,
)

export.insert(
    1,
    "Display Profile",
    kind,
)

c1, c2, c3 = st.columns(3)


with c1:

    st.download_button(
        "Download CSV",
        export.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="reviewed_insurance_fields.csv",
        mime="text/csv",
        width="stretch",
    )


with c2:

    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl",
    ) as writer:

        export.to_excel(
            writer,
            sheet_name="Reviewed Fields",
            index=False,
        )

    st.download_button(
        "Download Excel",
        excel_buffer.getvalue(),
        file_name="reviewed_insurance_fields.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        width="stretch",
    )


with c3:

    json_content = json.dumps(
        {
            "document": selected_file,
            "display_profile": kind,
            "detected_type": detected,
            "fields": rows,
        },
        ensure_ascii=False,
        indent=2,
    )

    st.download_button(
        "Download JSON",
        json_content.encode(
            "utf-8"
        ),
        file_name="reviewed_insurance_fields.json",
        mime="application/json",
        width="stretch",
    )


st.markdown(
    (
        '<div class="footer-note">'
        "Original PDF stays unchanged. "
        "Common fields and dynamic fields "
        "share the same review registry. "
        "Source evidence can be inspected "
        "before accepting extracted values."
        "</div>"
    ),
    unsafe_allow_html=True,
)
