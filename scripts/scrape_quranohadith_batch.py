"""
Batch scraper for quranohadith.com - scrapes all 7 existing books + 15 new books.

Extracts: Arabic, Urdu, international_number, chapter_title_arabic
(English and grades come from HuggingFace dataset)
"""

import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://quranohadith.com"
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

NEW_BOOK_SLUGS = {
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
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        return ""


def scrape_hadith(book_slug: str, hadith_id: int) -> dict:
    url = f"{BASE_URL}/{book_slug}/{hadith_id}"
    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Arabic: h4.font-arabic2.text-center.mb-4
    arabic_el = soup.select_one("h4.font-arabic2.text-center.mb-4")
    arabic = arabic_el.get_text(strip=True) if arabic_el else ""

    # Urdu: .card-body h4.font-urdu (full text from accordion)
    urdu_el = soup.select_one(".card-body h4.font-urdu")
    urdu = urdu_el.get_text(strip=True) if urdu_el else ""

    # International number
    international_number = None
    for el in soup.find_all(string=lambda t: t and "International" in t):
        m = re.search(r"International:\s*(\d+)", str(el))
        if m:
            international_number = int(m.group(1))
            break

    # Chapter title (Arabic)
    chapter_title_arabic = ""
    alert_section = soup.select_one("section.alert-secondary")
    if alert_section:
        for h2 in alert_section.find_all("h2"):
            text = h2.get_text(strip=True)
            if text and ("کتاب" in text or "باب" in text):
                chapter_title_arabic = text
                break

    return {
        "arabic": arabic,
        "urdu": urdu,
        "international_number": international_number,
        "chapter_title_arabic": chapter_title_arabic,
    }


def scrape_batch(
    book_slug: str, hadith_ids: list, output_path: str, max_workers: int = 8
):
    """Scrape a batch of hadiths with concurrency."""
    print(f"\n=== {book_slug}: {len(hadith_ids)} hadiths ===")

    # Load existing results to resume
    existing = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"  Resuming from {len(existing)} existing entries")

    remaining = [h for h in hadith_ids if str(h) not in existing]
    print(f"  Remaining: {len(remaining)}")

    if not remaining:
        print(f"  Already complete!")
        return existing

    results = existing
    completed = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {
            executor.submit(scrape_hadith, book_slug, h_id): h_id for h_id in remaining
        }

        batch_save = []
        for future in as_completed(future_to_id):
            h_id = future_to_id[future]
            completed += 1
            try:
                result = future.result()
                if result:
                    results[str(h_id)] = result
                    batch_save.append(h_id)
                else:
                    errors += 1
            except Exception as e:
                errors += 1

            # Save every 100 hadiths
            if len(batch_save) >= 100:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                batch_save = []

            if completed % 500 == 0 or completed == len(remaining):
                print(f"  Progress: {completed}/{len(remaining)} (errors: {errors})")
                time.sleep(1)

    # Final save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  Done: {len(results)} hadiths saved")
    return results


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "scraped_data")
    os.makedirs(output_dir, exist_ok=True)

    # Get hadith IDs from existing section files
    editions_dir = os.path.join(base_dir, "editions")

    books_to_scrape = BOOK_SLUGS.copy()
    if len(sys.argv) > 1:
        # Only scrape specified books
        books_to_scrape = {k: v for k, v in BOOK_SLUGS.items() if k in sys.argv[1:]}

    for book_key, slug in books_to_scrape.items():
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
        scrape_batch(slug, sorted(hadith_numbers), output_path, max_workers=8)
        time.sleep(3)  # Pause between books
