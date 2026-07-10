#!/usr/bin/env python3
"""Download from sunnah.com AJAX API only - strict sunnah.com source."""

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


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read()
                ct = r.headers.get("Content-Type", "")
                if body.startswith(b"[") or "json" in ct:
                    return json.loads(body.decode())
                return None
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2 * (attempt + 1))
    return None


def write_lang(slug, lang_code, hadiths):
    d = os.path.join(OUT_DIR, slug)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{lang_code}.json")
    # Merge with existing
    existing = {}
    if os.path.exists(p):
        with open(p) as f:
            for h in json.load(f):
                existing[h["hadithnumber"]] = h
    for h in hadiths:
        hn = h["hadithnumber"]
        if h.get("text"):
            if hn in existing:
                existing[hn]["text"] = h["text"]
            else:
                existing[hn] = h
    ordered = sorted(existing.values(), key=lambda x: int(x["hadithnumber"]))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
    return len(ordered)


def download_range(slug, lang, lang_code, start, end, workers=5, delay=0.5):
    """Download a range of hadiths from sunnah.com AJAX API."""
    print(f"\n{slug}/{lang} ({lang_code}): hadiths {start}-{end}")

    out_path = os.path.join(OUT_DIR, slug, f"{lang_code}.json")
    existing = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            for h in json.load(f):
                if h.get("text"):
                    existing[h["hadithnumber"]] = h

    missing = [str(i) for i in range(start, end + 1) if str(i) not in existing]
    if not missing:
        print(f"  Already complete ({len(existing)} hadiths)")
        return

    print(f"  Fetching {len(missing)}/{end-start+1} hadiths...")
    results = {}
    success = 0
    fail = 0

    def fetch_one(hn):
        url = f"https://sunnah.com/ajax/{lang}/{slug}/{hn}"
        data = fetch_json(url)
        if data and len(data) > 0:
            text = data[0].get("hadithText", "")
            return hn, text
        return hn, ""

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_one, h): h for h in missing}
        done = 0
        total = len(missing)
        for future in as_completed(futures):
            hn, text = future.result()
            if text:
                success += 1
            else:
                fail += 1
            results[hn] = {"hadithnumber": hn, "text": text}
            done += 1
            if done % 50 == 0 or done == total:
                print(f"    {done}/{total} ✅{success} ❌{fail}")
            time.sleep(delay)

    # Merge and write
    all_hadiths = {}
    for h in existing.values():
        all_hadiths[h["hadithnumber"]] = h
    for hn, h in results.items():
        if h.get("text"):
            all_hadiths[hn] = h

    ordered = [all_hadiths.get(str(i), {"hadithnumber": str(i), "text": ""}) for i in range(start, end + 1)]
    write_lang(slug, lang_code, ordered)
    print(f"  Saved {len(ordered)} hadiths")


def discover_total(slug, lang, max_check=50):
    """Discover total hadith count by binary search."""
    # First find an upper bound
    upper = 1
    for _ in range(20):
        data = fetch_json(f"https://sunnah.com/ajax/{lang}/{slug}/{upper}")
        if data and len(data) > 0:
            upper *= 2
        else:
            break
        time.sleep(0.5)

    # Binary search
    lo, hi = upper // 2, upper
    while lo < hi:
        mid = (lo + hi + 1) // 2
        data = fetch_json(f"https://sunnah.com/ajax/{lang}/{slug}/{mid}")
        if data and len(data) > 0:
            lo = mid
        else:
            hi = mid - 1
        time.sleep(0.5)

    print(f"  Discovered total: ~{lo} hadiths for {slug}/{lang}")
    return lo


def main():
    print("=" * 60)
    print("STRICT sunnah.com AJAX downloader")
    print("=" * 60)

    # === Batch 1: Bosnian for forty (includes nawawi40 + qudsi + dehlawi) ===
    print("\n--- Batch 1: Bosnian for forty ---")
    download_range("forty", "bosnian", "bs", 1, 122, workers=5, delay=0.3)

    # === Batch 2: Arabic for missing books ===
    print("\n--- Batch 2: Arabic for missing books ---")
    for slug in ["ibnhibban", "abdurrazzaq", "nasaikubra"]:
        total = discover_total(slug, "arabic")
        if total > 0:
            download_range(slug, "arabic", "ar", 1, total, workers=5, delay=0.3)
        else:
            print(f"  {slug}/arabic: not available")
        time.sleep(2)

    # === Batch 3: Try English for missing books ===
    print("\n--- Batch 3: English for missing books ---")
    for slug in ["ibnhibban", "abdurrazzaq", "nasaikubra"]:
        total = discover_total(slug, "english")
        if total > 0:
            download_range(slug, "english", "en", 1, total, workers=5, delay=0.3)
        else:
            print(f"  {slug}/english: not available")
        time.sleep(2)

    print("\n" + "=" * 60)
    print("ALL DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
