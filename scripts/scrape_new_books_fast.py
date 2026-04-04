"""
Fast scraper for new books from al-hadees.com.
Parallel chapter discovery + parallel hadith scraping.
"""

import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://al-hadees.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

NEW_BOOKS = {
    "musnad-ahmed": "musnad-ahmed",
    "silsila-sahih": "silsila-sahih",
    "mishkat": "mishkat",
    "fatah-alrabani": "fatah-alrabani",
    "bayhaqi": "bayhaqi",
    "shamail-tirmazi": "shamail-tirmazi",
    "aladab-almufrad": "aladab-almufrad",
    "mustadrak": "mustadrak",
    "sunan-darmi": "sunan-darmi",
    "muajam-tabarani-saghir": "muajam-tabarani-saghir",
    "musannaf-ibn-abi-shaybah": "musannaf-ibn-abi-shaybah",
    "sahih-ibn-khuzaymah": "sahih-ibn-khuzaymah",
    "sunan-al-daraqutni": "sunan-al-daraqutni",
    "bulugh-al-maram": "bulugh-al-maram",
    "lulu-wal-marjan": "lulu-wal-marjan",
}


def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except:
        return ""


def discover_chapters(book_slug):
    """Get all chapter IDs from the book landing page."""
    html = fetch(f"{BASE_URL}/hadees-name/{book_slug}/0")
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    chapters = set()
    for a in soup.find_all("a", href=True):
        m = re.search(rf"/hadees-subjects/{re.escape(book_slug)}/(\d+)", a["href"])
        if m:
            chapters.add(int(m.group(1)))
    return sorted(chapters)


def discover_hadiths_in_chapter(book_slug, chapter_id):
    """Get all hadith IDs from a single chapter page."""
    url = f"{BASE_URL}/hadees/{book_slug}/{chapter_id}/0"
    html = fetch(url)
    if not html:
        return set()
    soup = BeautifulSoup(html, "html.parser")
    ids = set()
    for a in soup.find_all("a", href=True):
        m = re.search(rf"/{re.escape(book_slug)}/(\d+)$", a["href"])
        if m:
            ids.add(int(m.group(1)))
    return ids


def scrape_hadith(book_slug, hadith_id):
    url = f"{BASE_URL}/{book_slug}/{hadith_id}"
    html = fetch(url)
    if not html:
        return hadith_id, None

    soup = BeautifulSoup(html, "html.parser")
    arabic_el = soup.select_one("h4.font-arabic2.text-center.mb-4")
    arabic = arabic_el.get_text(strip=True) if arabic_el else ""
    urdu_el = soup.select_one(".card-body h4.font-urdu")
    urdu = urdu_el.get_text(strip=True) if urdu_el else ""

    international_number = None
    for el in soup.find_all(string=lambda t: t and "International" in t):
        m = re.search(r"International:\s*(\d+)", str(el))
        if m:
            international_number = int(m.group(1))
            break

    chapter_title = ""
    alert = soup.select_one("section.alert-secondary")
    if alert:
        h2 = alert.select_one("h2.text-center.font-arabic2")
        if h2:
            chapter_title = h2.get_text(strip=True)

    return hadith_id, {
        "arabic": arabic,
        "urdu": urdu,
        "international_number": international_number,
        "chapter_title_arabic": chapter_title,
    }


def scrape_book(book_slug, output_path, discovery_workers=20, scrape_workers=30):
    print(f"\n{'=' * 80}")
    print(f"  {book_slug.upper()}")
    print(f"{'=' * 80}")

    # Step 1: Discover chapters
    print("  Discovering chapters...")
    chapters = discover_chapters(book_slug)
    print(f"  Found {len(chapters)} chapters: {chapters}")

    # Step 2: Parallel discover hadith IDs
    print("  Discovering hadith IDs (parallel)...")
    all_hadith_ids = set()
    with ThreadPoolExecutor(max_workers=discovery_workers) as ex:
        futures = {
            ex.submit(discover_hadiths_in_chapter, book_slug, ch): ch for ch in chapters
        }
        for i, future in enumerate(as_completed(futures)):
            ch = futures[future]
            ids = future.result()
            all_hadith_ids.update(ids)
            if (i + 1) % 5 == 0 or i + 1 == len(chapters):
                print(
                    f"  Chapters scanned: {i + 1}/{len(chapters)}, hadiths found: {len(all_hadith_ids)}"
                )

    hadith_ids = sorted(all_hadith_ids)
    print(f"  Total unique hadith IDs: {len(hadith_ids)}")

    if not hadith_ids:
        print("  No hadiths found, skipping")
        return

    # Step 3: Load existing
    results = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"  Resuming from {len(results)} existing")

    remaining = [h for h in hadith_ids if str(h) not in results]
    print(f"  Remaining: {len(remaining)}")

    if not remaining:
        print(f"  Already complete!")
        return

    # Step 4: Parallel scrape
    success = 0
    fail = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=scrape_workers) as ex:
        futures = {ex.submit(scrape_hadith, book_slug, h): h for h in remaining}
        batch = []

        for future in as_completed(futures):
            h_id, data = future.result()
            if data:
                results[str(h_id)] = data
                batch.append(h_id)
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

    books = NEW_BOOKS
    if len(sys.argv) > 1:
        books = {k: v for k, v in NEW_BOOKS.items() if k in sys.argv[1:]}

    for book_key, slug in books.items():
        output_path = os.path.join(output_dir, f"{book_key}_scraped.json")
        scrape_book(slug, output_path)
        time.sleep(2)
