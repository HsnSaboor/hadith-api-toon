#!/usr/bin/env python3
"""Scrape Urdu/English translations from quranohadith.com (same as al-hadees.com).

The hadith text is in hidden <textarea> elements in the server-rendered HTML.
No browser/JS needed - just HTTP requests.
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib.request
import urllib.error

SLUG_MAP = {
    "abudawud": "abu-dawood",
    "aladab-almufrad": "aladab-almufrad",
    "bayhaqi": "bayhaqi",
    "bukhari": "bukhari",
    "bulugh-al-maram": "bulugh-al-maram",
    "fatah-alrabani": "fatah-alrabani",
    "ibnmajah": "ibn-e-maja",
    "lulu-wal-marjan": "lulu-wal-marjan",
    "malik": "imam-malik",
    "mishkat": "mishkat",
    "muajam-tabarani-saghir": "muajam-tabarani-saghir",
    "musannaf-ibn-abi-shaybah": "musannaf-ibn-abi-shaybah",
    "muslim": "muslim",
    "musnad-ahmed": "musnad-ahmed",
    "mustadrak": "mustadrak",
    "nasai": "nisai",
    "sahih-ibn-khuzaymah": "sahih-ibn-khuzaymah",
    "shamail-tirmazi": "shamail-tirmazi",
    "silsila-sahih": "silsila-sahih",
    "sunan-al-daraqutni": "sunan-al-daraqutni",
    "sunan-darmi": "sunan-darmi",
    "tirmidhi": "tirmazi",
}

BASE_URL = "https://quranohadith.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Regex patterns to extract textarea content
TEXTAREA_RE = re.compile(
    r'<textarea[^>]*ID="content-(\w+)-(\d+)"[^>]*>(.*?)</textarea>',
    re.DOTALL | re.IGNORECASE,
)


def fetch_page(url):
    """Fetch a URL and return the HTML text."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_textareas(html):
    """Extract all textarea contents from HTML.

    Returns dict: {lang: {internal_id: text}}
    """
    result = {}
    for match in TEXTAREA_RE.finditer(html):
        lang = match.group(1).lower()
        internal_id = match.group(2)
        text = match.group(3)
        # Decode HTML entities
        text = text.replace("&#13;", "").replace("&#10;", "\n").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        if lang not in result:
            result[lang] = {}
        result[lang][internal_id] = text.strip()
    return result


def get_book_info(al_slug):
    """Get total hadith count from book index page."""
    url = f"{BASE_URL}/hadees-name/{al_slug}/0"
    try:
        html = fetch_page(url)
        m = re.search(r'([\d,]+)\s*Narrations?', html)
        total = int(m.group(1).replace(",", "")) if m else 0

        # Extract chapter links to verify count
        chapter_nums = set()
        for link_match in re.finditer(r'href="[^"]*/0#(\d+)"', html):
            chapter_nums.add(int(link_match.group(1)))
        for link_match in re.finditer(r'href="/hadees-name/' + re.escape(al_slug) + r'/(\d+)"', html):
            chapter_nums.add(int(link_match.group(1)))

        return {
            "total": total,
            "chapters": sorted(chapter_nums) if chapter_nums else [],
            "heading": m.group(0) if m else "",
        }
    except Exception as e:
        return {"total": 0, "chapters": [], "heading": f"error: {e}"}


def scrape_hadith(al_slug, hadith_num):
    """Scrape a single hadith page and return extracted text."""
    url = f"{BASE_URL}/{al_slug}/{hadith_num}"
    try:
        html = fetch_page(url)
        textareas = extract_textareas(html)
        urd = textareas.get("urd", {}).get(str(hadith_num), "")
        eng = textareas.get("eng", {}).get(str(hadith_num), "")
        arb = textareas.get("arb", {}).get(str(hadith_num), "")

        # Some pages use different internal IDs
        if not urd and not eng:
            # Try to find any urd/eng content
            for id_key, text in textareas.get("urd", {}).items():
                if len(text) > 50:
                    urd = text
                    break

        return {
            "hadith_num": hadith_num,
            "url": url,
            "urdu": urd,
            "english": eng,
            "arabic": arb,
            "has_urdu": len(urd) > 50,
            "error": None,
        }
    except urllib.error.HTTPError as e:
        return {
            "hadith_num": hadith_num,
            "url": url,
            "urdu": "",
            "english": "",
            "arabic": "",
            "has_urdu": False,
            "error": f"HTTP {e.code}",
        }
    except Exception as e:
        return {
            "hadith_num": hadith_num,
            "url": url,
            "urdu": "",
            "english": "",
            "arabic": "",
            "has_urdu": False,
            "error": str(e),
        }


