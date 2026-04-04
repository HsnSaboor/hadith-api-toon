"""
Fix chapter_title_arabic in existing scraped data by re-fetching one page per chapter.
"""

import json
import os
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://al-hadees.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except:
        return ""


def get_chapter_title(book_slug, hadith_id):
    html = fetch(f"{BASE_URL}/{book_slug}/{hadith_id}")
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    alert = soup.select_one("section.alert-secondary")
    if alert:
        # Try all h2 elements and pick the first non-empty one
        for h2 in alert.select("h2.text-center.font-arabic2"):
            text = h2.get_text(strip=True)
            if text:
                return text
    return ""


def fix_book(book_key, book_slug):
    path = f"scraped_data/{book_key}_scraped.json"
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Find unique chapter titles by sampling one hadith per unique chapter_title
    chapters_found = set()
    hadiths_to_fetch = []

    for h_id_str in sorted(data.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        h = data[h_id_str]
        current_title = h.get("chapter_title_arabic", "")
        if current_title:
            chapters_found.add(current_title)
        else:
            hadiths_to_fetch.append(h_id_str)

    if not hadiths_to_fetch:
        print(f"  {book_key}: all chapters already filled")
        return

    print(f"  {book_key}: {len(hadiths_to_fetch)} hadiths need chapter titles")

    # Fetch in parallel
    fixed = 0
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {
            ex.submit(get_chapter_title, book_slug, int(h)): h for h in hadiths_to_fetch
        }
        for future in as_completed(futures):
            h_id_str = futures[future]
            title = future.result()
            if title:
                data[h_id_str]["chapter_title_arabic"] = title
                fixed += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    unique_chapters = set(h.get("chapter_title_arabic", "") for h in data.values())
    print(
        f"  {book_key}: fixed {fixed} entries, {len(unique_chapters)} unique chapters: {sorted(unique_chapters)}"
    )


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

for book_key, slug in NEW_BOOKS.items():
    fix_book(book_key, slug)
