import os
import pandas as pd
import streamlit as st
from address_enricher import run as enrich_run

# ---------------- Page Setup ----------------
st.set_page_config(page_title="BD Address Enricher", page_icon="🗺️", layout="wide")

st.markdown("""
<div style='text-align:center;padding:20px;border-radius:10px;
background:linear-gradient(90deg,#2563eb,#1e3a8a);color:white;
font-size:32px;font-weight:700;'>🗺️ Bangladesh Address Enricher</div>
<p style='text-align:center;color:#cbd5e1;font-size:15px;margin-top:6px;'>
Automatically detect <b>District</b> & <b>Thana</b> from any Excel file
</p>""", unsafe_allow_html=True)

st.markdown("<div style='text-align:center;'><span style='display:inline-block;padding:6px 12px;"
            "border-radius:999px;font-size:12px;background:#eef2ff;color:#3730a3;"
            "border:1px solid #c7d2fe;'>Auto mode: Offline → Online fallback</span></div><hr>",
            unsafe_allow_html=True)

# ---------------- Upload Controls ----------------
uploaded = st.file_uploader("📤 Upload Excel (.xlsx) with an **Address** column", type=["xlsx"])
c1, c2, c3 = st.columns(3)
mode = c1.selectbox("Mode", ["auto", "offline", "online"], 0,
                    help="auto = Offline first, then only missing via Online (OpenStreetMap)")
address_col = c2.text_input("Address column name (optional; auto-detects)", value="")
sheet_index = c3.number_input("Sheet index (0-based)", min_value=0, value=0, step=1)

# ---------------- Gazetteer & Cache ----------------
with st.expander("🗂 Gazetteer & Cache (optional)"):
    gaz = st.file_uploader("Upload `bangladesh_thana_district.csv` (thana/upazila/area,district)", type=["csv"])
    cache_csv = st.file_uploader("Upload existing `cache_geocode.csv` (address,district,thana)", type=["csv"])
    retry_flag = st.checkbox("Retry online for rows that remain Not found", value=True)
    st.caption("💡 Tip: Start with **offline** for speed, then **auto** for unresolved rows.")

    # ---------- Fetch Full Gazetteer (robust; never numeric) ----------
    def fetch_full_gazetteer() -> pd.DataFrame:
    DIST_URL = "https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/districts/districts.csv"
    UPAZ_URL = "https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/upazilas/upazilas.csv"

    # Load with flexible encoding
    dist = pd.read_csv(DIST_URL, encoding="utf-8", engine="python")
    upaz = pd.read_csv(UPAZ_URL, encoding="utf-8", engine="python")

    # Try to detect columns dynamically
    def detect(df, possible_names):
        for name in possible_names:
            for col in df.columns:
                if name.lower() in col.lower():
                    return col
        return df.columns[0]

    # district file columns
    d_id = detect(dist, ["id", "district_id", "code"])
    d_name = detect(dist, ["district_name", "name", "en_name", "bn_name"])

    # upazila file columns
    u_did = detect(upaz, ["district_id", "district_code", "parent_id"])
    u_name = detect(upaz, ["upazila_name", "upazila", "name", "en_name", "bn_name"])

    merged = upaz.merge(dist, left_on=u_did, right_on=d_id, how="left")

    df = pd.DataFrame({
        "thana": merged[u_name].astype(str).str.strip().str.title(),
        "district": merged[d_name].astype(str).str.strip().str.title()
    }).dropna()

    # Filter out numeric or blank values
    import re
    numeric = re.compile(r"^\s*\d+([/.,-]\d+)*\s*$")
    df = df[~df["thana"].str.match(numeric)]
    df = df[~df["district"].str.match(numeric)]

    df = df.drop_duplicates().sort_values(["district", "thana"]).reset_index(drop=True)
    return df

# ---------------- Demo Downloads ----------------
l, r = st.columns(2)
if l.button("⬇️ Download Sample Gazetteer CSV"):
    p = "bangladesh_thana_district.sample.csv"
    if os.path.exists(p):
        with open(p, "rb") as f:
            st.download_button("Download: bangladesh_thana_district.sample.csv", f,
                               file_name="bangladesh_thana_district.sample.csv")
    else:
        st.warning("`bangladesh_thana_district.sample.csv` not found in the repo.")
if r.button("📥 Download Sample Address File (Excel)"):
    p = "sample_addresses.xlsx"
    if os.path.exists(p):
        with open(p, "rb") as f:
            st.download_button("Download: sample_addresses.xlsx", f, file_name="sample_addresses.xlsx")
    else:
        st.warning("`sample_addresses.xlsx` not found in the repo. Please upload it to GitHub.")

st.markdown("---")

# ---------------- Process Button ----------------
if st.button("⚙️ Process & Download", type="primary"):
    if not uploaded:
        st.error("Please upload an Excel (.xlsx) file first.")
    else:
        with st.spinner("Processing your file... Please wait ⏳"):
            os.makedirs("tmp", exist_ok=True)
            in_path = os.path.join("tmp", "input.xlsx")
            with open(in_path, "wb") as f:
                f.write(uploaded.getbuffer())

            # Gazetteer (uploaded or freshly built)
            gaz_path = None
            built = os.path.join("tmp", "bangladesh_thana_district.csv")
            if gaz is not None:
                gaz_path = built
                with open(gaz_path, "wb") as f:
                    f.write(gaz.getbuffer())
            elif os.path.exists(built):
                gaz_path = built

            # Cache
            cache_path = None
            if cache_csv is not None:
                cache_path = os.path.join("tmp", "cache_geocode.csv")
                with open(cache_path, "wb") as f:
                    f.write(cache_csv.getbuffer())
            else:
                cache_path = "cache_geocode.csv"

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
        st.success("✅ Done! Offline + Online enrichment completed.")

# ---------------- Footer ----------------
st.markdown("---")
st.markdown("<div style='text-align:center;color:#475569;font-size:13px;'>"
            "Made with ❤️ by <b>NoyonSoftworks</b> | Powered by Streamlit & OpenStreetMap</div>",
            unsafe_allow_html=True)
