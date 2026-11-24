
"""
PolicyLens - UI Source Priority Bridge

Purpose:
1. Preserve existing extracted fields.
2. Try the original verified extraction.
3. If zero vehicle records are returned, retry independently.
4. Recover motor identifiers from native PDF text/geometry.
5. Reject obvious incorrect Engine/Chassis associations.
6. Preserve PDF page and bounding-box evidence.
7. Keep policy schedule extraction independent.
8. Return diagnostic information.

This is a source-backed recovery layer, not an OCR replacement.
"""

from __future__ import annotations

import re

import pymupdf

from verified_table_overrides import (
    apply_source_priority,
    checked,
    as_result,
)

from vehicle_table_verified import (
    vehicle_records as verified_vehicle_records,
)

from policy_schedule_verified import (
    policy_schedule_records,
)


VIN_PATTERN = re.compile(
    r"^[A-HJ-NPR-Z0-9]{17}$",
    re.IGNORECASE,
)

ENGINE_PATTERN = re.compile(
    r"^(?=.*[A-Z])(?=.*\d)[A-Z0-9-]{7,20}$",
    re.IGNORECASE,
)

REGISTRATION_PATTERN = re.compile(
    r"\b([A-Z]{2})\s*-?\s*(\d{1,2})\s*-?\s*"
    r"([A-Z]{1,3})\s*-?\s*(\d{1,4})\b",
    re.IGNORECASE,
)


# -----------------------------------------------------
# BASIC HELPERS
# -----------------------------------------------------

def clean(value):
    return " ".join(str(value or "").split())


def compact(value):
    return re.sub(
        r"[^A-Z0-9]",
        "",
        clean(value).upper(),
    )


def valid_vehicle_value(field, value):
    """
    Basic validation independent of the old checked()
    function, which may reject correct recovered values.
    """

    field_key = clean(field).lower()
    value = clean(value)

    if not field_key or not value:
        return False

    normalized = compact(value)

    if field_key == "engine number":

        if not ENGINE_PATTERN.fullmatch(normalized):
            return False

        # Avoid accepting a 17-character chassis/VIN.
        if VIN_PATTERN.fullmatch(normalized):
            return False

        return True

    if field_key == "chassis number":
        return bool(VIN_PATTERN.fullmatch(normalized))

    if field_key == "registration number":
        return bool(
            REGISTRATION_PATTERN.search(value)
        )

    if field_key in {
        "cubic capacity",
        "gvw",
        "carrying capacity",
        "year of manufacture",
    }:
        return bool(
            re.fullmatch(r"\d{1,6}", normalized)
        )

    if field_key in {
        "vehicle idv",
        "insured declared value",
    }:
        return bool(
            re.fullmatch(r"\d{4,12}", normalized)
        )

    if normalized.lower() in {
        "vehicle",
        "engine",
        "engineno",
        "policyschedule",
        "geographicalarea",
    }:
        return False

    return True


def make_result(field, value, page_number, bbox, evidence):
    return {
        "Field": field,
        "Value": value,
        "Page": page_number,
        "BBox": bbox,
        "Evidence": evidence,
        "Person": "",
        "Method": "native-pdf-geometry",
    }


def normalize_bbox(bbox):
    if not bbox or len(bbox) != 4:
        return None

    try:
        return tuple(float(x) for x in bbox)
    except (ValueError, TypeError):
        return None


def source_result(item):
    """
    Convert source record into the registry structure
    expected by app.py.
    """

    return {
        "value": item.get("Value", ""),
        "status": "review",
        "page": item.get("Page"),
        "bbox": normalize_bbox(item.get("BBox")),
        "evidence": item.get("Evidence", ""),
        "person": item.get("Person", ""),
    }


def find_bbox(page, value):
    try:
        boxes = page.search_for(str(value))

        if boxes:
            return tuple(boxes[0])

    except Exception:
        pass

    return None


def word_center(word):
    return (
        (word[0] + word[2]) / 2,
        (word[1] + word[3]) / 2,
    )


def same_row(a, b, tolerance=7):
    return abs(
        word_center(a)[1] - word_center(b)[1]
    ) <= tolerance


# -----------------------------------------------------
# DIRECT MOTOR SOURCE RECOVERY
# -----------------------------------------------------

