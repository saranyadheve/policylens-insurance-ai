
import io
import re
import pymupdf


def normalize(text):
    return " ".join(str(text or "").split())


def find_source_position(
    pdf_bytes,
    value,
    page_number=None,
    label=None
):
    """
    Find the location of a value in the PDF.

    Returns:
        Page: 1-based page number
        BBox: [x0, y0, x1, y1]
        Evidence: matched source text
    """

    value = normalize(value)

    if not value:
        return None

    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf"
    ) as doc:

        if page_number is not None:
            page_indexes = [page_number - 1]
        else:
            page_indexes = range(len(doc))

        for page_index in page_indexes:

            if not 0 <= page_index < len(doc):
                continue

            page = doc[page_index]

            # First: exact value search.
            matches = page.search_for(value)

            # Second: flexible whitespace search.
            if not matches:
                try:
                    words = page.get_text("words")

                    # Word search for single-token values.
                    if len(value.split()) == 1:
                        for word in words:
                            if normalize(word[4]) == value:
                                matches.append(
                                    pymupdf.Rect(word[:4])
                                )
                except Exception:
                    pass

            if not matches:
                continue

            # If multiple matches exist, choose the
            # occurrence closest to the field label.
            selected = matches[0]

            if label:
                label_rects = page.search_for(label)

                if label_rects:
                    def distance(rect):
                        return min(
                            abs(rect.y0 - lr.y0)
                            + abs(rect.x0 - lr.x1)
                            for lr in label_rects
                        )

                    selected = min(
                        matches,
                        key=distance
                    )

            return {
                "Page": page_index + 1,
                "BBox": [
                    selected.x0,
                    selected.y0,
                    selected.x1,
                    selected.y1
                ],
                "Evidence": value
            }

    return None


def render_highlighted_page(
    pdf_bytes,
    page_number,
    bbox,
    zoom=1.8
):
    """
    Render a PDF page with a yellow rectangle
    around the selected extracted value.
    """

    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf"
    ) as doc:

        page = doc[page_number - 1]

        if bbox:
            rect = pymupdf.Rect(bbox)

            # Highlight on this in-memory page only.
            page.draw_rect(
                rect + (-2, -2, 2, 2),
                color=(1, 0.65, 0),
                fill=(1, 1, 0),
                fill_opacity=0.25,
                width=2,
                overlay=True
            )

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(zoom, zoom),
            alpha=False
        )

        return pix.tobytes("png")


def show_field_source(
    pdf_bytes,
    value,
    page_number=None,
    label=None
):
    """
    Streamlit helper.
    Show the actual source with highlight.
    """

    import streamlit as st

    position = find_source_position(
        pdf_bytes=pdf_bytes,
        value=value,
        page_number=page_number,
        label=label
    )

    if position is None:
        st.warning(
            "Exact source location was not found. "
            "Please verify the extracted value."
        )
        return

    image = render_highlighted_page(
        pdf_bytes,
        position["Page"],
        position["BBox"]
    )

    st.caption(
        f"Source: Page {position['Page']}"
    )

    st.image(image, use_container_width=True)

    return position
