import io
import re
from datetime import datetime

import pymupdf


STOP = {
    "what", "which", "who", "where", "is", "are",
    "was", "were", "the", "a", "an", "my", "your",
    "of", "for", "in", "on", "to", "from",
    "give", "get", "show", "find", "tell", "me",
    "please", "pdf", "document", "field",
    "value", "values", "details", "detail",
    "amount", "amounts", "can", "you",
    "do", "does", "have", "has", "and",
    "all", "enaku", "enna", "kudu", "sollu"
}

SKIP_LABELS = {
    "yes", "no", "name", "date",
    "place", "signature", "year"
}

DATE_FIELDS = {
    "date of birth", "dob",
    "policy start date", "policy end date",
    "expiry date", "expiration date",
    "commencement date", "renewal date",
    "proposal date", "date of issue"
}

DATE_RE = re.compile(
    r"(?<!\w)(\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\w)"
)

INSURED_HEADER_RE = re.compile(
    r"\b(?:\d+(?:st|nd|rd|th)\s+)?insured\s+person\b",
    re.IGNORECASE
)


def tokens(value):
    return re.findall(
        r"[a-z0-9]+",
        str(value).lower()
    )


def tidy(value):
    return " ".join(
        str(value or "")
        .replace("\u25a1", " ")
        .split()
    ).strip(" :|-")


def field_name_ok(label):
    label = tidy(label)
    words = tokens(label)

    if not 1 <= len(words) <= 18:
        return False

    if not 2 <= len(label) <= 155:
        return False

    if re.search(
        r"\b(if|please|shall|would|whether|"
        r"does|that|this|there|under|"
        r"according|hereby|declare)\b",
        label,
        re.IGNORECASE
    ):
        return False

    return any(char.isalpha() for char in label)


def value_ok(value):
    value = tidy(value)

    if not value:
        return False

    if value.upper() in {
        "NA", "N/A", "NIL", "NONE",
        "NOT APPLICABLE", "-", "--"
    }:
        return False

    if "☐" in value:
        return False

    if "DD/MM/YYYY" in value.upper():
        return False

    if len(value) > 180:
        return False

    return True


def normalize_field(field):
    """Normalize common compact PDF labels."""

    field = tidy(field)

    compact = re.sub(
        r"[^a-z0-9]",
        "",
        field.lower()
    )

    aliases = {
        "dateofbirth": "Date of Birth",
        "dob": "Date of Birth",
        "insuredname": "Insured Name",
        "policyholdername": "Policyholder Name",
        "policyno": "Policy Number",
        "policynumber": "Policy Number",
        "proposalno": "Proposal Number",
        "emailid": "Email",
        "mobileno": "Mobile Number",
        "phonenumber": "Phone Number",
        "maritalstatus": "Marital Status",
        "aadhaarno": "Aadhaar Number",
        "panno": "PAN Number"
    }

    return aliases.get(compact, field)


def is_date_field(field):
    field = normalize_field(field).lower()

    return (
        field in DATE_FIELDS
        or field.endswith(" date")
        or field.startswith("date of ")
    )


def clean_table_value(field, value):
    """
    Clean a field value.

    Important:
    Never guess a corrupted DOB such as 15/06/0D198/9M.
    """

    value = tidy(value)

    if not value_ok(value):
        return ""

    if is_date_field(field):
        match = DATE_RE.search(value)

        if not match:
            return ""

        date_value = match.group(1)

        for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
            try:
                datetime.strptime(date_value, fmt)
                return date_value
            except ValueError:
                continue

        return ""

    return value


def add(
    found,
    seen,
    label,
    value,
    page,
    evidence,
    method,
    person=""
):
    label = normalize_field(label)
    value = tidy(value)
    person = tidy(person)

    if not field_name_ok(label):
        return

    if not value_ok(value):
        return

    if label.lower() == value.lower():
        return

    key = (
        tuple(tokens(label)),
        value.lower(),
        page,
        person.lower()
    )

    if key in seen:
        return

    seen.add(key)

    found.append({
        "Field": label,
        "Value": value,
        "Page": page,
        "Person": person,
        "Evidence": tidy(evidence)[:240],
        "Method": method
    })


def is_insured_person_table(rows):
    """Identify a table with insured-person columns."""

    for row in rows[:5]:
        if not row:
            continue

        cells = [tidy(cell) for cell in row]

        matches = sum(
            bool(INSURED_HEADER_RE.search(cell))
            for cell in cells
        )

        if matches >= 1:
            return True

    return False


def extract_person_table(
    table,
    page_number,
    found=None,
    seen=None
):
    """
    Extract actual row/column relationships.

    Example:
        Field           1st Insured       2nd Insured
        Name            Arun Kumar        Meera Arun
        Date of Birth   15/06/1989        21/09/1992
    """

    if found is None:
        found = []

    if seen is None:
        seen = set()

    rows = table.extract()

    if not rows:
        return found

    header_index = None
    headers = []

    for idx, row in enumerate(rows[:5]):
        cells = [tidy(cell) for cell in row]

        if any(
            INSURED_HEADER_RE.search(cell)
            for cell in cells
        ):
            header_index = idx
            headers = cells
            break

    if header_index is None:
        return found

    for row in rows[header_index + 1:]:
        cells = [tidy(cell) for cell in row]

        if len(cells) < 2:
            continue

        field = normalize_field(cells[0])

        if not field_name_ok(field):
            continue

        # Skip repeated header rows.
        if INSURED_HEADER_RE.search(field):
            continue

        for col in range(1, min(len(cells), len(headers))):
            person = headers[col]

            if not INSURED_HEADER_RE.search(person):
                continue

            value = clean_table_value(
                field,
                cells[col]
            )

            if not value:
                continue

            add(
                found,
                seen,
                field,
                value,
                page_number,
                f"{person} | {field}: {value}",
                "person table",
                person=person
            )

    return found


