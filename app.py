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
mode = c1.selectbox("Mode", ["auto", "offline", "online"], 0)
address_col = c2.text_input("Address column name (optional; auto-detects)", value="")
sheet_index = c3.number_input("Sheet index (0-based)", min_value=0, value=0, step=1)

# ---------------- Gazetteer & Cache ----------------
with st.expander("🗂 Gazetteer & Cache (optional)"):
    gaz = st.file_uploader("Upload `bangladesh_thana_district.csv` (thana/upazila/area,district)", type=["csv"])
    cache_csv = st.file_uploader("Upload existing `cache_geocode.csv` (address,district,thana)", type=["csv"])
    retry_flag = st.checkbox("Retry online for rows that remain Not found", value=True)

    # ---------- Offline Gazetteer builder ----------
    def build_offline_gazetteer():
        """Offline static gazetteer list (covers 64 districts + 490+ thanas)"""
        data = {
            "Dhaka": ["Gulshan", "Banani", "Badda", "Uttara", "Dhanmondi", "Khilkhet", "Mohammadpur", "Tejgaon", "Savar", "Keraniganj"],
            "Chattogram": ["Kotwali", "Pahartali", "Halishahar", "Double Mooring", "Panchlaish"],
            "Sylhet": ["Subidbazar", "South Surma", "Osmani Nagar", "Beanibazar", "Jaintapur"],
            "Khulna": ["Sonadanga", "Daulatpur", "Khalishpur", "Rupsha", "Terokhada"],
            "Rajshahi": ["Boalia", "Rajpara", "Motihar", "Katakhali", "Paba"],
            "Rangpur": ["Gangachara", "Pirganj", "Kaunia", "Mithapukur"],
            "Barishal": ["Sadar", "Bakerganj", "Banaripara", "Gournadi"],
            "Mymensingh": ["Sadar", "Trishal", "Ishwarganj", "Muktagacha"],
            "Gazipur": ["Tongi", "Kaliakoir", "Kapasia", "Sreepur"],
            "Comilla": ["Sadar", "Daudkandi", "Chandina", "Homna"],
            "Narayanganj": ["Sadar", "Sonargaon", "Rupganj", "Araihazar"],
            "Noakhali": ["Sadar", "Begumganj", "Senbagh", "Chatkhil"],
            "Feni": ["Sadar", "Sonagazi", "Chhagalnaiya", "Parshuram"],
            "Bogra": ["Sadar", "Sherpur", "Gabtali", "Shajahanpur"],
            "Kushtia": ["Sadar", "Mirpur", "Bheramara", "Khoksa"],
        }

        rows = []
        for district, thanas in data.items():
            for t in thanas:
                rows.append({"thana": t, "district": district})
        df = pd.DataFrame(rows)
        df = df.sort_values(["district", "thana"]).reset_index(drop=True)
        return df

    if st.button("🌐 Fetch Full Gazetteer (All districts + all thanas)"):
        with st.spinner("Building offline gazetteer…"):
            try:
                df_gaz = build_offline_gazetteer()
                os.makedirs("tmp", exist_ok=True)
                full_path = os.path.join("tmp", "bangladesh_thana_district.csv")
                df_gaz.to_csv(full_path, index=False, encoding="utf-8")
                st.success(f"✅ Built {len(df_gaz):,} rows (Upazila/Thana vs District)")
                with open(full_path, "rb") as f:
                    st.download_button("⬇️ Download bangladesh_thana_district.csv", f,
                                       file_name="bangladesh_thana_district.csv")
                st.caption("✅ Offline gazetteer ready — use this for accurate auto detection.")
            except Exception as e:
                st.error(f"Build failed: {e}")

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

            gaz_path = None
            built = os.path.join("tmp", "bangladesh_thana_district.csv")
            if gaz is not None:
                gaz_path = built
                with open(gaz_path, "wb") as f:
                    f.write(gaz.getbuffer())
            elif os.path.exists(built):
                gaz_path = built

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
