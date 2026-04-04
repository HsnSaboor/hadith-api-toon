"""
Fast parallel scraper using ThreadPoolExecutor (requests library).
Tests scraping and shows live progress.

Usage: python scripts/test_scrape.py bukhari 5
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

BOOK_SLUGS = {
    "bukhari": "bukhari",
    "muslim": "muslim",
    "abudawud": "abu-dawood",
    "ibnmajah": "ibn-e-maja",
    "malik": "imam-malik",
    "nasai": "nisai",
    "tirmidhi": "tirmazi",
}


def scrape_hadith(book_slug: str, hadith_id: int) -> tuple:
    """Scrape a single hadith page. Returns (hadith_id, data_or_None)."""
    url = f"{BASE_URL}/{book_slug}/{hadith_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return hadith_id, None, resp.status_code
        html = resp.text
    except Exception as e:
        return hadith_id, None, str(e)

    soup = BeautifulSoup(html, "html.parser")

    # Arabic
    arabic_el = soup.select_one("h4.font-arabic2.text-center.mb-4")
    arabic = arabic_el.get_text(strip=True)[:100] if arabic_el else ""

    # Urdu
    urdu_el = soup.select_one(".card-body h4.font-urdu")
    urdu = urdu_el.get_text(strip=True)[:100] if urdu_el else ""

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
                chapter_title = text[:80]
                break

    return (
        hadith_id,
        {
            "arabic": arabic,
            "urdu": urdu,
            "international_number": international_number,
            "chapter_title": chapter_title,
        },
        200,
    )


def test_scrape(book_key: str, count: int, workers: int = 20):
    slug = BOOK_SLUGS.get(book_key)
    if not slug:
        print(f"Unknown book: {book_key}. Available: {list(BOOK_SLUGS.keys())}")
        return

    print(
        f"Scraping {count} hadiths from {book_key} ({slug}) with {workers} workers..."
    )
    print("-" * 100)

    success = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scrape_hadith, slug, i + 1): i + 1 for i in range(count)
        }

        for future in as_completed(futures):
            h_id, data, status = future.result()
            if data:
                success += 1
                print(
                    f"  ✅ #{h_id}: arabic={data['arabic'][:50]}... | urdu={'yes' if data['urdu'] else 'no'} | intl={data['international_number']} | chapter={data['chapter_title'][:40]}"
                )
            else:
                fail += 1
                print(f"  ❌ #{h_id}: {status}")

    print("-" * 100)
    print(f"Done: {success} success, {fail} failed out of {count}")


def scrape_full_book(
    book_key: str, hadith_ids: list, output_path: str, workers: int = 30
):
    """Scrape a full book with live progress."""
    slug = BOOK_SLUGS.get(book_key)
    if not slug:
        print(f"Unknown book: {book_key}")
        return

    print(f"\n{'=' * 80}")
    print(f"  {book_key.upper()}: {len(hadith_ids)} hadiths | {workers} workers")
    print(f"{'=' * 80}")

    # Load existing
    results = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"  Resuming from {len(results)} existing entries")

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
            executor.submit(scrape_hadith, slug, h_id): h_id for h_id in remaining
        }
        batch_save = []

        for future in as_completed(futures):
            h_id, data, status = future.result()
            if data:
                results[str(h_id)] = data
                batch_save.append(h_id)
                success += 1
            else:
                fail += 1

            # Save every 200
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

    # Final save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"  DONE: {success} success, {fail} failed | {elapsed:.0f}s total")


def scrape_all_books(editions_dir: str, output_dir: str, workers: int = 30):
    """Scrape all 7 books."""
    os.makedirs(output_dir, exist_ok=True)

    for book_key, slug in BOOK_SLUGS.items():
        # Find edition
        edition = None
        for d in os.listdir(editions_dir):
            if d.endswith(f"-{book_key}"):
                edition = d
                break
        if not edition:
            print(f"  {book_key}: no edition found, skipping")
            continue

        sec_dir = os.path.join(editions_dir, edition, "sections")
        if not os.path.isdir(sec_dir):
            print(f"  {book_key}: no sections dir, skipping")
            continue

        # Get hadith numbers
        hadith_numbers = set()
        for fname in os.listdir(sec_dir):
            if not fname.endswith(".toon"):
                continue
            with open(os.path.join(sec_dir, fname), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if (
                        line.startswith("hadiths[")
                        or line.startswith("metadata")
                        or line.startswith("  ")
                    ):
                        continue
                    if not line:
                        continue
                    parts = line.split(",", 1)
                    if parts[0].isdigit():
                        hadith_numbers.add(int(parts[0]))

        output_path = os.path.join(output_dir, f"{book_key}_scraped.json")
        scrape_full_book(book_key, sorted(hadith_numbers), output_path, workers)
        time.sleep(2)


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) == 1:
        # Scrape all 7 books
        scrape_all_books(
            os.path.join(base, "editions"),
            os.path.join(base, "scraped_data"),
            workers=30,
        )
    elif len(sys.argv) == 2:
        # Test: scrape first 5 hadiths
        test_scrape(sys.argv[1], 5)
    else:
        # Test with custom count
        test_scrape(sys.argv[1], int(sys.argv[2]))
