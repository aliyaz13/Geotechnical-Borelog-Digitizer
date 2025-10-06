# -*- coding: utf-8 -*-
"""
PDF Table Extractor (Interactive GUI) v4
-------------------------------------

TODO: Add a bit thick background for column labels to increase UX readbility.
TODO: Improve performance of setting column boundaries with clicking on PDF.

This Streamlit app lets users visually define and adjust table column boundaries
for PDFs where tabular data is aligned but not structured.

Features:
----------
1. **Interactive Column Creation**
   - Click on the PDF image to define new column x-ranges (xmin/xmax).
   - The first click sets xmin, the second click sets xmax.
   - A new column is automatically added.

2. **Column Management**
   - Edit existing column names and boundaries.
   - Delete columns using red ❌ buttons.
   - Add new empty columns if needed.

3. **Header & Footer Cutoffs**
   - Define the y-ranges to ignore headers and footers.

4. **Page Navigation**
   - Navigate between pages with previous/next buttons or numeric input.

5. **Data Extraction**
   - Extract table data from the *current page* or *all pages*.
   - Export results as an Excel file.

6. **PDF Preview**
   - Displays the PDF page with visual boundaries for columns, header, and footer.

Author: Ali Yaz
Date: 2025-10-06
"""

import streamlit as st
import pdfplumber
import pandas as pd
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# optional: click-to-coords component (if you use it)
try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    _has_click_comp = True
except Exception:
    _has_click_comp = False

st.set_page_config(page_title="PDF Table Extractor", layout="wide")
st.title("📊 PDF Table Extractor (Interactive Column Boundaries)")

# ---------- FUNCTIONS ----------
def assign_row(y, existing_rows, tolerance=2):
    """Group visually-close y positions into the same row."""
    for ry in existing_rows:
        if abs(y - ry) <= tolerance:
            return ry
    return y

def extract_positional_table(page, columns, y_tolerance=2, header_cutoff=200, footer_cutoff=570):
    """Extract rows from a single page using defined x-ranges for columns."""
    words = page.extract_words()
    rows = defaultdict(lambda: defaultdict(str))
    for w in words:
        x, y, text = w["x0"], w["top"], w["text"]
        if y < header_cutoff or y > footer_cutoff:
            continue
        for col, (xmin, xmax) in columns.items():
            if xmin <= x <= xmax:
                row_y = assign_row(y, rows.keys(), tolerance=y_tolerance)
                rows[row_y][col] += (" " + text)
                break
    data = [rows[y] for y in sorted(rows.keys())]
    return pd.DataFrame(data)

def draw_page_image_with_columns(page, columns, header_cutoff=None, footer_cutoff=None, scale=2):
    """
    Draws the PDF page with visual guides:
    - Red boxes around words
    - Vertical lines for each column's xmin/xmax
    - Optional header/footer cutoff lines
    - Column labels with improved visibility
    """
    # Convert PDF page to a high-res image
    im_obj = page.to_image(resolution=72 * scale)
    pil_img = im_obj.original.copy()
    draw = ImageDraw.Draw(pil_img)

    # Load font safely
    try:
        font = ImageFont.truetype("arial.ttf", 12 * scale)
    except:
        font = ImageFont.load_default()

    # Draw word bounding boxes (for debugging)
    for w in page.extract_words():
        x0, top, x1, bottom = (
            w["x0"] * scale,
            w["top"] * scale,
            w["x1"] * scale,
            w["bottom"] * scale,
        )
        draw.rectangle([x0, top, x1, bottom], outline="red", width=1 * scale)

    # Draw column boundaries and vertical text labels
    colors = ["blue", "green", "orange", "purple", "brown", "pink", "cyan", "magenta"]
    for i, (col_name, (xmin, xmax)) in enumerate(columns.items()):
        color = colors[i % len(colors)]
        xmin_s, xmax_s = xmin * scale, xmax * scale

        # Draw vertical boundary lines
        draw.line([(xmin_s, 0), (xmin_s, pil_img.height)], fill=color, width=2 * scale)
        draw.line([(xmax_s, 0), (xmax_s, pil_img.height)], fill=color, width=2 * scale)

        # Draw vertical (rotated) label with white background
        text_img = Image.new("RGBA", (200, 50), (255, 255, 255, 0))
        text_draw = ImageDraw.Draw(text_img)
        text_draw.text((5, 5), col_name, fill=color, font=font)

        # Rotate text
        rotated = text_img.rotate(90, expand=1)

        # Crop the rotated image to remove extra transparent space
        bbox = rotated.getbbox()
        rotated_cropped = rotated.crop(bbox)

        # Create tight white background
        bg = Image.new("RGBA", rotated_cropped.size, (255, 255, 255, 255))  # solid white

        # Compute placement
        text_x = int((xmin_s + xmax_s) / 2 - rotated_cropped.width / 2)
        text_y = 15  # top margin

        # Paste background then the rotated text
        pil_img.paste(bg, (text_x, text_y), bg)
        pil_img.paste(rotated_cropped, (text_x, text_y), rotated_cropped)


    # Draw header cutoff
    if header_cutoff is not None:
        y = header_cutoff * scale
        draw.line([(0, y), (pil_img.width, y)], fill="black", width=2 * scale)
        draw.text((5, y - 50), "Header cutoff", fill="black", font=font)

    # Draw footer cutoff
    if footer_cutoff is not None:
        y = footer_cutoff * scale
        draw.line([(0, y), (pil_img.width, y)], fill="black", width=2 * scale)
        draw.text((5, y - 15), "Footer cutoff", fill="black", font=font)

    return pil_img

