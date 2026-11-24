
"""Clean table-derived field records before displaying them.

Preserves other extraction engines. Rejects row/column mispairing,
corrupted dates, duplicated candidates, and person headings used
as field names.

Requires: PyMuPDF.
"""

import re
from datetime import datetime

import pymupdf


DATE_FIELDS = {
    "dateofbirth", "dob",
    "policydate", "policy start date",
    "policy end date", "expirydate",
    "proposaldate", "renewaldate",
    "dateofcommencementofpolicy"
}

PERSON_HEADER = re.compile(
    r"\b(?:\d+(?:st|nd|rd|th)\s*)?"
    r"insured\s*person\b",
    re.I
)

PERSON_ROWS = {
    "name", "dateofbirth", "gender",
    "maritalstatus", "abhaid", "occupation",
    "aadhaarno", "bloodgroup", "heightcm",
    "weightkg", "dependent",
    "relationwithproposer",
    "sumininsuredifindbasis",
}


def compact(text):
    return re.sub(
        r"[^a-z0-9]", "",
        str(text or "").lower()
    )


def clean(text):
    return " ".join(str(text or "").split())


def valid_date(value):
    value = clean(value)

    # Reject OCR-corrupted/overlapping dates.
    if not re.fullmatch(
        r"\d{1,2}[/-]\d{1,2}[/-]\d{4}",
        value
    ):
        return False

    for pattern in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            datetime.strptime(value, pattern)
            return True
        except ValueError:
            pass

    return False


def invalid_record(record):
    field = clean(record.get("Field"))
    value = clean(record.get("Value"))

    if not field or not value:
        return True

    if value.upper() in {"NA", "N/A", "NONE"}:
        return True

    if compact(field) == compact(value):
        return True

    if "insuredperson" in compact(value):
        return True

    # Wrong pair: Name -> DateofBirth.
    if compact(field) in {
        "name", "insuredname", "customername"
    } and compact(value) in PERSON_ROWS:
        return True

    # Wrong pair: a person's name became a field,
    # and a damaged DOB became the value.
    if (
        re.search(r"\d{1,2}/\d{1,2}/", value)
        and re.search(r"[A-Za-z]", value)
        and not re.search(r"[A-Za-z]{3}\s+\d{4}", value)
    ):
        return True

    if compact(field) in DATE_FIELDS:
        if not valid_date(value):
            return True

    # Reject template formatting text.
    if re.search(
        r"(?i)DD/MM/YYYY|☐|□",
        value
    ):
        return True

    # Reject generic policy wording accidentally
    # classified as a short table value.
    if len(value) > 220:
        return True

    return False


def find_person_tables(pdf_bytes):
    """Read insured-person table rows with correct column context."""
    extracted = []
    person_pages = set()

    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf"
    ) as doc:

        for page_no, page in enumerate(doc, start=1):

            try:
                tables = page.find_tables().tables
            except Exception:
                continue

            for table in tables:

                try:
                    rows = table.extract()
                except Exception:
                    continue

                if not rows:
                    continue

                header_index = None
                headers = []

                for i, row in enumerate(rows[:5]):
                    cells = [clean(c) for c in row]

                    if sum(
                        bool(PERSON_HEADER.search(c))
                        for c in cells
                    ) >= 1:
                        header_index = i
                        headers = cells
                        break

                if header_index is None:
                    continue

                person_pages.add(page_no)

                for row in rows[header_index + 1:]:
                    cells = [clean(c) for c in row]

                    if not cells or len(cells) < 2:
                        continue

                    field = cells[0]

                    if compact(field) not in PERSON_ROWS:
                        continue

                    for col in range(
                        1, min(len(cells), len(headers))
                    ):
                        person = headers[col]

                        if not PERSON_HEADER.search(person):
                            continue

                        value = cells[col]

                        if not value or value.upper() in {
                            "NA", "N/A", "NONE"
                        }:
                            continue

                        record = {
                            "Field": field,
                            "Value": value,
                            "Person": person,
                            "Page": page_no,
                            "Evidence": (
                                f"{person} | {field}: {value}"
                            ),
                            "Method": "validated person table"
                        }

                        if invalid_record(record):
                            continue

                        extracted.append(record)

    return extracted, person_pages


def clean_list(records, person_pages=None):
    """Remove malformed and duplicate records."""
    output = []
    seen = set()
    person_pages = person_pages or set()

    for rec in records or []:
        if not isinstance(rec, dict):
            continue

        if invalid_record(rec):
            continue

        field = clean(rec.get("Field"))
        value = clean(rec.get("Value"))
        page = rec.get("Page")
        method = str(rec.get("Method", "")).lower()

        # In person tables, reject generic table pairing.
        # Validated person records are inserted separately.
        if (
            page in person_pages
            and "table" in method
            and "validated person" not in method
            and compact(field) in PERSON_ROWS
        ):
            continue

        key = (
            compact(field),
            value.lower(),
            str(page),
            clean(rec.get("Person")).lower()
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(rec)

    return output


def fix_document_records(data, pdf_bytes):
    """Clean all record collections used by the UI."""
    person_records, person_pages = find_person_tables(
        pdf_bytes
    )

    groups = (
        "indexed_records",
        "dynamic_records",
        "priority_records",
        "contact_records",
        "proposal_records",
        "checkbox_records"
    )

    for group in groups:
        data[group] = clean_list(
            data.get(group, []),
            person_pages
        )

    # Add validated person-table rows to the
    # common record index used by the field resolver.
    data["indexed_records"] = clean_list(
        data.get("indexed_records", []) + person_records
    )

    # Keep dynamic records consistent with the index.
    data["dynamic_records"] = clean_list(
        data.get("dynamic_records", []) + person_records
    )

    return data
