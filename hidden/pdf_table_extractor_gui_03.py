# -*- coding: utf-8 -*-
"""
PDF Table Extractor (Interactive Column Boundaries)
---------------------------------------------------
This Streamlit app allows you to:
1. Upload a PDF file.
2. Define column boundaries dynamically (with add/delete/edit).
3. Adjust header and footer cutoffs to exclude non-table text.
4. Preview PDF pages with detected words, column boundaries, and cutoffs.
5. Extract tables across all pages into a structured DataFrame.
6. Export extracted data to Excel.

Created on Thu Sep  4 18:40:10 2025
@author: Ali Yaz (aliyaz99@outlook.com)
"""

import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
import pdfplumber
import pandas as pd
from collections import defaultdict
from PIL import ImageDraw, ImageFont
from io import BytesIO

# Streamlit layout settings
st.set_page_config(page_title="PDF Table Extractor", layout="wide")
st.title("PDF Table Extractor (Interactive Column Boundaries)")

# ---------- FUNCTIONS ----------

def assign_row(y, existing_rows, tolerance=2):
    """
    Assigns a y-coordinate to an existing row if it is within tolerance.
    This helps group words that belong to the same text line into one row.

    Parameters
    ----------
    y : float
        Y-coordinate of the detected word.
    existing_rows : list
        List of y-coordinates already assigned to rows.
    tolerance : int, optional
        Allowed vertical distance for considering two words in the same row.

    Returns
    -------
    float
        The matched row y-coordinate (if found) or the new y value.
    """
    for ry in existing_rows:
        if abs(y - ry) <= tolerance:
            return ry
    return y


def extract_positional_table(page, columns, y_tolerance=2, header_cutoff=200, footer_cutoff=570):
    """
    Extracts a table from a PDF page using positional word matching.

    Parameters
    ----------
    page : pdfplumber.page.Page
        The PDF page to extract from.
    columns : dict
        Dictionary of {column_name: (xmin, xmax)} defining column boundaries.
    y_tolerance : int, optional
        Vertical tolerance for grouping words into the same row.
    header_cutoff : int, optional
        Ignore any text above this y-coordinate.
    footer_cutoff : int, optional
        Ignore any text below this y-coordinate.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the extracted table rows.
    """
    words = page.extract_words()
    rows = defaultdict(lambda: defaultdict(str))
    for w in words:
        x, y, text = w["x0"], w["top"], w["text"]
        # Skip header/footer areas
        if y < header_cutoff or y > footer_cutoff:
            continue
        # Assign word to a column if x falls inside column boundary
        for col, (xmin, xmax) in columns.items():
            if xmin <= x <= xmax:
                row_y = assign_row(y, rows.keys(), tolerance=y_tolerance)
                rows[row_y][col] += (" " + text)
                break
    # Convert grouped rows into DataFrame
    data = [rows[y] for y in sorted(rows.keys())]
    return pd.DataFrame(data)


