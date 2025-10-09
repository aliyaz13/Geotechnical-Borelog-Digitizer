# 🧱 Geotechnical Borelog Digitizer — *PDF Table Extractor (Interactive GUI)*

> An interactive Streamlit app for visually defining and extracting tabular data from geotechnical borelogs or other structured-but-unformatted PDFs.

![Demo Screenshot](assets/demo_preview.png) <!-- optional if you add a screenshot -->

---

## 📘 Overview

**Geotechnical Borelog Digitizer** helps convert complex borelog PDFs into clean, structured data — **without needing fixed templates or OCR-heavy workflows.**

This tool provides a **visual interface** where you can:
- Define column boundaries by clicking directly on the PDF.
- Adjust, rename, and delete columns dynamically.
- Set header/footer cutoff regions to exclude unwanted areas.
- Extract data from single or multiple pages into Excel format.

It’s especially handy for **SPT logs, field sheets, or scanned borehole tables** where data columns are aligned visually but not tagged digitally.

---

## ✨ Key Features

| Feature | Description |
|----------|--------------|
| 🖱️ **Interactive Column Creation** | Click on the PDF to define column ranges (xmin/xmax). |
| 🧭 **Column Management** | Rename, delete, or manually edit column boundaries. |
| 📏 **Header/Footer Cutoffs** | Ignore fixed regions such as titles, legends, or notes. |
| 📄 **Page Navigation** | Quickly switch between pages with buttons or number input. |
| ⚙️ **Data Extraction** | Export current or all pages to `.xlsx`. |
| 🖼️ **PDF Visualization** | Shows all column lines and cutoff markers directly on the page image. |
| 🔍 **Optional Click-to-Coordinates Support** | Uses `streamlit-image-coordinates` for interactive clicks. |

---

## 🧰 Installation

Make sure you have **Python 3.9+** installed, then install the required packages:

```bash
pip install streamlit streamlit-image-coordinates pdfplumber pandas openpyxl pillow


# Geotechnical Borelog Digitizer

pip install streamlit streamlit-image-coordinates pdfplumber pandas openpyxl

cd C:\Users\RYZEN 5\Desktop\Borelog_GUI

python -m streamlit run pdf_table_extractor_gui_04.py