def scrape_book(our_slug, al_slug, max_hadith=0, sample=False, workers=5):
    """Scrape all hadith for a book."""
    print(f"\n=== {our_slug} ({al_slug}) ===")

    info = get_book_info(al_slug)
    total_site = info["total"]
    print(f"  Book index: {info['heading']}")
    print(f"  Total narrations: {total_site}")

    if total_site == 0:
        print("  WARNING: Could not determine total, using fallback")
        # Known totals from our local data
        known_totals = {
            "bukhari": 7563,
            "muslim": 7558,
            "tirmazi": 4951,
            "abu-dawood": 5274,
            "nisai": 5851,
            "ibn-e-maja": 4561,
            "silsila-sahih": 3550,
            "musnad-ahmed": 26303,
            "fatah-alrabani": 89,
            "mishkat": 4857,
            "bayhaqi": 20545,
            "shamail-tirmazi": 388,
            "aladab-almufrad": 1329,
            "mustadrak": 8941,
            "sunan-darmi": 3431,
            "imam-malik": 2883,
            "muajam-tabarani-saghir": 18326,
            "musannaf-ibn-abi-shaybah": 38019,
            "sahih-ibn-khuzaymah": 3073,
            "sunan-al-daraqutni": 194,
            "bulugh-al-maram": 1691,
            "lulu-wal-marjan": 1907,
        }
        total_site = known_totals.get(al_slug, 100)
        # Check index page for actual count from heading
        print(f"  Using fallback total: {total_site}")

    if sample:
        total_site = min(total_site, 20)

    if max_hadith and total_site > max_hadith:
        total_site = max_hadith

    print(f"  Scraping {total_site} hadith...")

    results = []
    found_count = 0
    empty_count = 0

    # Use thread pool for parallel scraping
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scrape_hadith, al_slug, num): num
            for num in range(1, total_site + 1)
        }

        for future in as_completed(futures):
            num = futures[future]
            try:
                result = future.result()
                results.append(result)
                if result["has_urdu"]:
                    found_count += 1
                else:
                    empty_count += 1
            except Exception as e:
                results.append({
                    "hadith_num": num,
                    "url": f"{BASE_URL}/{al_slug}/{num}",
                    "urdu": "", "english": "", "arabic": "",
                    "has_urdu": False, "error": str(e),
                })
                empty_count += 1

            if (found_count + empty_count) % 50 == 0 or (found_count + empty_count) == 1:
                done = found_count + empty_count
                print(f"  Progress: {done}/{total_site} (found: {found_count}, empty: {empty_count})")

    # Sort by hadith number
    results.sort(key=lambda r: r["hadith_num"])

    print(f"  Done: {total_site} checked, {found_count} with Urdu, {empty_count} empty/error")

    return {
        "our_slug": our_slug,
        "al_slug": al_slug,
        "total_site": total_site,
        "info": info,
        "results": results,
        "found": found_count,
        "empty": empty_count,
    }


def save_results(data, out_dir):
    """Save scrape results to JSON + generate .toon file."""
    os.makedirs(out_dir, exist_ok=True)

    # Save raw JSON
    json_path = f"{out_dir}/scrape_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Generate Urdu .toon file
    ur_results = [
        r for r in data["results"]
        if r["has_urdu"] and r["urdu"]
    ]
    if ur_results:
        toon_path = f"{out_dir}/urdu.toon"
        with open(toon_path, "w", encoding="utf-8") as f:
            f.write(f"hadiths[{len(ur_results)}]{{hadithnumber,text}}:\n")
            for r in ur_results:
                text = r["urdu"].replace("\n", "\\n").replace('"', '""')
                f.write(f'"{r["hadith_num"]}","{text}"\n')
        print(f"  Urdu .toon: {len(ur_results)} hadith -> {toon_path}")

    # Generate English .toon file
    en_results = [
        r for r in data["results"]
        if r["english"] and len(r["english"]) > 50
    ]
    if en_results:
        toon_path = f"{out_dir}/english.toon"
        with open(toon_path, "w", encoding="utf-8") as f:
            f.write(f"hadiths[{len(en_results)}]{{hadithnumber,text}}:\n")
            for r in en_results:
                text = r["english"].replace("\n", "\\n").replace('"', '""')
                f.write(f'"{r["hadith_num"]}","{text}"\n')
        print(f"  English .toon: {len(en_results)} hadith -> {toon_path}")

    return json_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Urdu translations from quranohadith.com")
    parser.add_argument("books", nargs="*", help="Books to scrape (default: all)")
    parser.add_argument("--sample", action="store_true", help="Sample mode: only 20 per book")
    parser.add_argument("--max", type=int, default=0, help="Max hadith per book")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers")
    parser.add_argument("--out", default="scraped_data", help="Output directory")
    args = parser.parse_args()

    books_to_scrape = args.books if args.books else list(SLUG_MAP.keys())

    for our_slug in books_to_scrape:
        if our_slug not in SLUG_MAP:
            print(f"Unknown slug: {our_slug}")
            continue

        al_slug = SLUG_MAP[our_slug]
        data = scrape_book(our_slug, al_slug, max_hadith=args.max, sample=args.sample, workers=args.workers)
        out_dir = f"{args.out}/{our_slug}"
        json_path = save_results(data, out_dir)
        print(f"  Saved -> {json_path}")


if __name__ == "__main__":
    main()
