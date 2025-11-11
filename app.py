import os, io, re
import pandas as pd
import streamlit as st
from address_enricher import run as enrich_run

st.set_page_config(page_title="BD Address Enricher", page_icon="🗺️", layout="wide")

# ----------------- UI Header -----------------
st.markdown("""
<div style='text-align:center;padding:20px;border-radius:10px;
background:linear-gradient(90deg,#2563eb,#1e3a8a);color:white;font-size:32px;font-weight:700;'>
🗺️ Bangladesh Address Enricher
</div>
<p style='text-align:center;color:#cbd5e1;font-size:15px;margin-top:6px;'>
Offline → Online fallback • Learns from cache • Merge multiple CSV sources
</p>
""", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- Upload section -----------------
uploaded = st.file_uploader("📤 Upload Excel (.xlsx) with an **Address** column", type=["xlsx"])
c1, c2, c3 = st.columns(3)
mode = c1.selectbox("Mode", ["auto","offline","online"], 0,
                    help="auto = Offline first, then fill missing via Online")
address_col = c2.text_input("Address column name (optional; auto-detects)", "")
sheet_index = c3.number_input("Sheet index (0-based)", min_value=0, value=0, step=1)

# =============================================================================
# Gazetteer & Cache toolbox
# =============================================================================
with st.expander("🗂 Gazetteer & Cache (build • merge • grow)"):
    st.caption("Use any (thana/upazila/area,district) CSVs. Tool will clean, merge, and dedupe.")

    gaz_files = st.file_uploader(
        "Upload one or more Gazetteer CSVs (you can add client lists too)",
        type=["csv"], accept_multiple_files=True
    )
    cache_csv = st.file_uploader("Upload existing cache_geocode.csv (optional)", type=["csv"])
    retry_flag = st.checkbox("Retry online for rows that remain Not found", value=True)

    NUMERIC = re.compile(r"^\s*\d+([/.,-]\d+)*\s*$")

    def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
        cols = {c.lower(): c for c in df.columns}
        th = cols.get("thana") or cols.get("upazila") or cols.get("area") or list(df.columns)[0]
        di = cols.get("district") or list(df.columns)[1]
        part = df[[th, di]].rename(columns={th: "thana", di: "district"})
        part["thana"] = part["thana"].astype(str).str.strip().str.title()
        part["district"] = part["district"].astype(str).str.strip().str.title()
        # FIX: no .str.eq(); use lowercase compare
        part = part[
            (part["thana"] != "") & (part["district"] != "") &
            (~part["thana"].str.match(NUMERIC)) & (~part["district"].str.match(NUMERIC)) &
            (part["thana"].str.strip().str.lower() != "not found") &
            (part["district"].str.strip().str.lower() != "not found")
        ]
        return part

    def merge_gazetteers(file_list) -> str | None:
        if not file_list:
            return None
        frames = []
        for up in file_list:
            df = pd.read_csv(io.BytesIO(up.read()), encoding="utf-8", engine="python", on_bad_lines="skip")
            frames.append(_clean_df(df))
        if not frames:
            return None
        out = (pd.concat(frames, ignore_index=True)
               .drop_duplicates()
               .sort_values(["district","thana"])
               .reset_index(drop=True))
        os.makedirs("tmp", exist_ok=True)
        p = os.path.join("tmp","bangladesh_thana_district.csv")
        out.to_csv(p, index=False, encoding="utf-8")
        st.success(f"✅ Merged gazetteer: {len(out):,} rows")
        return p

    def build_starter() -> str:
        data = {
            "Dhaka": ["Gulshan","Banani","Badda","Uttara","Khilkhet","Mohammadpur","Tejgaon","Dhanmondi",
                      "Rampura","Jatrabari","Wari","Motijheel","Kafrul","Cantonment","Baridhara",
                      "Bashundhara R/A","Bosila","Khilgaon"],
            "Gazipur": ["Tongi","Joydebpur","Kaliakair","Kaliganj","Sreepur"],
            "Narayanganj": ["Sadar","Sonargaon","Rupganj","Araihazar","Siddhirganj","Bandar","Fatulla"],
            "Chattogram": ["Kotwali","Pahartali","Double Mooring","Halishahar","Patenga","Bakalia",
                           "Panchlaish","Chandgaon","Bayazid","Akbar Shah"],
            "Sylhet": ["Subidbazar","South Surma","Kotwali Sylhet","Moglabazar","Ambarkhana","Osmani Nagar","Beanibazar"],
            "Comilla": ["Adarsa Sadar","Kotwali Comilla","Daudkandi","Chandina","Homna","Burichang"],
            "Khulna": ["Sonadanga","Daulatpur","Khalishpur","Khulna Kotwali","Rupsha"],
            "Rajshahi": ["Boalia","Rajpara","Motihar","Shah Makhdum","Paba"],
            "Barishal": ["Barishal Kotwali","Bakerganj","Banaripara","Gournadi"],
            "Mymensingh": ["Sadar","Trishal","Ishwarganj","Muktagacha"],
            "Rangpur": ["Gangachara","Pirganj","Kaunia","Mithapukur"],
            "Noakhali": ["Sadar","Begumganj","Senbagh","Chatkhil"],
            "Feni": ["Sadar","Sonagazi","Chhagalnaiya","Parshuram"],
            "Bogura": ["Sadar","Sherpur","Gabtali","Shajahanpur"],
            "Kushtia": ["Sadar","Mirpur","Bheramara","Khoksa"],
        }
        rows = [{"thana":t,"district":d} for d,ts in data.items() for t in ts]
        df = pd.DataFrame(rows).sort_values(["district","thana"]).reset_index(drop=True)
        os.makedirs("tmp", exist_ok=True)
        p = os.path.join("tmp","bangladesh_thana_district.csv")
        df.to_csv(p, index=False, encoding="utf-8")
        st.success(f"✅ Starter gazetteer built: {len(df):,} rows")
        return p

    cA, cB, cC = st.columns([1,1,1])
    if cA.button("🧩 Build Starter Gazetteer"):
        build_starter()
    if cB.button("➕ Merge Uploaded Gazetteers"):
        merge_gazetteers(gaz_files)

    # ---- Grow from cache (FIXED filters) ----
    with cC:
        if st.button("🔁 Grow Gazetteer from Cache"):
            try:
                cache_path = "cache_geocode.csv"
                if cache_csv is not None:
                    os.makedirs("tmp", exist_ok=True)
                    cache_path = os.path.join("tmp","cache_geocode.csv")
                    with open(cache_path,"wb") as f:
                        f.write(cache_csv.getbuffer())
                dfc = pd.read_csv(cache_path, encoding="utf-8", engine="python")
                cols = {c.lower(): c for c in dfc.columns}
                dcol = cols.get("district")
                tcol = cols.get("thana")
                if not (dcol and tcol):
                    st.error("Cache must have columns: address,district,thana")
                else:
                    pairs = (dfc[[dcol,tcol]].rename(columns={dcol:"district",tcol:"thana"})
                             .dropna())
                    pairs["district"] = pairs["district"].astype(str).str.strip().str.title()
                    pairs["thana"]    = pairs["thana"].astype(str).str.strip().str.title()
                    # FIX: no .str.eq(); use lowercase compare
                    pairs = pairs[
                        (pairs["district"] != "") & (pairs["thana"] != "") &
                        (~pairs["district"].str.match(NUMERIC)) & (~pairs["thana"].str.match(NUMERIC)) &
                        (pairs["district"].str.strip().str.lower() != "not found") &
                        (pairs["thana"].str.strip().str.lower() != "not found")
                    ].drop_duplicates().sort_values(["district","thana"])
                    base_path = os.path.join("tmp","bangladesh_thana_district.csv")
                    if os.path.exists(base_path):
                        base = pd.read_csv(base_path, encoding="utf-8", engine="python")
                        base = (pd.concat([base, pairs], ignore_index=True)
                                .drop_duplicates()
                                .sort_values(["district","thana"]))
                    else:
                        base = pairs
                    base.to_csv(base_path, index=False, encoding="utf-8")
                    with open(base_path,"rb") as f:
                        st.download_button("⬇️ Download updated bangladesh_thana_district.csv", f,
                                           file_name="bangladesh_thana_district.csv")
                    st.success(f"✅ Added {len(pairs)} unique pairs from cache.")
            except Exception as e:
                st.error(f"Failed: {e}")

st.markdown("---")

# =============================================================================
# Process
# =============================================================================
if st.button("⚙️ Process & Download", type="primary"):
    if not uploaded:
        st.error("Please upload an Excel (.xlsx) file first.")
    else:
        with st.spinner("Processing your file... ⏳"):
            os.makedirs("tmp", exist_ok=True)
            in_path = os.path.join("tmp","input.xlsx")
            with open(in_path,"wb") as f:
                f.write(uploaded.getbuffer())

            # Choose gazetteer priority: merged/starter > uploaded single > nothing
            gaz_path = None
            built = os.path.join("tmp","bangladesh_thana_district.csv")
            if os.path.exists(built):
                gaz_path = built
            elif gaz_files:
                gaz_path = merge_gazetteers(gaz_files)

            # Cache path
            cache_path = "cache_geocode.csv"
            if cache_csv is not None:
                cache_path = os.path.join("tmp","cache_geocode.csv")
                with open(cache_path,"wb") as f:
                    f.write(cache_csv.getbuffer())

            out_path = os.path.join("tmp","output.xlsx")
            enrich_run(
                input_xlsx=in_path,
                output_xlsx=out_path,
                address_col=(address_col if address_col.strip() else None),
                mode=mode,
                gazetteer_csv=gaz_path,
                cache_path=cache_path,
                sheet_index=int(sheet_index),
                retry_online_notfound=bool(retry_flag),
            )

        with open(out_path,"rb") as f:
            st.download_button("⬇️ Download Enriched Excel", f, file_name="address_enriched.xlsx")
        st.success("✅ Done! Offline + Online enrichment completed.")

# ----------------- Footer -----------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;color:#475569;font-size:13px;'>"
            "Made with ❤️ by <b>NoyonSoftworks</b> | Powered by Streamlit & OpenStreetMap</div>",
            unsafe_allow_html=True)