def extract_regular_table(
    table,
    page_number,
    found,
    seen
):
    """Extract normal Label | Value and serial-number tables."""

    rows = table.extract()

    if not rows:
        return

    for row in rows[:250]:
        if not row:
            continue

        cells = [tidy(cell) for cell in row]

        if len(cells) < 2:
            continue

        # Example: 7 | Name of Scheme | Actual value
        if (
            len(cells) >= 3
            and re.fullmatch(r"\d{1,3}[.)]?", cells[0])
        ):
            pairs = [(cells[1], cells[2])]

        elif len(cells) == 2:
            pairs = [(cells[0], cells[1])]

        elif len(cells) % 2 == 0:
            pairs = [
                (cells[i], cells[i + 1])
                for i in range(0, len(cells) - 1, 2)
            ]

        else:
            pairs = [
                (cells[0], cells[i])
                for i in range(1, len(cells))
            ]

        for label, value in pairs:
            label = normalize_field(label)

            if not field_name_ok(label):
                continue

            value = clean_table_value(label, value)

            if not value:
                continue

            add(
                found,
                seen,
                label,
                value,
                page_number,
                f"Table: {label} = {value}",
                "table cell"
            )


def extract_line_pairs(
    text,
    page_number,
    found,
    seen
):
    """Extract ordinary Label: Value text."""

    for original_line in text.splitlines():
        line = tidy(original_line)

        if not line or len(line) > 240:
            continue

        if line.startswith(("http://", "https://")):
            continue

        spans = list(re.finditer(
            r"(?<![\w])"
            r"([A-Za-z][A-Za-z0-9()./\- ]{1,44}?)"
            r"\s*:\s*",
            line
        ))

        for index, match in enumerate(spans):
            label = normalize_field(match.group(1))

            end = (
                spans[index + 1].start()
                if index + 1 < len(spans)
                else len(line)
            )

            value = clean_table_value(
                label,
                line[match.end():end]
            )

            if not value:
                continue

            add(
                found,
                seen,
                label,
                value,
                page_number,
                line,
                "line label:value"
            )


def dynamic_candidates(
    pdf_bytes,
    max_pages=100,
    text_pages=None,
    tables_by_page=None,
    **kwargs
):
    """
    Main dynamic extraction function.

    text_pages and tables_by_page are optional cached data.
    Existing callers can still use:
        dynamic_candidates(pdf_bytes)
    """

    found = []
    seen = set()

    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf"
    ) as doc:

        for page_index, page in enumerate(doc):

            if page_index >= max_pages:
                break

            page_number = page_index + 1

            # Reuse cached text if available.
            if (
                text_pages is not None
                and page_index < len(text_pages)
            ):
                text = text_pages[page_index]
            else:
                text = page.get_text(
                    "text",
                    sort=True
                )

            # OCR fallback for image-only pages.
            if len(text.strip()) < 60:
                try:
                    import pytesseract
                    from PIL import Image

                    pix = page.get_pixmap(dpi=160)

                    image = Image.open(
                        io.BytesIO(
                            pix.tobytes("png")
                        )
                    )

                    text = pytesseract.image_to_string(
                        image
                    )

                except Exception:
                    text = ""

            extract_line_pairs(
                text,
                page_number,
                found,
                seen
            )

            # Reuse cached tables if supplied.
            if tables_by_page is not None:
                try:
                    tables = tables_by_page[page_index]
                except (KeyError, IndexError):
                    tables = None
            else:
                try:
                    tables = page.find_tables().tables
                except Exception:
                    tables = None

            if tables is None:
                continue

            # Support a PyMuPDF TableFinder object too.
            if hasattr(tables, "tables"):
                tables = tables.tables

            for table in list(tables)[:24]:

                try:
                    rows = table.extract()
                except Exception:
                    continue

                # Important:
                # Person tables must not go through generic
                # row pairing again.
                if is_insured_person_table(rows):

                    extract_person_table(
                        table,
                        page_number,
                        found,
                        seen
                    )

                else:

                    extract_regular_table(
                        table,
                        page_number,
                        found,
                        seen
                    )

    return found


def query_dynamic(
    query,
    records,
    max_results=25
):
    """Match complete field words, not partial substrings."""

    query_words = tokens(query)

    if not query_words:
        return []

    content = [
        word
        for word in query_words
        if word not in STOP
    ]

    if not content:
        return []

    scored = []

    for record in records:

        label_words = tokens(
            record.get("Field", "")
        )

        if not label_words:
            continue

        # Query must match actual field words.
        if any(
            word not in label_words
            for word in content
        ):
            continue

        score = (
            10 * len(content)
            - 2 * abs(
                len(label_words) - len(content)
            )
        )

        if label_words == content:
            score += 20

        scored.append((score, record))

    if not scored:
        return []

    scored.sort(
        key=lambda item: -item[0]
    )

    best_score = scored[0][0]

    return [
        record
        for score, record in scored
        if score >= best_score - 12
    ][:max_results]
