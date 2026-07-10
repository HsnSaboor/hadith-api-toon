#!/usr/bin/env python3
"""Download translations from sunnah.com AJAX API (no rate limiting, fast JSON)."""

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
}

# Format: (collection_slug, language_name, lang_code, hadith_range)
# Languages confirmed available from avbl_languages on sunnah.com
DOWNLOADS = [
    # Bosnian
    ("nawawi40", "bosnian", "bs", range(1, 43)),
    ("forty", "bosnian", "bs", None),  # None = auto-discover from en.json
    # Bangla for forty
    ("forty", "bangla", "bn", None),
    # Also try Bangla for nawawi40 (already done, but just in case)
    # Other languages for remaining books
    ("ibnhibban", "english", "en", None),
    ("ibnhibban", "arabic", "ar", None),
    ("abdurrazzaq", "english", "en", None),
    ("abdurrazzaq", "arabic", "ar", None),
    ("nasaikubra", "english", "en", None),
    ("nasaikubra", "arabic", "ar", None),
]


def fetch_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def read_en_json(book_slug):
    path = os.path.join(OUT_DIR, book_slug, "en.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return [h["hadithnumber"] for h in data]
    return []


def read_existing(book_slug, lang_code):
    path = os.path.join(OUT_DIR, book_slug, f"{lang_code}.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return {h["hadithnumber"] for h in data if h.get("text")}
    return set()


def write_json(book_slug, lang_code, hadiths):
    out_dir = os.path.join(OUT_DIR, book_slug)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{lang_code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hadiths, f, ensure_ascii=False, indent=2)
    return path


def download_translation(collection, lang, lang_code, hadith_ids, workers=10):
    """Download translations using sunnah.com AJAX API."""
    existing = read_existing(collection, lang_code)
    missing = [h for h in hadith_ids if h not in existing]
    
    if not missing:
        print(f"  {collection}/{lang_code}: complete ({len(existing)} hadiths)")
        return

    print(f"  {collection}/{lang_code}: fetching {len(missing)} hadiths...")
    results = {}
    success = 0

    def fetch_one(hid):
        url = f"https://sunnah.com/ajax/{lang}/{collection}/{hid}"
        data = fetch_json(url)
        if data and len(data) > 0:
            text = data[0].get("hadithText", "")
            return hid, text
        return hid, ""

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_one, hid): hid for hid in missing}
        for future in as_completed(futures):
            hid, text = future.result()
            if text:
                success += 1
            results[str(hid)] = {"hadithnumber": str(hid), "text": text}

    # Merge with existing
    existing_data = {}
    path = os.path.join(OUT_DIR, collection, f"{lang_code}.json")
    if os.path.exists(path):
        with open(path) as f:
            for item in json.load(f):
                existing_data[item["hadithnumber"]] = item

    for hn, h in results.items():
        if hn in existing_data and h.get("text"):
            existing_data[hn]["text"] = h["text"]
        elif h.get("text"):
            existing_data[hn] = h

    # Re-order by hadith_ids
    final = []
    for hid in hadith_ids:
        hs = str(hid)
        if hs in existing_data:
            final.append(existing_data[hs])
        else:
            final.append({"hadithnumber": hs, "text": ""})

    write_json(collection, lang_code, final)
    print(f"    Saved {len(final)} hadiths, ✅{success} ❌{len(missing)-success}")


def main():
    print("=" * 60)
    print("Downloading from sunnah.com AJAX API")
    print("=" * 60)

    for collection, lang, lang_code, hadith_range in DOWNLOADS:
        print(f"\n--- {collection}/{lang} ---")
        
        # Determine hadith IDs
        if hadith_range:
            hadith_ids = list(hadith_range)
        else:
            hadith_ids = read_en_json(collection)
            if not hadith_ids:
                print(f"  No en.json found, trying discovery...")
                # Use the AJAX API to discover: get hadith 1 and check total
                data = fetch_json(f"https://sunnah.com/ajax/{lang}/{collection}/1")
                if data and len(data) > 0:
                    # Try to infer total from metadata
                    print(f"  Got data for hadith 1, trying common ranges...")
                    # Try up to 10000
                    hadith_ids = list(range(1, 10001))
                else:
                    print(f"  Cannot discover hadiths, skipping")
                    continue

        download_translation(collection, lang, lang_code, hadith_ids)

    print("\nDone!")


if __name__ == "__main__":
    main()
