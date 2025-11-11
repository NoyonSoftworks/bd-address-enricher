# 🗺️ Bangladesh Address Enricher

Automatically detect **District** and **Thana** from any Excel file containing an `Address` column.  
Built by **NoyonSoftworks** using Python + Streamlit.

---

## 🚀 Live App
👉 **[Open on Streamlit Cloud](https://share.streamlit.io)**  
*(You’ll get your own link like `https://noyonsoftworks-bd-address-enricher.streamlit.app` after deploy)*

---

## ⚙️ Features
✅ Auto mode → Offline first → then Online fallback (OpenStreetMap)  
✅ Offline / Online modes separately available  
✅ Smart fuzzy matching for local areas (Dhaka, Chattogram, etc.)  
✅ Cache system for faster repeated lookups  
✅ Excel output includes both **Original** & **Enriched** sheets  
✅ Download sample files directly from the app  

---

## 📂 Files Overview
| File | Description |
|------|--------------|
| `app.py` | Streamlit frontend web app |
| `address_enricher.py` | Core logic (offline + online address parsing) |
| `requirements.txt` | Dependencies for Streamlit Cloud |
| `README_Deploy.md` | Deploy guide for Streamlit/HuggingFace |
| `bangladesh_thana_district.sample.csv` | Sample Gazetteer (district & thana) |
| `sample_addresses.xlsx` | Demo Excel with sample addresses ✅ |

---

## 🧭 How to Use
1. Go to the live app link.  
2. Upload your Excel file with an **Address** column.  
3. Choose your preferred **Mode**:
   - `auto` → Offline first, then Online fallback  
   - `offline` → Only local CSV matching  
   - `online` → Only OpenStreetMap (with cache)
4. (Optional) Upload your `bangladesh_thana_district.csv` file for full coverage.
5. Click **⚙️ Process & Download** to get your enriched Excel file.

---

## 📥 Demo Files
You can download sample files directly from the app:
- [Sample Gazetteer CSV](bangladesh_thana_district.sample.csv)
- [Sample Address Excel](sample_addresses.xlsx)

---

## ❤️ Credits
Made with ❤️ by **NoyonSoftworks**  
Powered by **Streamlit** & **OpenStreetMap**