def draw_page_image_with_columns(page, columns, header_cutoff=None, footer_cutoff=None, scale=2):
    """
    Creates a preview image of a PDF page with overlays:
    - Red boxes around detected words
    - Colored vertical lines for column boundaries
    - Horizontal lines for header/footer cutoffs
    - Column names drawn at the top

    Parameters
    ----------
    page : pdfplumber.page.Page
        PDF page to render.
    columns : dict
        Column definitions {col_name: (xmin, xmax)}.
    header_cutoff : int, optional
        Y-coordinate for header cutoff line.
    footer_cutoff : int, optional
        Y-coordinate for footer cutoff line.
    scale : int, optional
        Zoom factor for higher resolution preview.

    Returns
    -------
    PIL.Image
        Page image with visualized boundaries and cutoffs.
    """
    # Convert PDF page to image
    im_obj = page.to_image(resolution=72*scale)
    pil_img = im_obj.original.copy()
    draw = ImageDraw.Draw(pil_img)

    # Font for labels
    try:
        font = ImageFont.truetype("arial.ttf", 10*scale)
    except:
        font = ImageFont.load_default()
    
    # Draw word bounding boxes
    for w in page.extract_words():
        x0, top, x1, bottom = w["x0"]*scale, w["top"]*scale, w["x1"]*scale, w["bottom"]*scale
        draw.rectangle([x0, top, x1, bottom], outline="red", width=1*scale)
    
    # Draw column boundaries
    colors = ["blue", "green", "orange", "purple", "brown", "pink", "cyan", "magenta"]
    for i, (col_name, (xmin, xmax)) in enumerate(columns.items()):
        color = colors[i % len(colors)]
        xmin_s, xmax_s = xmin*scale, xmax*scale
        draw.line([(xmin_s, 0), (xmin_s, pil_img.height)], fill=color, width=2*scale)
        draw.line([(xmax_s, 0), (xmax_s, pil_img.height)], fill=color, width=2*scale)
        draw.text((xmin_s, 0), col_name, fill=color, font=font)
    
    # Draw header/footer cutoffs
    if header_cutoff is not None:
        y = header_cutoff*scale
        draw.line([(0, y), (pil_img.width, y)], fill="black", width=2*scale)
        draw.text((5, y-25), "Header cutoff", fill="black", font=font)
    if footer_cutoff is not None:
        y = footer_cutoff*scale
        draw.line([(0, y), (pil_img.width, y)], fill="black", width=2*scale)
        draw.text((5, y+15), "Footer cutoff", fill="black", font=font)
    
    return pil_img

# ---------- UPLOAD PDF ----------
uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"])

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        num_pages = len(pdf.pages)
        st.success(f"PDF loaded successfully ({num_pages} pages).")
        
        # ---------- LAYOUT: LEFT (controls) / RIGHT (preview) ----------
        left_panel, right_panel = st.columns([1, 2])

        # ---------- LEFT PANEL: CONTROLS ----------
