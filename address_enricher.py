#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, csv, time, argparse, requests
import pandas as pd
from difflib import get_close_matches

# ---------------- Utilities ----------------
def normalize(s: str) -> str:
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = s.lower()
    replacements = {
        "dacca": "dhaka", "chittagong": "chattogram", "ctg": "chattogram",
        "barisal": "barishal", "cumilla": "comilla", "uttora": "uttara",
        "gulshan-1": "gulshan 1", "gulshan-2": "gulshan 2",
        "badda thana": "badda", "banani thana": "banani",
        "kotowali": "kotwali", "mohammad pur": "mohammadpur",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9,/\-\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def bangla_normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    rep = {
        "ঢাকা":"Dhaka","চট্টগ্রাম":"Chattogram","কমিল্লা":"Comilla","কুমিল্লা":"Comilla",
        "বগুড়া":"Bogura","নরসিংদী":"Narsingdi","নরায়ণগঞ্জ":"Narayanganj",
        "সিলেট":"Sylhet","খুলনা":"Khulna","বরিশাল":"Barishal","রাজশাহী":"Rajshahi",
        "কিশোরগঞ্জ":"Kishoreganj","দিনাজপুর":"Dinajpur","ফেনী":"Feni","নোয়াখালী":"Noakhali",
        "লক্ষ্মীপুর":"Lakshmipur","শ্যামলী":"Shyamoli","গুলশান":"Gulshan","বানানী":"Banani",
        "উত্তরা":"Uttara","বাড্ডা":"Badda","মতিঝিল":"Motijheel","শাহবাগ":"Shahbag",
    }
    for a, b in rep.items():
        s = s.replace(a, b)
    return s

def to_english(s: str | None) -> str:
    if not s or str(s).strip().lower() == "not found":
        return "Not found"
    txt = bangla_normalize_text(str(s).strip())
    canon = {
        "Chittagong": "Chattogram",
        "Jessore": "Jashore",
        "Barisal": "Barishal",
        "Cumilla": "Comilla",
        "Bogra": "Bogura",
        "Cox'S Bazar": "Cox S Bazar",
        "Cox's Bazar": "Cox S Bazar",
    }
    txt = canon.get(txt, txt)
    return txt.title()

# ---------------- Data seeds ----------------
DISTRICTS = [
    "dhaka","gazipur","narayanganj","munshiganj","manikganj","narshingdi","kishoreganj","tangail",
    "mymensingh","jamalpur","netrokona","sherpur","faridpur","madaripur","gopalganj","rajbari","shariatpur",
    "chattogram","cox s bazar","feni","noakhali","lakshmipur","rangamati","khagrachhari","bandarban","comilla","brahmanbaria",
    "sylhet","moulvibazar","habiganj","sunamganj","khulna","jashore","satkhira","bagerhat","chuadanga","kushtia",
    "meherpur","jhenaidah","magura","narail","rajshahi","chapainawabganj","naogaon","natore","pabna","sirajganj","bogura",
    "barishal","patuakhali","barguna","jhalokathi","pirojpur","bhola","rangpur","dinajpur","nilphamari","lalmonirhat",
    "kurigram","gaibandha","thakurgaon","panchagarh"
]
DISTRICT_ALIASES = {
    "laxmipur":"lakshmipur","bogra":"bogura","jessore":"jashore","barisal":"barishal",
    "chittagong":"chattogram","coxsbazar":"cox s bazar","cox's bazar":"cox s bazar",
}

AREA_TO_DISTRICT = {
    # Dhaka city
    "gulshan":"dhaka","banani":"dhaka","baridhara":"dhaka","badda":"dhaka","uttara":"dhaka","mirpur":"dhaka",
    "mohammadpur":"dhaka","tejgaon":"dhaka","dhanmondi":"dhaka","lalbagh":"dhaka","kafrul":"dhaka","cantonment":"dhaka",
    "airport":"dhaka","ramna":"dhaka","motijheel":"dhaka","paltan":"dhaka","sabujbagh":"dhaka","khilgaon":"dhaka",
    "rampura":"dhaka","jatrabari":"dhaka","mugda":"dhaka","wari":"dhaka","demra":"dhaka","shyampur":"dhaka",
    "kamrangirchar":"dhaka","adabor":"dhaka","hazaribagh":"dhaka","shahbag":"dhaka","banglamotor":"dhaka",
    "bansree":"dhaka","khilkhet":"dhaka","bosila":"dhaka","niketan":"dhaka",
    "bashundhara":"dhaka","bashundhara r/a":"dhaka","nakhalpara":"dhaka","tejgaon industrial area":"dhaka","zigatola":"dhaka",
    # Gazipur
    "tongi":"gazipur","joydebpur":"gazipur","kaliakair":"gazipur","kaliganj":"gazipur","sreepur":"gazipur",
    # Narayanganj
    "siddhirganj":"narayanganj","bandar":"narayanganj","fatulla":"narayanganj",
    # Chattogram city
    "kotwali":"chattogram","panchlaish":"chattogram","double mooring":"chattogram","pahartali":"chattogram",
    "halishahar":"chattogram","patenga":"chattogram","bakalia":"chattogram","bandar thana":"chattogram",
    "chandgaon":"chattogram","akbar shah":"chattogram","bayazid":"chattogram",
    # Sylhet city
    "kotwali sylhet":"sylhet","south surma":"sylhet","moglabazar":"sylhet","subidbazar":"sylhet",
    # Rajshahi city
    "boalia":"rajshahi","motihar":"rajshahi","rajpara":"rajshahi","shah makhdum":"rajshahi",
    # Khulna city
    "khalishpur":"khulna","daulatpur":"khulna","sonadanga":"khulna","khulna kotwali":"khulna",
    # Others
    "barishal kotwali":"barishal","airport barishal":"barishal",
    "kotwali comilla":"comilla","adarsa sadar":"comilla",
    "sadar noakhali":"noakhali","sadar bogura":"bogura",
}
def _expand(area_to_district):
    out = {}
    for k, v in area_to_district.items():
        for variant in {k, k.replace("-", " "), k.replace(" ", ""), k.replace("/", " ")}:
            out[normalize(variant)] = v
    return out
EXPANDED_AREA = _expand(AREA_TO_DISTRICT)
AREA_KEYS = list(set(EXPANDED_AREA.keys()))
DISTRICT_KEYS = list(set([normalize(d) for d in DISTRICTS] + list(DISTRICT_ALIASES.keys())))

# ---------------- Guessers (offline) ----------------
def guess_area(addr_norm: str) -> str | None:
    for a in AREA_KEYS:
        if re.search(rf"\b{re.escape(a)}\b", addr_norm):
            return a
    toks = addr_norm.replace(",", " ").split()
    grams = toks + [" ".join(toks[i:i+2]) for i in range(len(toks)-1)]
    for g in grams:
        g = normalize(g)
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
        m = get_close_matches(t, [normalize(x) for x in DISTRICTS], n=1, cutoff=0.88)
        if m:
            return m[0]
    return None

# ---------------- Gazetteer (UTF-8 SAFE) ----------------
def load_csv_gazetteer(path: str):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    # try pandas (utf-8, utf-8-sig)
    for enc in ("utf-8", "utf-8-sig"):
        try:
            df = pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
            cols = {c.lower(): c for c in df.columns}
            th_col = cols.get("thana") or cols.get("upazila") or cols.get("area") or list(df.columns)[0]
            di_col = cols.get("district") or list(df.columns)[1]
            for _, r in df[[th_col, di_col]].dropna().iterrows():
                th = normalize(str(r[th_col]))
                di = normalize(str(r[di_col]))
                if th and di:
                    rows.append((th, di))
            return rows
        except Exception:
            continue
    # fallback csv
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        r = csv.DictReader(f)
        for row in r:
            th = normalize(row.get("thana") or row.get("upazila") or row.get("area") or "")
            di = normalize(row.get("district") or "")
            if th and di:
                rows.append((th, di))
    return rows

def make_offline_index(csv_rows):
    m = dict(EXPANDED_AREA)
    for th, di in csv_rows:
        m[th] = di
    return m

# ---------------- Cache ----------------
def load_cache(cache_path):
    cache = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, newline="", encoding="utf-8", errors="ignore") as f:
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

