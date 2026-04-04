"""
Ultra-fast async scraper for quranohadith.com using aiohttp + asyncio.
Scrapes Arabic, Urdu, international_number, chapter_title from individual hadith pages.
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup


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

CONCURRENCY = 50  # concurrent requests
BATCH_SIZE = 500  # save every N hadiths


async def fetch_hadith(
    session: aiohttp.ClientSession,
    book_slug: str,
    hadith_id: int,
    semaphore: asyncio.Semaphore,
) -> tuple:
    """Fetch and parse a single hadith page."""
    async with semaphore:
        url = f"{BASE_URL}/{book_slug}/{hadith_id}"
        try:
            async with session.get(
                url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return hadith_id, None
                html = await resp.text()
        except Exception:
            return hadith_id, None

    soup = BeautifulSoup(html, "html.parser")

    # Arabic: h4.font-arabic2.text-center.mb-4
    arabic_el = soup.select_one("h4.font-arabic2.text-center.mb-4")
    arabic = arabic_el.get_text(strip=True) if arabic_el else ""

    # Urdu: .card-body h4.font-urdu
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
    chapter_title_arabic = ""
    alert_section = soup.select_one("section.alert-secondary")
    if alert_section:
        for h2 in alert_section.find_all("h2"):
            text = h2.get_text(strip=True)
            if text and ("کتاب" in text or "باب" in text):
                chapter_title_arabic = text
                break

    return hadith_id, {
        "arabic": arabic,
        "urdu": urdu,
        "international_number": international_number,
        "chapter_title_arabic": chapter_title_arabic,
    }


async def scrape_book(book_slug: str, hadith_ids: list, output_path: str):
    """Scrape all hadiths for a book with high concurrency."""
    print(f"\n=== {book_slug}: {len(hadith_ids)} hadiths ===")

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

    semaphore = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(
        limit=CONCURRENCY, ttl_dns_cache=300, force_close=False
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_hadith(session, book_slug, h_id, semaphore) for h_id in remaining
        ]

        completed = 0
        for future in asyncio.as_completed(tasks):
            h_id, data = await future
            if data:
                results[str(h_id)] = data
            completed += 1

            if completed % BATCH_SIZE == 0:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"  Progress: {completed}/{len(remaining)}")

    # Final save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  Done: {len(results)} hadiths saved to {output_path}")


def get_hadith_ids(editions_dir: str, book_key: str) -> list:
    """Extract hadith numbers from existing section files."""
    edition = None
    for d in os.listdir(editions_dir):
        if d.endswith(f"-{book_key}"):
            edition = d
            break
    if not edition:
        return []

    sec_dir = os.path.join(editions_dir, edition, "sections")
    if not os.path.isdir(sec_dir):
        return []

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

    return sorted(hadith_numbers)


async def main(books_to_scrape: list = None):
    base_dir = Path(__file__).parent.parent
    editions_dir = base_dir / "editions"
    output_dir = base_dir / "scraped_data"
    output_dir.mkdir(exist_ok=True)

    slugs = BOOK_SLUGS
    if books_to_scrape:
        slugs = {k: v for k, v in BOOK_SLUGS.items() if k in books_to_scrape}

    for book_key, slug in slugs.items():
        hadith_ids = get_hadith_ids(str(editions_dir), book_key)
        if not hadith_ids:
            print(f"  {book_key}: no hadiths found, skipping")
            continue

        output_path = output_dir / f"{book_key}_scraped.json"
        await scrape_book(slug, hadith_ids, str(output_path))
        await asyncio.sleep(2)  # brief pause between books


if __name__ == "__main__":
    books = sys.argv[1:] if len(sys.argv) > 1 else None
    asyncio.run(main(books))