# ---------- UPLOAD ----------
uploaded_file = st.file_uploader("📂 Upload PDF file", type=["pdf"])
if not uploaded_file:
    st.info("Upload a PDF to start. (Click coordinates feature requires 'streamlit-image-coordinates' package.)")
    st.stop()

with pdfplumber.open(uploaded_file) as pdf:
    num_pages = len(pdf.pages)
    st.success(f"✅ PDF loaded successfully ({num_pages} pages)")

    # ---------- LAYOUT ----------
    left_panel, right_panel = st.columns([1, 2])

    # ---------- LEFT PANEL (robust add/rename/delete) ----------
    with left_panel:
        st.subheader("🧭 Column & Boundary Settings")

        # Initialize session columns once
        if "columns" not in st.session_state:
            st.session_state.columns = {
                "SoilType": (45, 50),
                "SampleID": (85, 95),
                "BlowCounts": (150, 190),
                "CasingDepth_m": (195, 221),
                "RodLength_m": (223, 245),
                "EnergyRatio_%": (250, 272),
                "PocketPen_kPa": (390, 410),
                "Torvane_kPa": (410, 440),
                "Moisture_%": (440, 460),
            }

        # Add new column safely (form prevents accidental triggers)
        with st.form("add_column_form", clear_on_submit=True):
            add_col = st.form_submit_button("➕ Add Column")
            if add_col:
                counter = 1
                while f"NewColumn{counter}" in st.session_state.columns:
                    counter += 1
                new_name = f"NewColumn{counter}"
                st.session_state.columns[new_name] = (10, 50)
                st.rerun()


        st.markdown("**Edit or delete columns**")

        # We'll build a fresh mapping from the visible widgets each run.
        # Use index-based widget keys to avoid name-collision issues on rename/delete.
        items = list(st.session_state.columns.items())
        updated_columns = {}
        deleted_any = False

        for idx, (col_name, (xmin, xmax)) in enumerate(items):
            # small left column for delete button, then inputs
            c_del, c_name, c_xmin, c_xmax = st.columns([0.35, 2, 1.4, 1.4])

            # delete button keyed by index (stable during this run)
            if c_del.button("❌", key=f"del_{idx}"):
                # mark deleted and force a rerun to clear orphan widgets
                st.session_state._deleted = col_name
                deleted_any = True
                break  # break out so we rerun immediately

            # editable name/xmin/xmax with index-based keys
            new_name = c_name.text_input("Name", value=col_name, key=f"name_{idx}")
            new_xmin = c_xmin.number_input("Xmin", value=float(xmin), key=f"xmin_{idx}")
            new_xmax = c_xmax.number_input("Xmax", value=float(xmax), key=f"xmax_{idx}")

            # guard rails
            if not str(new_name).strip():
                new_name = col_name
            try:
                new_xmin = float(new_xmin)
                new_xmax = float(new_xmax)
            except Exception:
                new_xmin, new_xmax = xmin, xmax
            if new_xmin > new_xmax:
                new_xmin, new_xmax = new_xmax, new_xmin

            updated_columns[new_name] = (new_xmin, new_xmax)

        # If delete was clicked, actually remove the column and rerun immediately to avoid ghost widgets
        if deleted_any and "_deleted" in st.session_state:
            name_to_remove = st.session_state.pop("_deleted")
            st.session_state.columns.pop(name_to_remove, None)
            # trigger a fresh rerun so Streamlit rebuilds widgets afresh (no ghost buttons)
            st.rerun()

        # If no deletion triggered, save the updated mapping
        st.session_state.columns = updated_columns

        # --- Header/Footer cutoffs ---
        st.subheader("📏 Header / Footer Cutoffs")
        header_cutoff = st.number_input("Header cutoff (y)", value=160)
        footer_cutoff = st.number_input("Footer cutoff (y)", value=570)

        # --- Page navigation (symmetric) ---
        st.subheader("📄 Page Selection")
        if "current_page" not in st.session_state:
            st.session_state.current_page = 1

        nav1, nav2, nav3 = st.columns([1, 0.8, 1])
        with nav1:
            if st.button("⬅ Previous"):
                if st.session_state.current_page > 1:
                    st.session_state.current_page -= 1
        with nav2:
            st.session_state.current_page = st.number_input(
                "Page",
                min_value=1,
                max_value=num_pages,
                value=st.session_state.current_page,
                step=1,
                format="%d",
                label_visibility="collapsed",
                key="compact_page_input"
            )
            st.markdown(f"<div style='text-align:center;'>Page {st.session_state.current_page} / {num_pages}</div>", unsafe_allow_html=True)
        with nav3:
            if st.button("Next ➡"):
                if st.session_state.current_page < num_pages:
                    st.session_state.current_page += 1

        page_number = st.session_state.current_page

    # ---------- RIGHT PANEL (preview + click-to-add) ----------
    with right_panel:
        st.subheader("🖼️ PDF Preview & Click-to-define Columns")
        page = pdf.pages[page_number - 1]

        # render preview image with overlays
        page_img = draw_page_image_with_columns(
            page,
            st.session_state.columns,
            header_cutoff=header_cutoff,
            footer_cutoff=footer_cutoff,
            scale=2
        )

        # optional: click-to-define column boundaries if component is available
        if _has_click_comp:
            coords = streamlit_image_coordinates(page_img, key=f"coords_{page_number}")
            if coords:
                x, y = coords["x"], coords["y"]
                st.write(f"Clicked at x={x:.1f}, y={y:.1f}")
                if "pending_x" not in st.session_state:
                    st.session_state.pending_x = x
                    st.info(f"First boundary set at x={x:.1f} (click a second time for xmax)")
                else:
                    xmin_px, xmax_px = sorted([st.session_state.pending_x, x])
                    # convert pixels back to PDF coords (we used scale=2)
                    xmin_pdf, xmax_pdf = xmin_px / 2.0, xmax_px / 2.0
                    # add new column and refresh UI
                    base = "NewColumn"
                    i = 1
                    existing = set(st.session_state.columns.keys())
                    while f"{base}{i}" in existing:
                        i += 1
                    new_col_name = f"{base}{i}"
                    st.session_state.columns[new_col_name] = (xmin_pdf, xmax_pdf)
                    del st.session_state.pending_x
                    st.success(f"Added column '{new_col_name}' → ({xmin_pdf:.1f}, {xmax_pdf:.1f})")
                    st.rerun()
        else:
            st.info("Click-to-define columns requires 'streamlit-image-coordinates' package. (Optional)")

        st.image(page_img, use_column_width=True)

    # ---------- EXTRACTION ----------
    st.divider()
    st.subheader("📤 Data Extraction")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Extract Current Page"):
            df_page = extract_positional_table(
                pdf.pages[page_number - 1],
                columns=st.session_state.columns,
                header_cutoff=header_cutoff,
                footer_cutoff=footer_cutoff
            )
            if not df_page.empty:
                st.success(f"Data extracted from page {page_number}")
                st.dataframe(df_page.head(50))
                towrite = BytesIO()
                df_page.to_excel(towrite, index=False, engine="openpyxl")
                towrite.seek(0)
                st.download_button("⬇ Download current page", data=towrite, file_name=f"page_{page_number}.xlsx")
            else:
                st.warning("No data extracted from this page. Check boundaries/cutoffs.")

    with c2:
        if st.button("📘 Extract All Pages"):
            all_pages = []
            for i, pg in enumerate(pdf.pages, start=1):
                df_page = extract_positional_table(
                    pg,
                    columns=st.session_state.columns,
                    header_cutoff=header_cutoff,
                    footer_cutoff=footer_cutoff
                )
                if not df_page.empty:
                    df_page["Page"] = i
                    all_pages.append(df_page)
            if all_pages:
                df_all = pd.concat(all_pages, ignore_index=True)
                st.success("Extraction completed for all pages!")
                st.dataframe(df_all.head(50))
                towrite = BytesIO()
                df_all.to_excel(towrite, index=False, engine="openpyxl")
                towrite.seek(0)
                st.download_button("⬇ Download all pages", data=towrite, file_name="extracted_all.xlsx")
            else:
                st.warning("No data extracted. Check column boundaries/cutoffs.")