# ---------------- Online (OSM) ----------------
def nominatim_lookup(address):
    base = "https://nominatim.openstreetmap.org/search"
    headers = {
        "User-Agent": "BD-Address-Enricher/1.1 (educational; contact: youremail@example.com)",
        "Accept-Language": "en"
    }
    raw = (address or "").strip()
    attempts = [
        raw,
        bangla_normalize_text(raw),
        f"{raw}, Bangladesh" if "bangladesh" not in raw.lower() else raw,
        re.sub(r"\s+", " ", raw.replace(",", " ")) + ", Bangladesh",
    ]
    for q in attempts:
        if not q or len(q.strip()) < 3:
            continue
        try:
            r = requests.get(
                base,
                params={"q": q, "format": "json", "addressdetails": 1, "countrycodes": "bd", "limit": 1},
                headers=headers, timeout=20
            )
            if r.status_code != 200:
                time.sleep(1.1); continue
            js = r.json()
            if not js:
                time.sleep(1.1); continue
            comp = js[0].get("address", {})
            d = comp.get("state_district") or comp.get("district") or comp.get("county") or comp.get("state")
            t = (comp.get("suburb") or comp.get("neighbourhood") or comp.get("city_district") or
                 comp.get("municipality") or comp.get("borough") or comp.get("town") or
                 comp.get("city") or comp.get("village") or comp.get("police"))
            return to_english(d), to_english(t)
        except Exception:
            time.sleep(1.1); continue
    return None, None

