#!/usr/bin/env python3
"""
Super-fast sunnah.com downloader.

KEY OPTIMIZATION: One request per hadith fetches ALL available languages
(sunnah.com shows English, Arabic, Urdu, Bangla, Bosnian, etc. all on one page).

Phase 1: Download Arabic via API for books that have it (fast)
Phase 2: For books needing extra langs, scrape each hadith once, extract all langs
Phase 3: HTML-only books (darimi, ibnkhuzayma, etc.)
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sunnah.com-download")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
}

API_BASE = "https://api.islamic.app/v1/hadith/collections"

API_SLUGS = {
    "bukhari", "muslim", "nasai", "abudawud", "tirmidhi", "ibnmajah",
    "malik", "ahmad", "riyadussalihin", "adab", "shamail", "mishkat",
    "bulugh", "forty", "hisn", "virtues",
}

HTML_SLUGS = {
    "darimi", "ibnkhuzayma", "ibnhibban", "hakim", "abdurrazzaq",
    "ibnabishayba", "daraqutni", "bayhaqi", "nasaikubra", "nawawi40",
}

SUNNAH_BASE = "https://sunnah.com"

LANG_CODE_MAP = {
    "urdu": "ur", "bangla": "bn", "bosnian": "bs", "indonesian": "id",
    "turkish": "tr", "russian": "ru", "french": "fr", "german": "de",
    "spanish": "es", "malay": "ms", "persian": "fa", "swahili": "sw",
    "arabic": "ar", "english": "en", "hindi": "hi",
}

# All known language CSS class names on sunnah.com
LANG_CLASSES = {
    "english": "english_hadith",
    "arabic": "arabic_hadith",
    "urdu": "urdu_hadith",
    "bangla": "bangla_hadith",
    "bosnian": "bosnian_hadith",
    "indonesian": "indonesian_hadith",
    "turkish": "turkish_hadith",
    "russian": "russian_hadith",
    "french": "french_hadith",
    "german": "german_hadith",
    "spanish": "spanish_hadith",
    "malay": "malay_hadith",
    "hindi": "hindi_hadith",
    "persian": "persian_hadith",
    "swahili": "swahili_hadith",
}


def log(msg):
    print(msg, flush=True)


def fetch_url(url, retries=3, timeout=30):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                log(f"  Rate limited ({url[-30:]}), waiting {wait}s...")
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def fetch_json(url):
    text = fetch_url(url)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def write_lang_file(book_slug, lang_code, hadiths):
    ensure_dir(os.path.join(OUT_DIR, book_slug))
    path = os.path.join(OUT_DIR, book_slug, f"{lang_code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hadiths, f, ensure_ascii=False, indent=2)
    return path


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


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============ PHASE 1: API Arabic ============

def api_get_books(slug):
    data = fetch_json(f"{API_BASE}/{slug}/books")
    if data and data.get("code") == 200:
        return data["data"]
    return []


def api_get_hadiths_for_book(slug, book_number):
    all_h = []
    offset = 0
    while True:
        url = f"{API_BASE}/{slug}/books/{book_number}/hadiths?limit=200&offset={offset}"
        data = fetch_json(url)
        if not data or data.get("code") != 200:
            break
        hadiths = data["data"].get("hadiths", [])
        if not hadiths:
            break
        all_h.extend(hadiths)
        offset += len(hadiths)
        if offset >= len(all_h):
            break
    return all_h


def api_download_language(slug):
    """Download Arabic from API for a slug."""
    log(f"  {slug}: fetching Arabic via API...")
    books = api_get_books(slug)
    if not books:
        log(f"  No API data for {slug}")
        return False

    existing_ar = read_lang_file(slug, "ar")
    all_ar = []

    for bk in books:
        bn = bk["bookNumber"]
        hadiths = api_get_hadiths_for_book(slug, bn)
        for h in hadiths:
            hn = h["hadithNumber"]
            if hn not in existing_ar:
                ar = h.get("ar", {}) or {}
                all_ar.append({
                    "hadithnumber": hn,
                    "text": clean_text(ar.get("text", "")),
                })

    if all_ar:
        write_lang_file(slug, "ar", all_ar)
        log(f"  Wrote ar.json ({len(all_ar)} new hadiths)")
    else:
        log(f"  No new Arabic hadiths")
    return True


# ============ PHASE 2: Multi-language from single page ============

def discover_hadith_ids(slug, max_chapters=5):
    """Discover hadith IDs from sunnah.com chapter pages."""
    html = fetch_url(f"{SUNNAH_BASE}/{slug}")
    if not html:
        return []

    chapters = set()
    hadith_ids = set()

    for m in re.finditer(rf'/{re.escape(slug)}/(\d+)', html):
        chapters.add(int(m.group(1)))
    for m in re.finditer(rf'/{re.escape(slug)}:(\d+)', html):
        hadith_ids.add(int(m.group(1)))

    if not hadith_ids and chapters:
        # Get from first few chapter pages
        for ch in sorted(chapters)[:max_chapters]:
            html = fetch_url(f"{SUNNAH_BASE}/{slug}/{ch}")
            if html:
                for m in re.finditer(rf'/{re.escape(slug)}:(\d+)', html):
                    hadith_ids.add(int(m.group(1)))
            time.sleep(0.3)

    return sorted(hadith_ids)


def discover_available_langs(slug):
    """Discover what languages are available from the main page or any hadith page."""
    html = fetch_url(f"{SUNNAH_BASE}/{slug}")
    if not html:
        return {"english", "arabic"}
    langs = {"english", "arabic"}
    for m in re.finditer(r'href="/([a-z-]+)/' + re.escape(slug), html):
        lang = m.group(1)
        if lang in LANG_CODE_MAP:
            langs.add(lang)
    return langs


def extract_langs_from_page(html, langs_to_get):
    """Extract all requested languages from a single hadith page."""
    result = {}
    for lang_name in langs_to_get:
        lang_class = LANG_CLASSES.get(lang_name, f"{lang_name}_hadith")
        # Try full text first, then simple
        for pat in [
            rf'class="{re.escape(lang_class)}_full[^"]*"[^>]*>.*?class="text_details"[^>]*>(.*?)</div>',
            rf'class="{re.escape(lang_class)}[^"]*"[^>]*>(.*?)</div>',
        ]:
            m = re.search(pat, html, re.DOTALL)
            if m:
                text = clean_text(re.sub(r"<[^>]+>", " ", m.group(1)))
                if text:
                    result[lang_name] = text
                    break
    return result


def scrape_multi_lang(slug, hadith_ids, langs_to_get, workers=5, rate_limit_delay=0.3):
    """Scrape all hadiths - each request extracts ALL requested languages."""
    # Build lookup of existing data per language
    existing = {}
    for lang_name in langs_to_get:
        lang_code = LANG_CODE_MAP.get(lang_name, lang_name[:2])
        existing[lang_code] = read_lang_file(slug, lang_code)

    # Check what's missing per language
    missing = []
    for hid in hadith_ids:
        hs = str(hid)
        for lang_name in langs_to_get:
            lang_code = LANG_CODE_MAP.get(lang_name, lang_name[:2])
            if hs not in existing.get(lang_code, {}):
                missing.append((hid, lang_name))
                break

    # Group by hadith ID
    missing_ids = set(h for h, _ in missing)
    if not missing_ids:
        log(f"  All languages complete!")
        return

    log(f"  {len(missing_ids)} hadiths need fetching for {len(langs_to_get)} languages")
    log(f"  Using {workers} workers...")

    # Store results per language
    results = {lang: {} for lang in langs_to_get}
    success = 0
    fail = 0
    done = 0
    total = len(missing_ids)

    def fetch_hadith(hid):
        url = f"{SUNNAH_BASE}/{slug}:{hid}"
        html = fetch_url(url, timeout=15)
        if not html:
            return hid, {}
        texts = extract_langs_from_page(html, langs_to_get)
        return hid, texts

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_hadith, hid): hid for hid in missing_ids}
        for future in as_completed(futures):
            hid = futures[future]
            try:
                _, texts = future.result()
            except Exception:
                texts = {}
            if texts:
                success += 1
            else:
                fail += 1
            for lang_name, text in texts.items():
                results[lang_name][str(hid)] = text
            done += 1
            if done % 200 == 0 or done == total:
                log(f"    {done}/{total} ✅{success} ❌{fail}")
            time.sleep(rate_limit_delay)

    # Write files
    for lang_name in langs_to_get:
        lang_code = LANG_CODE_MAP.get(lang_name, lang_name[:2])
        merged = dict(existing.get(lang_code, {}))
        for hs, text in results[lang_name].items():
            merged[hs] = {"hadithnumber": hs, "text": text}
        ordered = [merged.get(str(h), {"hadithnumber": str(h), "text": ""}) for h in hadith_ids]
        path = write_lang_file(slug, lang_code, ordered)
        written = sum(1 for h in ordered if h.get("text"))
        log(f"    {lang_code}.json: {written}/{len(ordered)} hadiths with text → {path}")

    log(f"  Done: ✅{success} ❌{fail}")


# ============ MAIN ============

def phase1():
    log("=" * 60)
    log("PHASE 1: Arabic from API")
    log("=" * 60)
    for slug in sorted(API_SLUGS):
        needs_ar = not bool(read_lang_file(slug, "ar"))
        needs_en = not bool(read_lang_file(slug, "en"))
        if not needs_ar and not needs_en:
            continue
        if needs_en and needs_ar:
            log(f"  {slug}: needs en+ar (will get from API)")
        elif needs_ar:
            log(f"  {slug}: needs Arabic")
        try:
            if needs_ar:
                api_download_language(slug)
            if needs_en:
                # Need en.json - use API if available
                pass  # Phase 2/3 handles this
        except Exception as e:
            log(f"  ERROR: {e}")
        time.sleep(0.2)
    log("Phase 1 done\n")


def phase2():
    log("=" * 60)
    log("PHASE 2: Extra languages via multi-lang page scrape")
    log("=" * 60)

    books_to_scrape = {
        "bukhari": ["urdu", "bangla"],
        "abudawud": ["urdu"],
        "nawawi40": ["bangla", "bosnian", "english", "arabic"],
        "forty": ["bangla", "bosnian"],
    }

    for slug, langs in books_to_scrape.items():
        log(f"\n--- {slug} ---")
        hadith_ids = discover_hadith_ids(slug)
        if not hadith_ids:
            log(f"  Cannot discover hadiths, skipping")
            continue
        log(f"  Hadith IDs: {len(hadith_ids)} ({hadith_ids[0]}-{hadith_ids[-1]})")
        scrape_multi_lang(slug, hadith_ids, langs, workers=5, rate_limit_delay=0.5)
        time.sleep(2)

    log("Phase 2 done\n")


def phase3():
    log("=" * 60)
    log("PHASE 3: HTML-only books")
    log("=" * 60)

    for slug in sorted(HTML_SLUGS):
        if slug in ("nawawi40",):  # Already handled in phase2
            continue
        log(f"\n--- {slug} ---")
        try:
            hadith_ids = discover_hadith_ids(slug)
            if not hadith_ids:
                log(f"  Cannot discover hadiths, skipping")
                continue
            log(f"  Hadith IDs: {len(hadith_ids)} ({hadith_ids[0]}-{hadith_ids[-1]})")
            langs = discover_available_langs(slug)
            log(f"  Languages: {', '.join(sorted(langs))}")
            scrape_multi_lang(slug, hadith_ids, sorted(langs), workers=5, rate_limit_delay=0.5)
        except Exception as e:
            log(f"  ERROR: {e}")
        time.sleep(2)

    log("Phase 3 done\n")


if __name__ == "__main__":
    log("Super-fast sunnah.com downloader\n")
    os.makedirs(OUT_DIR, exist_ok=True)
    phase1()
    phase2()
    phase3()
    log("=" * 60)
    log("ALL DONE!")
    log("=" * 60)
