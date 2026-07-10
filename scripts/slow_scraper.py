#!/usr/bin/env python3
"""
Slow but steady scraper for sunnah.com.
For the remaining missing content:
  - Missing books: ibnhibban, abdurrazzaq, nasaikubra
  - Missing languages: Bosnian for nawawi40, forty
  - Bengali for forty

Uses 1 worker with 2s delay to avoid rate limiting.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sunnah.com-download")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
}

SUNNAH_BASE = "https://sunnah.com"

LANG_CODE_MAP = {
    "urdu": "ur", "bangla": "bn", "bosnian": "bs", "indonesian": "id",
    "turkish": "tr", "russian": "ru", "french": "fr", "german": "de",
    "spanish": "es", "malay": "ms", "persian": "fa", "swahili": "sw",
    "arabic": "ar", "english": "en", "hindi": "hi",
}


def log(msg):
    print(msg, flush=True)


def fetch_url(url, retries=5):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                log(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            time.sleep(3 * (attempt + 1))
        except Exception as e:
            time.sleep(3 * (attempt + 1))
    return None


def read_lang_file(book_slug, lang_code):
    path = os.path.join(OUT_DIR, book_slug, f"{lang_code}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {item["hadithnumber"]: item for item in data if "hadithnumber" in item}
    except Exception:
        return {}


def write_lang_file(book_slug, lang_code, hadiths):
    ensure_dir(os.path.join(OUT_DIR, book_slug))
    path = os.path.join(OUT_DIR, book_slug, f"{lang_code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hadiths, f, ensure_ascii=False, indent=2)
    return path


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def discover_sunnah_book(slug):
    """Discover all hadith IDs by crawling all chapter pages."""
    log(f"  Discovering {slug}...")
    html = fetch_url(f"{SUNNAH_BASE}/{slug}")
    if not html:
        return []

    chapters = set()
    for m in re.finditer(rf'/{re.escape(slug)}/(\d+)', html):
        chapters.add(int(m.group(1)))

    if not chapters:
        log(f"  No chapters found on main page")
        return []

    log(f"  Found {len(chapters)} chapters on main page")

    all_ids = set()
    for i, ch in enumerate(sorted(chapters)):
        html = fetch_url(f"{SUNNAH_BASE}/{slug}/{ch}")
        if html:
            for m in re.finditer(rf'/{re.escape(slug)}:(\d+)', html):
                all_ids.add(int(m.group(1)))
        time.sleep(1.5)
        if (i + 1) % 50 == 0:
            log(f"    Scanned {i+1}/{len(chapters)} chapters, found {len(all_ids)} hadiths")

    result = sorted(all_ids)
    log(f"  Found {len(result)} hadith IDs")
    return result


def scrape_single_lang(slug, lang_name, hadith_ids):
    """Scrape all hadiths for ONE language with 1 worker and 2s delay."""
    lang_code = LANG_CODE_MAP.get(lang_name, lang_name[:2])
    lang_path = "" if lang_name == "english" else f"/{lang_name}"

    existing = read_lang_file(slug, lang_code)
    missing = [h for h in hadith_ids if str(h) not in existing]
    if not missing:
        log(f"  {lang_name}: complete")
        return

    log(f"  {lang_name}: fetching {len(missing)}/{len(hadith_ids)} hadiths (1 worker, ~3s each)")
    success = 0
    fail = 0

    for i, hid in enumerate(missing):
        url = f"{SUNNAH_BASE}{lang_path}/{slug}:{hid}"
        html = fetch_url(url)
        text = ""
        if html:
            lang_class = f"{lang_name}_hadith"
            for pat in [
                rf'class="{re.escape(lang_class)}_full[^"]*"[^>]*>.*?class="text_details"[^>]*>(.*?)</div>',
                rf'class="{re.escape(lang_class)}[^"]*"[^>]*>(.*?)</div>',
            ]:
                m = re.search(pat, html, re.DOTALL)
                if m:
                    text = clean_text(re.sub(r"<[^>]+>", " ", m.group(1)))
                    break

        if text:
            success += 1
        else:
            fail += 1

        existing[str(hid)] = {"hadithnumber": str(hid), "text": text}

        if (i + 1) % 25 == 0 or i == len(missing) - 1:
            log(f"    [{i+1}/{len(missing)}] ✅{success} ❌{fail}")
            # Save every 25
            ordered = [existing.get(str(h), {"hadithnumber": str(h), "text": ""}) for h in hadith_ids]
            write_lang_file(slug, lang_code, ordered)

        time.sleep(2.5)

    ordered = [existing.get(str(h), {"hadithnumber": str(h), "text": ""}) for h in hadith_ids]
    write_lang_file(slug, lang_code, ordered)
    log(f"  Done {lang_name}: {len(ordered)} total, ✅{success} ❌{fail}")


def main():
    log("=" * 60)
    log("Slow but steady sunnah.com scraper")
    log("=" * 60)

    # Missing books
    missing_books = ["ibnhibban", "abdurrazzaq", "nasaikubra"]

    for slug in missing_books:
        log(f"\n--- {slug} ---")
        hadith_ids = discover_sunnah_book(slug)
        if not hadith_ids:
            log(f"  Could not discover hadiths, skipping")
            continue

        # Check available languages
        html = fetch_url(f"{SUNNAH_BASE}/{slug}")
        langs = {"english", "arabic"}
        if html:
            for m in re.finditer(r'href="/([a-z-]+)/' + re.escape(slug), html):
                lang = m.group(1)
                if lang in LANG_CODE_MAP:
                    langs.add(lang)

        log(f"  Languages: {', '.join(sorted(langs))}")
        for lang_name in sorted(langs):
            try:
                scrape_single_lang(slug, lang_name, hadith_ids)
            except Exception as e:
                log(f"  ERROR: {e}")
            time.sleep(2)

    # Extra languages for existing books
    extra = [
        ("nawawi40", "bosnian"),
        ("forty", "bangla"),
        ("forty", "bosnian"),
    ]

    log(f"\n--- Extra languages ---")
    for slug, lang_name in extra:
        log(f"\n  {slug}: {lang_name}")
        lang_code = LANG_CODE_MAP.get(lang_name, lang_name[:2])
        existing = read_lang_file(slug, lang_code)
        if existing:
            log(f"  Already has {len(existing)} entries, checking what's missing...")

        # Get hadith IDs from the en.json file
        en_path = os.path.join(OUT_DIR, slug, "en.json")
        if os.path.exists(en_path):
            with open(en_path) as f:
                en_data = json.load(f)
            hadith_ids = [int(h["hadithnumber"]) for h in en_data]
            log(f"  Using {len(hadith_ids)} hadith IDs from en.json")
            scrape_single_lang(slug, lang_name, hadith_ids)
        else:
            log(f"  No en.json for {slug}, discovering from sunnah.com")
            hadith_ids = discover_sunnah_book(slug)
            if hadith_ids:
                scrape_single_lang(slug, lang_name, hadith_ids)

    log("\n" + "=" * 60)
    log("ALL DONE!")
    log("=" * 60)


if __name__ == "__main__":
    main()