# ---------------- Enrichment ----------------
def offline_enrich(addr_norm, offline_map):
    d = guess_district_from_text(addr_norm)
    a = guess_area(addr_norm)
    district_out = to_english(d) if d else "Not found"
    thana_out    = to_english(a.replace(" r a"," R/A")) if a else "Not found"

    toks = addr_norm.replace(",", " ").split()
    grams = toks + [" ".join(toks[i:i+2]) for i in range(len(toks)-1)]
    for g in grams:
        g_norm = normalize(g)
        if g_norm in offline_map:
            if thana_out == "Not found": thana_out = to_english(g_norm)
            if district_out == "Not found": district_out = to_english(offline_map[g_norm])
            break
    return district_out, thana_out

def online_enrich(address, cache):
    if address in cache:
        d, t = cache[address]
        return to_english(d), to_english(t)
    d, t = nominatim_lookup(address)
    time.sleep(1.1)  # respect OSM
    cache[address] = (d or "Not found", t or "Not found")
    return cache[address]

NUMERIC_ONLY = re.compile(r"^\d+([/.,-]\d+)*$")

def run(input_xlsx, output_xlsx, address_col=None, mode="auto",
        gazetteer_csv=None, cache_path=None, sheet_index=0,
        retry_online_notfound=True):
    xls = pd.ExcelFile(input_xlsx)
    df = pd.read_excel(xls, xls.sheet_names[sheet_index])

    # detect address column
    if address_col is None:
        for col in df.columns:
            c = str(col).strip().lower()
            if c in {"address"} or "address" in c or "addr" in c or "ঠিকানা" in c:
                address_col = col; break
        if address_col is None: address_col = df.columns[0]

    offline_map = make_offline_index(load_csv_gazetteer(gazetteer_csv)) if gazetteer_csv else make_offline_index([])
    cache = load_cache(cache_path) if cache_path else {}

    enriched = df.copy()
    if "District" not in enriched.columns: enriched["District"] = ""
    if "Thana" not in enriched.columns: enriched["Thana"] = ""

    for i, raw in enriched[address_col].items():
        addr = "" if pd.isna(raw) else str(raw)
        addr_norm = normalize(addr)
        district_out, thana_out = "Not found", "Not found"

        if mode == "offline":
            district_out, thana_out = offline_enrich(addr_norm, offline_map)
        elif mode == "online":
            district_out, thana_out = online_enrich(addr, cache)
        else:  # auto
            d1, t1 = offline_enrich(addr_norm, offline_map)
            district_out, thana_out = d1, t1
            if district_out == "Not found" or thana_out == "Not found":
                d2, t2 = online_enrich(addr, cache)
                if district_out == "Not found": district_out = d2
                if thana_out == "Not found": thana_out = t2

        if retry_online_notfound and (district_out == "Not found" or thana_out == "Not found") and mode != "online":
            d3, t3 = online_enrich(addr, cache)
            if district_out == "Not found" and d3: district_out = d3
            if thana_out == "Not found" and t3: thana_out = t3

        # force English
        district_out = to_english(district_out)
        thana_out    = to_english(thana_out)

        # 🚫 numeric-only cleanup (e.g., "6", "2/45/5/162")
        if NUMERIC_ONLY.fullmatch(str(thana_out).strip()):   thana_out = "Not found"
        if NUMERIC_ONLY.fullmatch(str(district_out).strip()): district_out = "Not found"

        if not str(enriched.at[i, "District"]).strip():
            enriched.at[i, "District"] = district_out
        if not str(enriched.at[i, "Thana"]).strip():
            enriched.at[i, "Thana"] = thana_out

    with pd.ExcelWriter(output_xlsx, engine="xlsxwriter") as w:
        df.to_excel(w, sheet_name="Original", index=False)
        enriched.to_excel(w, sheet_name="Enriched", index=False)

    if cache_path: save_cache(cache_path, cache)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--address-col", default=None)
    ap.add_argument("--mode", choices=["auto","offline","online"], default="auto")
    ap.add_argument("--csv-gazetteer", default="bangladesh_thana_district.csv")
    ap.add_argument("--cache", default="cache_geocode.csv")
    ap.add_argument("--sheet-index", type=int, default=0)
    ap.add_argument("--retry-online-notfound", action="store_true")
    args = ap.parse_args()

    run(
        input_xlsx=args.input,
        output_xlsx=args.output,
        address_col=args.address_col,
        mode=args.mode,
        gazetteer_csv=args.csv_gazetteer if os.path.exists(args.csv_gazetteer) else None,
        cache_path=args.cache,
        sheet_index=args.sheet_index,
        retry_online_notfound=bool(args.retry_online_notfound or True),
    )
