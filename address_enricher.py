#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Address ⇒ District & Thana (Bangladesh)

Modes:
  - auto (default): Offline first, then Online fallback for missing values
  - offline       : Only offline (text heuristics + CSV gazetteer)
  - online        : Only online (OpenStreetMap Nominatim + cache)

Examples:
  python address_enricher.py --input INPUT.xlsx --output OUTPUT.xlsx                     # auto
  python address_enricher.py --input INPUT.xlsx --output OUTPUT.xlsx --mode offline      # force offline
  python address_enricher.py --input INPUT.xlsx --output OUTPUT.xlsx --mode online       # force online

Optional:
  --csv-gazetteer bangladesh_thana_district.csv
  --cache cache_geocode.csv
  --address-col "Address"
  --sheet-index 0
"""
import os, re, csv, time, argparse, requests
import pandas as pd
from difflib import get_close_matches

def normalize(s: str) -> str:
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = s.lower()
    replacements = {
        "dacca": "dhaka",
        "chittagong": "chattogram",
        "ctg": "chattogram",
        "barisal": "barishal",
        "cumilla": "comilla",
        "uttora": "uttara",
        "gulshan-1": "gulshan 1",
        "gulshan-2": "gulshan 2",
        "badda thana": "badda",
        "banani thana": "banani",
        "kotowali": "kotwali",
        "mohammad pur": "mohammadpur",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9,/\-\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

DISTRICTS = [
    "dhaka","gazipur","narayanganj","munshiganj","manikganj","narshingdi","kishoreganj","tangail",
    "mymensingh","jamalpur","netrokona","sherpur",
    "faridpur","madaripur","gopalganj","rajbari","shariatpur",
    "chattogram","cox s bazar","feni","noakhali","lakshmipur","rangamati","khagrachhari","bandarban","comilla","brahmanbaria",
    "sylhet","moulvibazar","habiganj","sunamganj",
    "khulna","jashore","satkhira","bagerhat","chuadanga","kushtia","meherpur","jhenaidah","magura","narail",
    "rajshahi","chapainawabganj","naogaon","natore","pabna","sirajganj","bogura",
    "barishal","patuakhali","barguna","jhalokathi","pirojpur","bhola",
    "rangpur","dinajpur","nilphamari","lalmonirhat","kurigram","gaibandha","thakurgaon","panchagarh"
]
DISTRICT_ALIASES = {
    "laxmipur": "lakshmipur",
    "bogra": "bogura",
    "jessore": "jashore",
    "barisal": "barishal",
    "chittagong": "chattogram",
    "coxsbazar": "cox s bazar",
    "cox's bazar": "cox s bazar",
}

# Big-city area gazetteer (extendable)
AREA_TO_DISTRICT = {
    "gulshan":"dhaka","banani":"dhaka","baridhara":"dhaka","badda":"dhaka","uttara":"dhaka","mirpur":"dhaka",
    "mohammadpur":"dhaka","tejgaon":"dhaka","dhanmondi":"dhaka","lalbagh":"dhaka","kafrul":"dhaka","cantonment":"dhaka",
    "airport":"dhaka","ramna":"dhaka","motijheel":"dhaka","paltan":"dhaka","sabujbagh":"dhaka","khilgaon":"dhaka",
    "rampura":"dhaka","jatrabari":"dhaka","mugda":"dhaka","wari":"dhaka","demra":"dhaka","shyampur":"dhaka",
    "kamrangirchar":"dhaka","adabor":"dhaka","hazaribagh":"dhaka","shahbag":"dhaka","banglamotor":"dhaka",
    "bansree":"dhaka","khilkhet":"dhaka","bosila":"dhaka","niketan":"dhaka","notun bazar":"dhaka",
    "bashundhara":"dhaka","bashundhara r/a":"dhaka","nakhalpara":"dhaka","tejgaon industrial area":"dhaka","zigatola":"dhaka",
    "tongi":"gazipur","joydebpur":"gazipur","kaliakair":"gazipur","kaliganj":"gazipur","sreepur":"gazipur",
    "siddhirganj":"narayanganj","bandar":"narayanganj","fatulla":"narayanganj",
    "kotwali":"chattogram","panchlaish":"chattogram","double mooring":"chattogram","pahartali":"chattogram","halishahar":"chattogram","patenga":"chattogram","bakalia":"chattogram","bandar thana":"chattogram","chandgaon":"chattogram","akbar shah":"chattogram","bayazid":"chattogram",
    "kotwali sylhet":"sylhet","south surma":"sylhet","moglabazar":"sylhet","subidbazar":"sylhet",
    "boalia":"rajshahi","motihar":"rajshahi","rajpara":"rajshahi","shah makhdum":"rajshahi",
    "khalishpur":"khulna","daulatpur":"khulna","sonadanga":"khulna","khulna kotwali":"khulna",
    "barishal kotwali":"barishal","airport barishal":"barishal",
    "kotwali comilla":"comilla","adarsa sadar":"comilla",
    "sadar noakhali":"noakhali","sadar bogura":"bogura",
}

def expand_area_keys(area_to_district):
    expanded = {}
    for k, v in area_to_district.items():
        for variant in {k, k.replace("-", " "), k.replace(" ", ""), k.replace("/", " ")}:
            expanded[normalize(variant)] = v
    return expanded

EXPANDED_AREA = expand_area_keys(AREA_TO_DISTRICT)
AREA_KEYS = list(set(EXPANDED_AREA.keys()))
DISTRICT_KEYS = list(set([normalize(d) for d in DISTRICTS] + list(DISTRICT_ALIASES.keys())))

def guess_area(addr_norm: str) -> str | None:
    for a in AREA_KEYS:
        if re.search(rf"\b{re.escape(a)}\b", addr_norm):
            return a
    toks = addr_norm.replace(",", " ").split()
    grams = toks + [" ".join(toks[i:i+2]) for i in range(len(toks)-1)]
    for g in grams:
        g = normalize(g)
        from difflib import get_close_matches
        m = get_close_matches(g, AREA_KEYS, n=1, cutoff=0.9)
        if m:
            return m[0]
    return None

def guess_district_from_text(addr_norm: str) -> str | None:
    for d in DISTRICT_KEYS:
        if re.search(rf"\b{re.escape(d)}\b", addr_norm):
            return DISTRICT_ALIASES.get(d, d)
    a = guess_area(addr_norm)
    if a:
        return EXPANDED_AREA.get(a)
    tokens = addr_norm.replace(",", " ").split()
    for t in tokens:
        from difflib import get_close_matches
        m = get_close_matches(t, [normalize(x) for x in DISTRICTS], n=1, cutoff=0.88)
        if m:
            return m[0]
    return None

# --------- Gazetteer ---------
def load_csv_gazetteer(path: str):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            th = normalize(row.get("thana") or row.get("upazila") or row.get("area") or "")
            dist = normalize(row.get("district") or "")
            if th and dist:
                rows.append((th, dist))
    return rows

def make_offline_index(csv_rows):
    mapping = dict(EXPANDED_AREA)  # seed with big-city areas
    for th, dist in csv_rows:
        mapping[th] = dist
    return mapping

# --------- Online (Nominatim) + cache ---------
def load_cache(cache_path):
    cache = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                cache[row["address"]] = (row["district"], row["thana"])
    return cache

def save_cache(cache_path, cache_dict):
    if not cache_path:
        return
    with open(cache_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["address", "district", "thana"])
        for k, (d, t) in cache_dict.items():
            w.writerow([k, d, t])

def nominatim_lookup(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "addressdetails": 1, "countrycodes": "bd", "limit": 1}
    headers = {"User-Agent": "BD-Address-Enricher/1.0 (educational; contact: youremail@example.com)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        if not data:
            return None, None
        comp = data[0].get("address", {})
        district = comp.get("state_district") or comp.get("county") or comp.get("state")
        thana = comp.get("suburb") or comp.get("city_district") or comp.get("town") or comp.get("city") or comp.get("village")
        if district: district = normalize(district).title()
        if thana: thana = normalize(thana).title()
        return district, thana
    except Exception:
        return None, None

# --------- Enrichment logic ---------
def offline_enrich(addr_norm, offline_map):
    d = guess_district_from_text(addr_norm)
    a = guess_area(addr_norm)
    district_out = d.title() if d else "Not found"
    thana_out = a.replace(" r a"," R/A").title().replace("R/a","R/A") if a else "Not found"

    # token scan using offline_map
    toks = addr_norm.replace(",", " ").split()
    grams = toks + [" ".join(toks[i:i+2]) for i in range(len(toks)-1)]
    for g in grams:
        g_norm = normalize(g)
        if g_norm in offline_map:
            if thana_out == "Not found": thana_out = g_norm.title()
            if district_out == "Not found": district_out = offline_map[g_norm].title()
            break
    return district_out, thana_out

def online_enrich(address, cache):
    if address in cache:
        d, t = cache[address]
        return d or "Not found", t or "Not found"
    d, t = nominatim_lookup(address)
    time.sleep(1.1)  # be polite
    cache[address] = (d or "Not found", t or "Not found")
    return cache[address]

def run(input_xlsx, output_xlsx, address_col=None, mode="auto", gazetteer_csv=None, cache_path=None, sheet_index=0):
    xls = pd.ExcelFile(input_xlsx)
    df = pd.read_excel(xls, xls.sheet_names[sheet_index])

    # find address col
    if address_col is None:
        for col in df.columns:
            c = str(col).strip().lower()
            if c in {"address"} or "address" in c or "addr" in c or "ঠিকানা" in c:
                address_col = col; break
        if address_col is None:
            address_col = df.columns[0]

    offline_map = make_offline_index(load_csv_gazetteer(gazetteer_csv)) if gazetteer_csv else make_offline_index([])
    cache = load_cache(cache_path) if cache_path else {}

    enriched = df.copy()
    DIST_COL, THANA_COL = "District", "Thana"
    if DIST_COL not in enriched.columns: enriched[DIST_COL] = ""
    if THANA_COL not in enriched.columns: enriched[THANA_COL] = ""

    for i, raw in enriched[address_col].items():
        addr = "" if pd.isna(raw) else str(raw)
        addr_norm = normalize(addr)

        district_out, thana_out = "Not found", "Not found"

        if mode == "offline":
            district_out, thana_out = offline_enrich(addr_norm, offline_map)
        elif mode == "online":
            district_out, thana_out = online_enrich(addr, cache)
        else:  # auto
            # Offline first
            d1, t1 = offline_enrich(addr_norm, offline_map)
            district_out, thana_out = d1, t1
            # Then fill missing via Online
            if (district_out == "Not found" or thana_out == "Not found"):
                d2, t2 = online_enrich(addr, cache)
                if district_out == "Not found": district_out = d2
                if thana_out == "Not found": thana_out = t2

        if not str(enriched.at[i, DIST_COL]).strip():
            enriched.at[i, DIST_COL] = district_out
        if not str(enriched.at[i, THANA_COL]).strip():
            enriched.at[i, THANA_COL] = thana_out

    with pd.ExcelWriter(output_xlsx, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Original", index=False)
        enriched.to_excel(writer, sheet_name="Enriched", index=False)

    if cache_path:
        save_cache(cache_path, cache)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--address-col", default=None)
    ap.add_argument("--mode", choices=["auto","offline","online"], default="auto")
    ap.add_argument("--csv-gazetteer", default="bangladesh_thana_district.csv")
    ap.add_argument("--cache", default="cache_geocode.csv")
    ap.add_argument("--sheet-index", type=int, default=0)
    args = ap.parse_args()

    run(
        input_xlsx=args.input,
        output_xlsx=args.output,
        address_col=args.address_col,
        mode=args.mode,
        gazetteer_csv=args.csv_gazetteer if os.path.exists(args.csv_gazetteer) else None,
        cache_path=args.cache,
        sheet_index=args.sheet_index,
    )
