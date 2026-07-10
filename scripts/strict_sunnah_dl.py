#!/usr/bin/env python3
"""Download all remaining data from sunnah.com AJAX API - strict sunnah.com source."""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sunnah.com-download")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://sunnah.com/",
}

def fetch_page(lang, slug, page):
    url = f"https://sunnah.com/ajax/{lang}/{slug}/{page}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read()
                if body.startswith(b"[") or "json" in r.headers.get("Content-Type", ""):
                    return json.loads(body.decode())
                return None
        except Exception:
            if attempt == 2:
                return None
            time.sleep(2 ** attempt)
    return None

def save_hadiths(slug, lang_code, hadiths):
    path = os.path.join(OUT_DIR, slug, f"{lang_code}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = {}
    if os.path.exists(path):
        with open(path) as f:
            for h in json.load(f):
                existing[h["hadithnumber"]] = h
    for h in hadiths:
        hn = h["hadithnumber"]
        if h.get("text"):
            existing[hn] = h
    ordered = sorted(existing.values(), key=lambda x: x["hadithnumber"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
    return len(ordered)

def download_book_pages(slug, lang, lang_code, max_page, chunk_label="", delay=0.3, workers=3):
    print(f"\n{'='*50}")
    print(f"{chunk_label or slug}/{lang} ({lang_code}): {max_page} pages")
    print(f"{'='*50}")
    
    out_path = os.path.join(OUT_DIR, slug, f"{lang_code}.json")
    existing = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            for h in json.load(f):
                if h.get("text"):
                    existing[h["hadithnumber"]] = h
    
    def get_new_hadiths_from_page(page):
        data = fetch_page(lang, slug, page)
        if not data:
            return page, []
        new = []
        for d in data:
            hn_raw = d.get("hadithNumber", "")
            hadith_num = hn_raw if isinstance(hn_raw, str) else str(hn_raw)
            if hadith_num not in existing:
                text = d.get("hadithText", "") or ""
                clean = text.replace('<span class="arabic_sanad">', "").replace("</span>", "")
                if clean:
                    new.append({"hadithnumber": hadith_num, "text": clean})
        return page, new

    all_new = {}
    pages_done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(get_new_hadiths_from_page, p): p for p in range(1, max_page + 1)}
        for future in as_completed(futures):
            page, new = future.result()
            for h in new:
                all_new[h["hadithnumber"]] = h
            pages_done += 1
            if pages_done % 10 == 0 or pages_done == max_page:
                print(f"  Pages: {pages_done}/{max_page}, new hadiths: {len(all_new)}")
            time.sleep(delay)

    total = save_hadiths(slug, lang_code, list(all_new.values()))
    print(f"  Saved {total} hadiths (added {len(all_new)} new)")

def main():
    # === Batch 1: Arabic for 3 missing books ===
    ranges = [
        ("ibnhibban", "arabic", "ar", 64),
        ("abdurrazzaq", "arabic", "ar", 31),
        ("nasaikubra", "arabic", "ar", 69),
    ]
    
    for slug, lang, code, pages in ranges:
        download_book_pages(slug, lang, code, pages, delay=0.3, workers=3)
        time.sleep(2)

    # === Batch 2: Bosnian for forty (nawawi40 + other hadiths) ===
    # The forty collection returns ALL hadiths at page 1
    data = fetch_page("bosnian", "forty", 1)
    if data and len(data) > 0:
        hadiths = []
        for d in data:
            text = d.get("hadithText", "") or ""
            hn = d.get("hadithNumber")
            if text and hn:
                hadiths.append({"hadithnumber": str(hn), "text": text})
        
        # Save to both forty and nawawi40
        for slug in ["forty", "nawawi40"]:
            total = save_hadiths(slug, "bs", hadiths)
            print(f"\n{slug}/bs: {total} hadiths saved")
        
        # Also extract nawawi40 subset (hadiths 1-42)
        path_nawawi = os.path.join(OUT_DIR, "nawawi40", "bs.json")
        with open(path_nawawi) as f:
            all_bs = json.load(f)
        nawawi42 = [h for h in all_bs if 1 <= int(h["hadithnumber"]) <= 42]
        with open(path_nawawi, "w") as f:
            json.dump(nawawi42, f, ensure_ascii=False, indent=2)
        print(f"  nawawi40/bs trimmed to {len(nawawi42)} hadiths (1-42)")

    # === Batch 3: Bangla for forty (if available) ===
    data = fetch_page("bangla", "forty", 1)
    if data and len(data) > 0:
        hadiths = []
        for d in data:
            text = d.get("hadithText", "") or ""
            hn = d.get("hadithNumber")
            if text and hn:
                hadiths.append({"hadithnumber": str(hn), "text": text})
        if hadiths:
            total = save_hadiths("forty", "bn", hadiths)
            print(f"\nforty/bn: {total} hadiths saved")

    print("\n" + "="*50)
    print("FINISHED")
    print("="*50)

if __name__ == "__main__":
    main()
