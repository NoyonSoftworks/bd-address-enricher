
# Deploy the Bangladesh Address Enricher (Free Hosting)

You can deploy this app for **free** in either of these places:

## Option A: Streamlit Community Cloud (free & simple)
1. Create a new **public GitHub repo** and upload these files:
   - `app.py`
   - `address_enricher.py`
   - `bangladesh_thana_district.sample.csv` (optional starter)
   - `requirements.txt`
   - `README_Deploy.md` (optional)
2. Go to https://share.streamlit.io/
3. Log in → **New app** → point to your repo & `app.py` → **Deploy**.
4. You'll get a free URL like `https://yourname-yourrepo.streamlit.app`.

## Option B: Hugging Face Spaces (free)
1. Create a new **Space** at https://huggingface.co/spaces (choose **Streamlit**).
2. Upload the same files. Ensure `requirements.txt` exists.
3. Click **Restart** if needed. You’ll get a free URL like `https://huggingface.co/spaces/yourname/yourrepo`.

---

## Local Run (optional)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Usage
- Upload Excel with an **Address** column (or type the column name if different).
- Mode:
  - **auto (default)**: Offline first, then only missing via online (OSM)
  - **offline**: Only local CSV + matching
  - **online**: Only OSM + cache
- (Optional) Upload a full `bangladesh_thana_district.csv` gazetteer for complete coverage.
- (Optional) Upload an existing `cache_geocode.csv` to reuse saved lookups.

> Pro tip: Start with **offline** for speed, then switch to **auto** for the unresolved rows.
