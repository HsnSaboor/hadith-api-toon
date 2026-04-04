"""
Fast scraper for quranohadith.com - fetches individual hadith pages directly.

URL: /{book_slug}/{hadith_id}
Returns: Arabic, Urdu, English, grade, international_number, reference, narrator_chain, chapter_intro
"""

import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://quranohadith.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Book slug mapping: our book key -> quranohadith.com slug
BOOK_SLUGS = {
    "bukhari": "bukhari",
    "muslim": "muslim",
    "abudawud": "abu-dawood",
    "ibnmajah": "ibn-e-maja",
    "malik": "imam-malik",
    "nasai": "nisai",
    "tirmidhi": "tirmazi",
}

# New books
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
    """Scrape a single hadith page."""
    url = f"{BASE_URL}/{book_slug}/{hadith_id}"
    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Arabic text (h4.font-arabic2, not h3)
    arabic_el = soup.select_one("h4.font-arabic2.text-center.mb-4")
    arabic = ""
    if arabic_el:
        arabic = arabic_el.get_text(strip=True)

    # Urdu translation (full text from accordion card-body, not button)
    urdu_el = soup.select_one(".card-body h4.font-urdu")
    urdu = ""
    if urdu_el:
        urdu = urdu_el.get_text(strip=True)

    # English translation (not available on quranohadith.com individual pages)
    english = ""

    # Grade/Status (not on individual pages, only on listing pages)
    grade = ""

    # Hadith number
    hadith_number = None
    for el in soup.find_all(string=lambda t: t and "Hadees Number" in t):
        m = re.search(r"Hadees Number:\s*(\d+)", str(el))
        if m:
            hadith_number = int(m.group(1))
            break

    # International number
    international_number = None
    for el in soup.find_all(string=lambda t: t and "International" in t):
        m = re.search(r"International:\s*(\d+)", str(el))
        if m:
            international_number = int(m.group(1))
            break

    # Reference
    reference = ""
    for el in soup.find_all(string=lambda t: t and "Status Reference" in t):
        parent = el.find_next_sibling() or (
            el.parent.find_next_sibling() if el.parent else None
        )
        if parent:
            reference = parent.get_text(strip=True)
            break

    # Chapter info (from alert-secondary section)
    chapter_title_arabic = ""
    chapter_title_english = ""
    chapter_intro = ""

    alert_section = soup.select_one("section.alert-secondary")
    if alert_section:
        h2_elements = alert_section.find_all("h2")
        for h2 in h2_elements:
            text = h2.get_text(strip=True)
            if text and any("\u0600" <= c <= "\u06ff" for c in text):
                if "کتاب" in text or "باب" in text:
                    chapter_title_arabic = text
                elif not chapter_title_arabic:
                    chapter_title_arabic = text

        h5_el = alert_section.select_one("h5.text-center.text-subject")
        if h5_el:
            chapter_title_english = h5_el.get_text(strip=True)

        h4_el = alert_section.select_one("h4.text-center.font-arabic2")
        if h4_el:
            chapter_intro = h4_el.get_text(strip=True)

    return {
        "hadith_number": hadith_number or hadith_id,
        "arabic": arabic,
        "urdu": urdu,
        "english": english,
        "grade": grade,
        "international_number": international_number,
        "reference": reference,
        "chapter_title_arabic": chapter_title_arabic,
        "chapter_title_english": chapter_title_english,
        "chapter_intro": chapter_intro,
    }


def scrape_book(
    book_slug: str, hadith_ids: list, output_dir: str, max_workers: int = 5
):
    """Scrape a book using ThreadPoolExecutor for speed."""
    print(f"\n=== Scraping book: {book_slug} ({len(hadith_ids)} hadiths) ===")

    results = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {
            executor.submit(scrape_hadith, book_slug, h_id): h_id for h_id in hadith_ids
        }

        for future in as_completed(future_to_id):
            h_id = future_to_id[future]
            completed += 1
            try:
                result = future.result()
                if result:
                    results[h_id] = result
            except Exception as e:
                print(f"  Hadith {h_id}: ERROR - {e}")

            if completed % 100 == 0:
                print(f"  Progress: {completed}/{len(hadith_ids)}")
                time.sleep(1)  # Rate limit

    # Save output
    output_path = os.path.join(output_dir, f"{book_slug}_scraped.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(results)} hadiths to {output_path}")
    return results


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "scraped_data")
    os.makedirs(output_dir, exist_ok=True)

    if len(sys.argv) > 1:
        book_slug = sys.argv[1]
        max_hadiths = int(sys.argv[2]) if len(sys.argv) > 2 else None

        # Test: scrape first N hadiths
        test_ids = list(range(1, (max_hadiths or 5) + 1))
        scrape_book(book_slug, test_ids, output_dir, max_workers=3)
    else:
        print("Usage: python scrape_quranohadith.py <book_slug> [max_hadiths]")
        print(
            f"Available books: {list(BOOK_SLUGS.keys()) + list(NEW_BOOK_SLUGS.keys())}"
        )