with left_panel:
    st.subheader("Column & Boundary Settings")

    # Initialize default columns on first load
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

    # --- Add new column (immediately rerun so UI reflects new row) ---
    if st.button("Add Column"):
        base = "NewColumn"
        i = 1
        existing = set(st.session_state.columns.keys())
        while f"{base}{i}" in existing:
            i += 1
        st.session_state.columns[f"{base}{i}"] = (10, 50)
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()

    # --- Edit / Delete columns (index-based widget keys) ---
    updated_columns = {}
    items = list(st.session_state.columns.items())
    to_delete_any = False

    for idx, (col_name, (xmin, xmax)) in enumerate(items):
        c_del, c1, c2, c3 = st.columns([0.35, 2, 1.2, 1.2])

        # Per-row red X delete button
        if c_del.button("❌", key=f"del_{idx}"):
            to_delete_any = True
            # skip adding this column to updated_columns (i.e., delete it)
            continue

        # Editable fields (index-based keys so renames don't confuse Streamlit)
        new_name = c1.text_input("Column Name", value=col_name, key=f"name_{idx}")
        new_xmin = c2.number_input("Xmin", value=float(xmin), key=f"xmin_{idx}")
        new_xmax = c3.number_input("Xmax", value=float(xmax), key=f"xmax_{idx}")

        # Guard rails
        if not str(new_name).strip():
            new_name = col_name  # keep old name if blank
        if new_xmin > new_xmax:
            # swap if user inverted them
            new_xmin, new_xmax = new_xmax, new_xmin

        updated_columns[new_name] = (float(new_xmin), float(new_xmax))

    # Replace entire mapping so deletes/renames take effect cleanly
    st.session_state.columns = updated_columns

    # If any deletion occurred, force a rerun to clear orphaned widgets/lines
    if to_delete_any:
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()

    # --- Header / Footer cutoffs ---
    st.subheader("Header/Footer Cutoffs")
    header_cutoff = st.number_input("Header cutoff (y)", value=160)
    footer_cutoff = st.number_input("Footer cutoff (y)", value=570)

    # --- Page selection (compact counter + prev/next) ---
    st.subheader("Page Selection")
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

    # Three equal columns for prev, number, next
    nav1, nav2, nav3 = st.columns([1, 1, 1])

    with nav1:
        if st.button("⬅ Previous", use_container_width=True):
            if st.session_state.current_page > 1:
                st.session_state.current_page -= 1

    with nav2:
        st.session_state.current_page = st.number_input(
            f"Page (1/{num_pages})",
            min_value=1,
            max_value=num_pages,
            value=st.session_state.current_page,
            step=1,
            format="%d",
            key="compact_page_input",
        )

    with nav3:
        if st.button("Next ➡", use_container_width=True):
            if st.session_state.current_page < num_pages:
                st.session_state.current_page += 1

    page_number = st.session_state.current_page


    # ---------- RIGHT PANEL: PDF PREVIEW ----------

    with right_panel:
        st.subheader("PDF Preview with Column Boundaries")

        page = pdf.pages[page_number-1]
        page_img = draw_page_image_with_columns(
            page,
            st.session_state.columns,
            header_cutoff=header_cutoff,
            footer_cutoff=footer_cutoff,
            scale=2
        )

        # Interactive image click
        coords = streamlit_image_coordinates(page_img, key="pdf_click")

        if coords:
            x, y = coords["x"], coords["y"]
            st.write(f"Clicked at x={x}, y={y}")

            # Save first click as xmin, second as xmax
            if "pending_x" not in st.session_state:
                st.session_state.pending_x = x
                st.info(f"First boundary set at {x}")
            else:
                xmin, xmax = sorted([st.session_state.pending_x, x])
                new_name = f"NewColumn{len(st.session_state.columns)+1}"
                # Rescale back since you used scale=2 in draw_page_image_with_columns
                st.session_state.columns[new_name] = (xmin/2, xmax/2)
                st.success(f"New column '{new_name}' added: ({xmin/2:.1f}, {xmax/2:.1f})")
                del st.session_state.pending_x


    # ---------- EXTRACTION ----------
    st.subheader("Data Extraction")

    # Extract from CURRENT page
    if st.button("Extract Current Page"):
        df_page = extract_positional_table(
            page,
            columns=st.session_state.columns,
            header_cutoff=header_cutoff,
            footer_cutoff=footer_cutoff
        )
        if not df_page.empty:
            df_page["Page"] = page_number
            st.success(f"Data extracted from page {page_number}!")
            st.dataframe(df_page)

            # Export current page data
            towrite = BytesIO()
            df_page.to_excel(towrite, index=False, engine="openpyxl")
            towrite.seek(0)
            st.download_button(
                label=f"Download Page {page_number} Data",
                data=towrite,
                file_name=f"extracted_page_{page_number}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No data extracted from this page. Check boundaries and cutoffs.")

    # Extract from ALL pages
    if st.button("Extract Data from All Pages"):
        all_pages = []
        for i, pg in enumerate(pdf.pages, start=1):
            df_pg = extract_positional_table(
                pg,
                columns=st.session_state.columns,
                header_cutoff=header_cutoff,
                footer_cutoff=footer_cutoff
            )
            if not df_pg.empty:
                df_pg["Page"] = i
                all_pages.append(df_pg)

        if all_pages:
            df_all = pd.concat(all_pages, ignore_index=True)
            st.success("Extraction completed for all pages!")
            st.dataframe(df_all.head(20))

            # Export all pages
            towrite = BytesIO()
            df_all.to_excel(towrite, index=False, engine="openpyxl")
            towrite.seek(0)
            st.download_button(
                label="Download All Pages Data",
                data=towrite,
                file_name="extracted_table_all.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No data extracted from any pages. Check column boundaries and cutoffs.")
