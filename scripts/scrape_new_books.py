"""
Scrape new books from al-hadees.com that don't exist in hadith-api.

Discovers hadith IDs by crawling chapter listing pages, then scrapes each hadith.
Books: musnad-ahmed, silsila-sahih, mishkat, fatah-alrabani, bayhaqi,
       shamail-tirmazi, aladab-almufrad, mustadrak, sunan-darmi,
       muajam-tabarani-saghir, musannaf-ibn-abi-shaybah, sahih-ibn-khuzaymah,
       sunan-al-daraqutni, bulugh-al-maram, lulu-wal-marjan
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


def fetch_page(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        return ""


def discover_hadith_ids(book_slug: str) -> list:
    """Crawl chapter pages to discover all hadith IDs."""
    hadith_ids = set()
    chapter_id = 1
    max_empty = 5
    empty_count = 0

    while empty_count < max_empty:
        url = f"{BASE_URL}/hadees/{book_slug}/{chapter_id}/0"
        html = fetch_page(url)
        if not html:
            empty_count += 1
            chapter_id += 1
            continue

        soup = BeautifulSoup(html, "html.parser")
        found = False

        # Find hadith links: /{book}/{hadith-id}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = re.search(rf"/{re.escape(book_slug)}/(\d+)$", href)
            if m:
                hadith_ids.add(int(m.group(1)))
                found = True

        if not found:
            empty_count += 1
        else:
            empty_count = 0

        chapter_id += 1
        if chapter_id % 10 == 0:
            print(
                f"  Scanned {chapter_id} chapter pages, found {len(hadith_ids)} hadiths so far..."
            )

    return sorted(hadith_ids)


def scrape_hadith(book_slug: str, hadith_id: int) -> dict:
    """Scrape a single hadith page."""
    url = f"{BASE_URL}/{book_slug}/{hadith_id}"
    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Arabic
    arabic_el = soup.select_one("h4.font-arabic2.text-center.mb-4")
    arabic = arabic_el.get_text(strip=True) if arabic_el else ""

    # Urdu
    urdu_el = soup.select_one(".card-body h4.font-urdu")
    urdu = urdu_el.get_text(strip=True) if urdu_el else ""

    # International number
    international_number = None
    for el in soup.find_all(string=lambda t: t and "International" in t):
        m = re.search(r"International:\s*(\d+)", str(el))
        if m:
            international_number = int(m.group(1))
            break

    # Chapter title
    chapter_title = ""
    alert = soup.select_one("section.alert-secondary")
    if alert:
        for h2 in alert.find_all("h2"):
            text = h2.get_text(strip=True)
            if "کتاب" in text or "باب" in text:
                chapter_title = text
                break

    return {
        "arabic": arabic,
        "urdu": urdu,
        "international_number": international_number,
        "chapter_title_arabic": chapter_title,
    }


def scrape_book(book_slug: str, output_path: str, workers: int = 30):
    """Discover hadith IDs and scrape a new book."""
    print(f"\n{'=' * 80}")
    print(f"  {book_slug.upper()}")
    print(f"{'=' * 80}")

    # Discover hadith IDs
    print("  Discovering hadith IDs...")
    hadith_ids = discover_hadith_ids(book_slug)
    print(f"  Found {len(hadith_ids)} hadiths")

    if not hadith_ids:
        print("  No hadiths found, skipping")
        return

    # Load existing
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

    success = 0
    fail = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scrape_hadith, book_slug, h_id): h_id for h_id in remaining
        }
        batch_save = []

        for future in as_completed(futures):
            h_id, data = future.result()
            if data:
                results[str(h_id)] = data
                batch_save.append(h_id)
                success += 1
            else:
                fail += 1

            if len(batch_save) >= 200:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                elapsed = time.time() - start_time
                rate = (success + fail) / elapsed if elapsed > 0 else 0
                eta = (len(remaining) - success - fail) / rate if rate > 0 else 0
                print(
                    f"  [{success + fail}/{len(remaining)}] ✅{success} ❌{fail} | {rate:.1f}/s | ETA: {eta:.0f}s"
                )
                batch_save = []

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"  DONE: {success} success, {fail} failed | {elapsed:.0f}s total")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base, "scraped_data")
    os.makedirs(output_dir, exist_ok=True)

    books_to_scrape = NEW_BOOKS
    if len(sys.argv) > 1:
        books_to_scrape = {k: v for k, v in NEW_BOOKS.items() if k in sys.argv[1:]}

    for book_key, slug in books_to_scrape.items():
        output_path = os.path.join(output_dir, f"{book_key}_scraped.json")
        scrape_book(slug, output_path, workers=30)
        time.sleep(2)
