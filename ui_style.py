
"""
PolicyLens - Clean Professional UI
Unified light design system for Streamlit.

Only changes presentation.
Does not modify PDF extraction or backend logic.
"""

import streamlit as st


def install():
    st.markdown(
        """
<style>

/* ============================================
   1. DESIGN TOKENS
============================================ */

:root {
    --pl-bg: #F5F7FB;
    --pl-surface: #FFFFFF;
    --pl-sidebar: #F0F4F8;
    --pl-text: #0F172A;
    --pl-muted: #475569;
    --pl-border: #DFE6EE;
    --pl-primary: #0F766E;
    --pl-primary-dark: #115E59;
    --pl-soft: #E8F5F2;
}

/* ============================================
   2. MAIN PAGE
============================================ */

html,
body,
[data-testid="stAppViewContainer"],
.stApp {
    background: var(--pl-bg) !important;
    color: var(--pl-text) !important;
    font-family: Inter, "Segoe UI", Arial, sans-serif;
}

[data-testid="stMain"] {
    background: var(--pl-bg) !important;
}

.block-container {
    max-width: 1450px !important;
    padding-top: 2.2rem !important;
    padding-bottom: 3rem !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--pl-text) !important;
    letter-spacing: -0.4px;
}

[data-testid="stMain"] > div {
    color: var(--pl-text);
}

/* ============================================
   3. SIDEBAR
============================================ */

[data-testid="stSidebar"] {
    background: var(--pl-sidebar) !important;
    border-right: 1px solid var(--pl-border) !important;
}

[data-testid="stSidebar"] > div {
    background: transparent !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--pl-text) !important;
    opacity: 1 !important;
}

[data-testid="stSidebar"] hr {
    border-color: #D5DEE8 !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #64748B !important;
}

/* ============================================
   4. HERO BANNER
============================================ */

.hero {
    background: linear-gradient(
        120deg,
        #FFFFFF 0%,
        #F0F9F7 100%
    ) !important;

    border: 1px solid #D8E9E4 !important;
    border-left: 5px solid var(--pl-primary) !important;
    border-radius: 16px !important;
    padding: 30px 36px !important;
    margin-bottom: 26px !important;

    box-shadow: 0 5px 22px rgba(
        15, 23, 42, 0.035
    ) !important;

    opacity: 1 !important;
}

.hero .eyebrow,
.eyebrow {
    color: var(--pl-primary) !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    opacity: 1 !important;
}

.hero .hero-title,
.hero-title {
    color: #0F172A !important;
    font-size: clamp(25px, 3vw, 35px) !important;
    font-weight: 800 !important;
    letter-spacing: -1.2px !important;
    line-height: 1.2 !important;
    margin: 12px 0 !important;
    opacity: 1 !important;
}

.hero .hero-caption,
.hero-caption {
    color: #475569 !important;
    font-size: 15px !important;
    line-height: 1.65 !important;
    opacity: 1 !important;
}

/* ============================================
   5. LABELS AND CAPTIONS
============================================ */

[data-testid="stWidgetLabel"] p,
[data-testid="stFileUploader"] label,
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label {
    color: #1E293B !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #64748B !important;
    opacity: 1 !important;
}

/* ============================================
   6. FILE UPLOADER
============================================ */

[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 1.5px dashed #B8CDD5 !important;
    border-radius: 14px !important;
    padding: 12px !important;
}

[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small {
    color: #475569 !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] button {
    background: var(--pl-primary) !important;
    border: 1px solid var(--pl-primary) !important;
    color: #FFFFFF !important;
    border-radius: 9px !important;
    font-weight: 650 !important;
}

[data-testid="stFileUploaderDropzone"] button *,
[data-testid="stFileUploaderDropzone"] button p {
    color: #FFFFFF !important;
}

[data-testid="stFileUploaderFile"] {
    background: #F8FAFC !important;
    border-radius: 9px !important;
}

[data-testid="stFileUploaderFile"] p,
[data-testid="stFileUploaderFile"] span {
    color: #1E293B !important;
    opacity: 1 !important;
}

/* ============================================
   7. SELECTBOX
============================================ */

[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    border: 1px solid #CAD5E2 !important;
    border-radius: 10px !important;
    color: #0F172A !important;
    min-height: 44px !important;
}

[data-baseweb="select"] span,
[data-baseweb="select"] input,
[data-baseweb="select"] svg {
    color: #0F172A !important;
    fill: #334155 !important;
    -webkit-text-fill-color: #0F172A !important;
}

[data-baseweb="popover"] ul {
    background: #FFFFFF !important;
}

[data-baseweb="popover"] li {
    color: #0F172A !important;
}

/* ============================================
   8. INPUTS
============================================ */

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #FFFFFF !important;
    color: #0F172A !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 9px !important;
    -webkit-text-fill-color: #0F172A !important;
}

input::placeholder,
textarea::placeholder {
    color: #94A3B8 !important;
    opacity: 1 !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--pl-primary) !important;
    box-shadow: 0 0 0 2px #D1FAE5 !important;
}

/* ============================================
   9. BUTTONS
============================================ */

.stButton button {
    background: #FFFFFF !important;
    color: var(--pl-primary-dark) !important;
    border: 1px solid #BFD7D0 !important;
    border-radius: 9px !important;
    font-weight: 650 !important;
    transition: background 0.18s ease,
                border-color 0.18s ease !important;
}

.stButton button p,
.stButton button span {
    color: inherit !important;
}

.stButton button:hover {
    background: #E8F5F2 !important;
    border-color: var(--pl-primary) !important;
}

.stDownloadButton button {
    background: var(--pl-primary) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 650 !important;
}

.stDownloadButton button p,
.stDownloadButton button span {
    color: #FFFFFF !important;
}

/* ============================================
   10. INFO, SUCCESS AND WARNING CARDS

   Fixes the dark navy + dark green issue.
============================================ */

[data-testid="stAlert"] {
    background: #FFFFFF !important;
    color: #0F172A !important;
    border: 1px solid #DCE5ED !important;
    border-left: 4px solid #0F766E !important;
    border-radius: 12px !important;
    box-shadow: 0 3px 12px rgba(
        15, 23, 42, 0.025
    ) !important;
    opacity: 1 !important;
}

[data-testid="stAlert"] [data-baseweb="notification"],
[data-testid="stAlert"] [data-testid="stNotification"] {
    background: transparent !important;
    color: #0F172A !important;
}

[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] strong,
[data-testid="stAlert"] h3,
[data-testid="stAlert"] h4,
[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] {
    color: #0F172A !important;
    opacity: 1 !important;
}

[data-testid="stAlert"] a {
    color: #0F766E !important;
    text-decoration: underline !important;
}

/* Notification icons */
[data-testid="stAlert"] svg {
    color: #0F766E !important;
}

/* ============================================
   11. METRIC CARDS
============================================ */

[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #E0E7EF !important;
    border-radius: 13px !important;
    padding: 18px !important;
    box-shadow: 0 3px 12px rgba(
        15, 23, 42, 0.02
    ) !important;
}

[data-testid="stMetricLabel"] p {
    color: #64748B !important;
    font-size: 12px !important;
    font-weight: 650 !important;
}

[data-testid="stMetricValue"] {
    color: #0F766E !important;
    font-weight: 750 !important;
}

/* ============================================
   12. EXTRACTED FIELD SECTIONS
============================================ */

.section-pill {
    background: #EAF5F2 !important;
    color: #115E59 !important;
    padding: 11px 15px !important;
    border-radius: 9px !important;
    margin: 16px 0 10px !important;
    font-size: 12px !important;
    letter-spacing: 0.6px !important;
    font-weight: 800 !important;
    opacity: 1 !important;
}

.status-good {
    color: #166534 !important;
    font-weight: 750 !important;
    font-size: 11px !important;
}

.status-review {
    color: #A16207 !important;
    font-weight: 750 !important;
    font-size: 11px !important;
}

.status-missing {
    color: #B91C1C !important;
    font-weight: 750 !important;
    font-size: 11px !important;
}

/* ============================================
   13. EXPANDERS AND CONTAINERS
============================================ */

[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 11px !important;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #1E293B !important;
    font-weight: 600 !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
}

/* ============================================
   14. TABLES
============================================ */

[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden;
    border: 1px solid #E2E8F0 !important;
}

/* ============================================
   15. FOOTER
============================================ */

.footer-note {
    color: #64748B !important;
    font-size: 12px !important;
    text-align: center;
    padding: 22px 0;
    opacity: 1 !important;
}

/* ============================================
   16. MOBILE RESPONSIVENESS
============================================ */

@media (max-width: 768px) {

    .block-container {
        padding: 1rem !important;
    }

    .hero {
        padding: 22px !important;
        border-radius: 12px !important;
    }

    .hero-title {
        font-size: 25px !important;
    }

    .hero-caption {
        font-size: 13px !important;
    }
}

</style>
        """,
        unsafe_allow_html=True,
    )
