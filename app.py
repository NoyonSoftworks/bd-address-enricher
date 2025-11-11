import io
import os
import pandas as pd
import streamlit as st
from address_enricher import run as enrich_run

# ---------------- Page Setup ----------------
st.set_page_config(page_title="BD Address Enricher", page_icon="🗺️", layout="wide")

# ---------------- Header (Option 1: Native) ----------------
st.markdown(
    """
    <div style='text-align:center; padding:20px; border-radius:10px;
    background:linear-gradient(90deg, #2563eb, #1e3a8a);
    color:white; font-size:32px; font-weight:700;'>
        🗺️ Bangladesh Address Enricher
    </div>
    <p style='text-align:center; color:#cbd5e1; font-size:15px; margin-top:6px;'>
        Automatically detect <b>District</b> & <b>Thana</b> from any Excel file
    </p>
    """,
    unsafe_allow_html=True
)

# Small badge
st.markdown(
    "<div style='text-align:center;'><span style='display:inline-block; padding:6px 12px; "
    "border-radius:999px; font-size:12px; background:#eef2ff; color:#3730a3; "
    "border:1px solid #c7d2fe;'>Auto mode: Offline → Online fallback</span></div><hr>",
    unsafe_allow_html=True
)

# ---------------- Upload Controls ----------------
uploaded = st.file_uploader("📤 Upload Excel (.xlsx) with an **Address** column", type=["xlsx"])
col1, col2, col3 = st.columns(3)
mode = col1.selectbox(
    "Mode",
    options=["auto", "offline", "online"],
    index=0,
    help="auto = Offline first, then only missing via Online (OpenStreetMap)"
)
address_col = col2.text_input("Address column name (optional; auto-detects)", value="")
sheet_index = col3.number_input("Sheet index (0-based)", min_value=0, value=0, step=1)

with st.expander("🗂 Gazetteer & Cache (optional)"):
    gaz = st.file_uploader("Upload `bangladesh_thana_district.csv` (thana/upazila/area,district)", type=["csv"])
    cache_csv = st.file_uploader("Upload existing `cache_geocode.csv` (address,district,thana)", type=["csv"])
    retry_flag = st.checkbox("Retry online for rows that remain Not found", value=True)
    st.caption("💡 Tip: Start with **offline** for speed, then **auto** for unresolved rows.")

st.markdown("---")

# ---------------- Demo Downloads ----------------
colL, colR = st.columns(2)
demo_gaz = colL.button("⬇️ Download Sample Gazetteer CSV")
demo_addr = colR.button("📥 Download Sample Address File (Excel)")

if demo_gaz:
    gaz_sample = "bangladesh_thana_district.sample.csv"
    if os.path.exists(gaz_sample):
        with open(gaz_sample, "rb") as f:
            st.download_button(
                "Download: bangladesh_thana_district.sample.csv",
                f,
                file_name="bangladesh_thana_district.sample.csv"
            )
    else:
        st.warning("`bangladesh_thana_district.sample.csv` not found in the repo.")

if demo_addr:
    addr_sample = "sample_addresses.xlsx"
    if os.path.exists(addr_sample):
        with open(addr_sample, "rb") as f:
            st.download_button(
                "Download: sample_addresses.xlsx",
                f,
                file_name="sample_addresses.xlsx"
            )
    else:
        st.warning("`sample_addresses.xlsx` not found in the repo. Please upload it to GitHub.")

st.markdown("---")

# ---------------- Process Button ----------------
process = st.button("⚙️ Process & Download", type="primary")

if process:
    if not uploaded:
        st.error("Please upload an Excel (.xlsx) file first.")
        st.stop()

    with st.spinner("Processing your file... Please wait ⏳"):
        os.makedirs("tmp", exist_ok=True)
        in_path = os.path.join("tmp", "input.xlsx")
        with open(in_path, "wb") as f:
            f.write(uploaded.getbuffer())

        gaz_path = None
        if gaz is not None:
            gaz_path = os.path.join("tmp", "bangladesh_thana_district.csv")
            with open(gaz_path, "wb") as f:
                f.write(gaz.getbuffer())

        cache_path = None
        if cache_csv is not None:
            cache_path = os.path.join("tmp", "cache_geocode.csv")
            with open(cache_path, "wb") as f:
                f.write(cache_csv.getbuffer())
        else:
            cache_path = "cache_geocode.csv"  # created/updated as needed

        out_path = os.path.join("tmp", "output.xlsx")

        enrich_run(
            input_xlsx=in_path,
            output_xlsx=out_path,
            address_col=(address_col if address_col.strip() else None),
            mode=mode,
            gazetteer_csv=gaz_path if gaz_path else None,
            cache_path=cache_path,
            sheet_index=int(sheet_index),
            retry_online_notfound=bool(retry_flag),
        )

    with open(out_path, "rb") as f:
        st.download_button("⬇️ Download Enriched Excel", f, file_name="address_enriched.xlsx")

    st.success("✅ Done! You can now tweak modes or upload a larger CSV gazetteer for full coverage.")
    st.caption("If many rows go Online, re-run later — cache speeds things up and respects OSM limits.")

# ---------------- Footer ----------------
st.markdown("---")
st.markdown(
    '<div style="text-align:center; color:#475569; font-size:13px;">'
    'Made with ❤️ by <b>NoyonSoftworks</b> | Powered by Streamlit & OpenStreetMap'
    '</div>',
    unsafe_allow_html=True
)