def recover_motor_identifiers(raw):
    """
    Source-backed recovery for motor documents.

    The engine-number recovery requires a relationship
    to the chassis row or the Engine Number label.

    Does not hardcode policy-specific values.
    """

    records = []
    seen = set()

    with pymupdf.open(
        stream=raw,
        filetype="pdf",
    ) as document:

        for page_index, page in enumerate(document):

            page_number = page_index + 1
            text = page.get_text("text")
            upper_text = text.upper()

            # Never apply motor identifier recovery to
            # unrelated insurance documents.
            if not any(
                marker in upper_text
                for marker in (
                    "CHASSIS",
                    "ENGINE NO",
                    "ENGINE NUMBER",
                    "REGISTRATION NUMBER",
                )
            ):
                continue

            words = page.get_text("words")

            # -----------------------------------------
            # REGISTRATION NUMBER
            # -----------------------------------------

            for match in REGISTRATION_PATTERN.finditer(
                upper_text
            ):

                registration = (
                    f"{match.group(1)} - "
                    f"{match.group(2)} - "
                    f"{match.group(3)} - "
                    f"{match.group(4)}"
                )

                bbox = find_bbox(page, match.group(0))

                if bbox is None:
                    continue

                key = (
                    "Registration Number",
                    compact(registration),
                )

                if key in seen:
                    continue

                seen.add(key)

                records.append(
                    make_result(
                        "Registration Number",
                        registration,
                        page_number,
                        bbox,
                        match.group(0),
                    )
                )

            # -----------------------------------------
            # CHASSIS NUMBER
            # -----------------------------------------

            chassis_words = []

            for word in words:

                token = compact(word[4])

                if VIN_PATTERN.fullmatch(token):
                    chassis_words.append(word)

                    key = (
                        "Chassis Number",
                        token,
                    )

                    if key not in seen:

                        seen.add(key)

                        records.append(
                            make_result(
                                "Chassis Number",
                                token,
                                page_number,
                                tuple(word[:4]),
                                token,
                            )
                        )

            # -----------------------------------------
            # ENGINE NUMBER
            # -----------------------------------------

            engine_candidates = []

            for word in words:

                token = compact(word[4])

                if not ENGINE_PATTERN.fullmatch(token):
                    continue

                if VIN_PATTERN.fullmatch(token):
                    continue

                engine_candidates.append(word)

            # Prefer an engine identifier to the left
            # of a chassis number on the same table row.

            for chassis_word in chassis_words:

                left_candidates = []

                for candidate in engine_candidates:

                    if not same_row(
                        candidate,
                        chassis_word,
                    ):
                        continue

                    # Candidate must be left of chassis.
                    if candidate[2] >= chassis_word[0]:
                        continue

                    distance = (
                        chassis_word[0] - candidate[2]
                    )

                    left_candidates.append(
                        (distance, candidate)
                    )

                if not left_candidates:
                    continue

                left_candidates.sort(
                    key=lambda item: item[0]
                )

                candidate = left_candidates[0][1]
                engine = compact(candidate[4])

                if engine == compact(chassis_word[4]):
                    continue

                key = ("Engine Number", engine)

                if key not in seen:

                    seen.add(key)

                    records.append(
                        make_result(
                            "Engine Number",
                            engine,
                            page_number,
                            tuple(candidate[:4]),
                            (
                                "Vehicle row near chassis "
                                + compact(chassis_word[4])
                            ),
                        )
                    )

            # -----------------------------------------
            # ALTERNATIVE ENGINE SEARCH
            # -----------------------------------------

            # Used only if no source-backed engine was
            # found on the current page.
            has_engine = any(
                item["Field"] == "Engine Number"
                and item["Page"] == page_number
                for item in records
            )

            if not has_engine:

                engine_labels = []

                for word in words:

                    if clean(word[4]).lower() in {
                        "engine",
                        "engineno",
                        "engine-no",
                    }:
                        engine_labels.append(word)

                for label in engine_labels:

                    nearby = []

                    for candidate in engine_candidates:

                        lx, ly = word_center(label)
                        cx, cy = word_center(candidate)

                        dx = abs(cx - lx)
                        dy = abs(cy - ly)

                        # Same-row or nearby table-cell
                        # evidence required.
                        if dy > 45 or dx > 220:
                            continue

                        score = dx + 3 * dy

                        nearby.append(
                            (score, candidate)
                        )

                    if not nearby:
                        continue

                    nearby.sort(
                        key=lambda item: item[0]
                    )

                    candidate = nearby[0][1]
                    engine = compact(candidate[4])

                    key = (
                        "Engine Number",
                        engine,
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    records.append(
                        make_result(
                            "Engine Number",
                            engine,
                            page_number,
                            tuple(candidate[:4]),
                            "Near Engine label",
                        )
                    )

    return records


# -----------------------------------------------------
# UI REGISTRY MERGE
# -----------------------------------------------------

def merge_vehicle_record(
    item,
    common_fields,
    discovered_fields,
    resolved,
    names,
    report,
):
    field = clean(item.get("Field"))
    value = clean(item.get("Value"))

    if not valid_vehicle_value(field, value):
        return False

    bbox = normalize_bbox(item.get("BBox"))

    # Do not silently certify a value that has
    # no source location.
    if bbox is None:
        return False

    old = resolved.get(field, {})

    if not isinstance(old, dict):
        old = {}

    old_value = clean(old.get("value"))

    if old_value != value:

        report["updates"].append(
            (field, old_value, value)
        )

    # Verified candidates have source evidence.
    # Status remains review until confirmed.
    resolved[field] = source_result(item)

    if field not in discovered_fields:
        discovered_fields.append(field)

    if field not in names:
        names.append(field)

    return True


# -----------------------------------------------------
# COMPLETE UI SOURCE PRIORITY FUNCTION
# -----------------------------------------------------

def apply_ui_source_priority(
    raw,
    common_fields,
    discovered_fields,
    resolved,
):

    report = {
        "phase": "not started",
        "vehicle_count": 0,
        "vehicle_fields": [],
        "schedule_count": 0,
        "updates": [],
        "error": "",
        "fallback_used": False,
        "raw_vehicle_count": 0,
        "accepted_vehicle_count": 0,
        "native_vehicle_count": 0,
    }

    names = []

    # -----------------------------------------
    # STEP 1: EXISTING SOURCE PRIORITY
    # -----------------------------------------

    try:

        main_names, updates = apply_source_priority(
            raw,
            common_fields,
            discovered_fields,
            resolved,
        )

        names = list(main_names or [])

        report["updates"].extend(
            list(updates or [])
        )

        if names:
            report["phase"] = (
                "main source priority succeeded"
            )

        else:
            report["phase"] = (
                "main source priority returned zero"
            )

    except Exception as exc:

        report["error"] = (
            "Main priority: "
            f"{type(exc).__name__}: {exc}"
        )

    # -----------------------------------------
    # STEP 2: VERIFIED VEHICLE FALLBACK
    # -----------------------------------------

    if not names:

        report["fallback_used"] = True

        try:

            fallback_records = list(
                verified_vehicle_records(
                    raw,
                    max_pages=100000,
                )
            )

            report["raw_vehicle_count"] = len(
                fallback_records
            )

            for item in fallback_records:

                accepted = merge_vehicle_record(
                    item,
                    common_fields,
                    discovered_fields,
                    resolved,
                    names,
                    report,
                )

                if accepted:
                    report[
                        "accepted_vehicle_count"
                    ] += 1

        except Exception as exc:

            report["error"] += (
                " | Verified fallback: "
                f"{type(exc).__name__}: {exc}"
            )

    # -----------------------------------------
    # STEP 3: INDEPENDENT PDF RECOVERY
    # -----------------------------------------

    if not names:

        report["fallback_used"] = True

        try:

            native_records = recover_motor_identifiers(
                raw
            )

            report["native_vehicle_count"] = len(
                native_records
            )

            for item in native_records:

                merge_vehicle_record(
                    item,
                    common_fields,
                    discovered_fields,
                    resolved,
                    names,
                    report,
                )

            if names:
                report["phase"] = (
                    "native PDF vehicle recovery"
                )

            else:
                report["phase"] = (
                    "no source-backed vehicle "
                    "identifiers recovered"
                )

        except Exception as exc:

            report["error"] += (
                " | Native PDF recovery: "
                f"{type(exc).__name__}: {exc}"
            )

    # -----------------------------------------
    # STEP 4: POLICY SCHEDULE RECOVERY
    # -----------------------------------------

    try:

        schedule = list(
            policy_schedule_records(
                raw,
                max_pages=100000,
            )
        )

        report["schedule_count"] = len(schedule)

        by_field = {
            item["Field"]: item
            for item in schedule
            if item.get("Field")
        }

        for field in (
            "Sum Insured",
            "Total Premium",
            "Insured Name",
            "Policy Number",
            "Policy Start Date",
            "Policy End Date",
        ):

            if field not in common_fields:
                continue

            item = by_field.get(field)

            if not item:
                continue

            value = clean(item.get("Value"))

            if not value:
                continue

            # Preserve the original source validation.
            if not checked(field, value):
                continue

            previous = resolved.get(
                field,
                {},
            )

            if not isinstance(previous, dict):
                previous = {}

            if clean(previous.get("value")) != value:

                report["updates"].append(
                    (
                        field,
                        previous.get("value"),
                        value,
                    )
                )

            resolved[field] = as_result(item)

    except Exception as exc:

        report["error"] += (
            " | Schedule recovery: "
            f"{type(exc).__name__}: {exc}"
        )

    report["vehicle_fields"] = list(names)
    report["vehicle_count"] = len(names)

    if names and report["phase"] == (
        "main source priority returned zero"
    ):
        report["phase"] = (
            "verified vehicle fallback succeeded"
        )

    return names, report
