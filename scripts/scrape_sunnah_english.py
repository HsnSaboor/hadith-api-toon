"""
Scrape English translations from sunnah.com for 8 new books.
Uses the sunnah.com API (they have an official one at sunnah.com/api).
"""

import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# sunnah.com slug -> our book key
SUNNAH_BOOKS = {
    "ahmad": "musnad-ahmed",
    "adab": "aladab-almufrad",
    "shamail": "shamail-tirmazi",
    "mishkat": "mishkat",
    "bulugh": "bulugh-al-maram",
    "hisn": "hisn-al-muslim",
    "forty": "collections-of-forty",
    "darimi": "sunan-darmi",
}


def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except:
        return ""


def discover_chapters(sunnah_slug):
    """Get all chapter IDs from sunnah.com book page."""
    html = fetch(f"https://sunnah.com/{sunnah_slug}")
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    chapters = []
    for a in soup.find_all("a", href=True):
        m = re.search(rf"/{re.escape(sunnah_slug)}/(\d+)$", a["href"])
        if m:
            ch_id = int(m.group(1))
            if ch_id not in chapters:
                chapters.append(ch_id)
    return sorted(chapters)


def discover_hadiths(sunnah_slug, chapter_id):
    """Get hadith IDs from a sunnah.com chapter page."""
    url = f"https://sunnah.com/{sunnah_slug}/{chapter_id}"
    html = fetch(url)
    if not html:
        return set()
    soup = BeautifulSoup(html, "html.parser")
    ids = set()
    # Hadith links are like /{slug}:{hadith_num}
    for a in soup.find_all("a", href=True):
        m = re.search(rf"/{re.escape(sunnah_slug)}:(\d+)", a["href"])
        if m:
            ids.add(int(m.group(1)))
    return ids


def scrape_hadith_english(sunnah_slug, hadith_ref):
    """Scrape English text from sunnah.com hadith page."""
    url = f"https://sunnah.com/{sunnah_slug}:{hadith_ref}"
    html = fetch(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # English text: .english_hadith_full .text_details
    english_el = soup.select_one(".english_hadith_full .text_details")
    english = ""
    if english_el:
        english = english_el.get_text(strip=True)

    # Narrator
    narrator_el = soup.select_one(".hadith_narrated")
    narrator = ""
    if narrator_el:
        narrator = narrator_el.get_text(strip=True)

    return english, narrator


def scrape_book_english(sunnah_slug, book_key, output_path, workers=20):
    """Scrape English for a book from sunnah.com."""
    print(f"\n=== {book_key} (sunnah.com: {sunnah_slug}) ===")

    # Discover chapters
    print("  Discovering chapters...")
    chapters = discover_chapters(sunnah_slug)
    print(f"  Found {len(chapters)} chapters")

    # Discover hadiths
    print("  Discovering hadiths...")
    all_hadiths = set()
    for ch in chapters:
        ids = discover_hadiths(sunnah_slug, ch)
        all_hadiths.update(ids)

    hadith_refs = sorted(all_hadiths)
    print(f"  Found {len(hadith_refs)} hadith references")

    if not hadith_refs:
        print("  No hadiths found")
        return

    # Load existing
    results = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"  Resuming from {len(results)} existing")

    remaining = [h for h in hadith_refs if str(h) not in results]
    print(f"  Remaining: {len(remaining)}")

    if not remaining:
        print("  Already complete!")
        return

    success = 0
    fail = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(scrape_hadith_english, sunnah_slug, h): h for h in remaining
        }
        batch = []

        for future in as_completed(futures):
            h_ref = futures[future]
            try:
                data = future.result()
            except Exception:
                fail += 1
                continue
            if data and data[0]:
                results[str(h_ref)] = {"english": data[0], "narrator": data[1]}
                batch.append(h_ref)
                success += 1
            else:
                fail += 1

            if len(batch) >= 200:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                elapsed = time.time() - start
                rate = (success + fail) / elapsed if elapsed > 0 else 0
                eta = (len(remaining) - success - fail) / rate if rate > 0 else 0
                print(
                    f"  [{success + fail}/{len(remaining)}] ✅{success} ❌{fail} | {rate:.1f}/s | ETA: {eta:.0f}s"
                )
                batch = []

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    print(f"  DONE: {success} success, {fail} failed | {elapsed:.0f}s")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base, "scraped_data")
    os.makedirs(output_dir, exist_ok=True)

    books = SUNNAH_BOOKS
    if len(sys.argv) > 1:
        books = {k: v for k, v in SUNNAH_BOOKS.items() if k in sys.argv[1:]}

    for sunnah_slug, book_key in books.items():
        output_path = os.path.join(output_dir, f"{book_key}_english.json")
        scrape_book_english(sunnah_slug, book_key, output_path)
        time.sleep(2)
