"""
Test scraper - scrapes N hadiths with live progress output.
Usage: source .venv/bin/activate && python scripts/test_scrape.py bukhari 5
"""

import asyncio
import json
import os
import re
import sys
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


async def fetch_hadith(session, book_slug, hadith_id, semaphore):
    async with semaphore:
        url = f"{BASE_URL}/{book_slug}/{hadith_id}"
        try:
            async with session.get(
                url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return hadith_id, None, resp.status
                html = await resp.text()
        except Exception as e:
            return hadith_id, None, str(e)

    soup = BeautifulSoup(html, "html.parser")

    arabic_el = soup.select_one("h4.font-arabic2.text-center.mb-4")
    arabic = arabic_el.get_text(strip=True)[:100] if arabic_el else ""

    urdu_el = soup.select_one(".card-body h4.font-urdu")
    urdu = urdu_el.get_text(strip=True)[:100] if urdu_el else ""

    international_number = None
    for el in soup.find_all(string=lambda t: t and "International" in t):
        m = re.search(r"International:\s*(\d+)", str(el))
        if m:
            international_number = int(m.group(1))
            break

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


async def test_scrape(book_key, count):
    slug = BOOK_SLUGS.get(book_key)
    if not slug:
        print(f"Unknown book: {book_key}. Available: {list(BOOK_SLUGS.keys())}")
        return

    print(f"Scraping {count} hadiths from {book_key} ({slug})...")
    print(f"Concurrency: 20")
    print("-" * 80)

    semaphore = asyncio.Semaphore(20)
    connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_hadith(session, slug, i + 1, semaphore) for i in range(count)]
        success = 0
        fail = 0

        for future in asyncio.as_completed(tasks):
            h_id, data, status = await future
            if data:
                success += 1
                print(
                    f"  ✅ #{h_id}: arabic={data['arabic'][:50]}... | urdu={'yes' if data['urdu'] else 'no'} | intl={data['international_number']} | chapter={data['chapter_title'][:40]}"
                )
            else:
                fail += 1
                print(f"  ❌ #{h_id}: status={status}")

        print("-" * 80)
        print(f"Done: {success} success, {fail} failed out of {count}")


if __name__ == "__main__":
    book = sys.argv[1] if len(sys.argv) > 1 else "bukhari"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    asyncio.run(test_scrape(book, count))
