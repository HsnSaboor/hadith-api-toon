#!/usr/bin/env python3
"""
Fetch missing hadith translations from sunnah.com for hadithnumbers
that exist in Arabic sections but not in hadith-new source.

Missing ranges:
  abudawud: 5275-5276
  ibnmajah: 4342-4345
  malik:    1859-1985
  nasai:    5759-5768
  tirmidhi: 3957-4053
"""

import json
import os
import re
import time
import urllib.request
import urllib.error

EDITIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "editions")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# sunnah.com book slugs
BOOK_SLUGS = {
    "abudawud": "abudawud",
    "ibnmajah": "ibnmajah",
    "malik":    "malik",
    "nasai":    "nasai",
    "tirmidhi": "tirmidhi",
}

# Missing hadithnumber ranges per book
MISSING = {
    "abudawud": list(range(5275, 5277)),
    "ibnmajah": list(range(4342, 4346)),
    "malik":    list(range(1859, 1986)),
    "nasai":    list(range(5759, 5769)),
    "tirmidhi": list(range(3957, 4054)),
}


def fetch_url(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} for {url}")
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(2 * (attempt + 1))
    return None


def extract_hadith_from_page(html, hn):
    """Extract English hadith text from sunnah.com page HTML."""
    if not html:
        return None

    # sunnah.com embeds hadith text in specific HTML patterns
    # Look for the English text in .english-hadith-text or similar
    # Pattern 1: data in script tags
    patterns = [
        # English hadith text in divs
        r'<div[^>]*class="[^"]*english-hadith-text[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*hadith-text[^"]*"[^>]*>(.*?)</div>',
        r'<span[^>]*class="[^"]*hadith_eng[^"]*"[^>]*>(.*?)</span>',
        # Generic text block near hadith number
        r'class="[^"]*hadith[^"]*"[^>]*>.*?class="[^"]*english[^"]*"[^>]*>(.*?)</div>',
    ]

    for pat in patterns:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            text = m.group(1)
            # Clean HTML tags
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 20:
                return text

    return None


def get_hadith_text(book_slug, hn):
    """Fetch a single hadith from sunnah.com webpage."""
    # sunnah.com URL pattern: /book_slug/hadith_number
    url = f"https://sunnah.com/{book_slug}/{hn}"
    html = fetch_url(url)
    if not html:
        return None

    text = extract_hadith_from_page(html, hn)
    return text


def try_api_endpoint(book_slug, hn):
    """Try the sunnah.com internal API."""
    # Try various API patterns sunnah.com uses internally
    urls = [
        f"https://sunnah.com/api/hadiths/{book_slug}/{hn}",
        f"https://sunnah.com/ajax/hadith/{book_slug}/{hn}",
    ]
    for url in urls:
        html = fetch_url(url)
        if html:
            try:
                d = json.loads(html)
                # Look for English text
                for key in ["text", "english", "body", "hadith"]:
                    if key in d and d[key]:
                        return str(d[key])
                # Nested
                if "hadiths" in d:
                    for h in d["hadiths"]:
                        if h.get("lang") == "en" and h.get("body"):
                            return h["body"]
            except Exception:
                pass
    return None


def find_hadith_section(book, hn):
    """Find which Arabic section file contains this hadithnumber."""
    sec_dir = os.path.join(EDITIONS, book, "sections")
    for fname in os.listdir(sec_dir):
        if not fname.endswith(".toon") or fname == "0.toon":
            continue
        sec_id = int(fname.replace(".toon", ""))
        with open(os.path.join(sec_dir, fname)) as f:
            in_data = False
            for line in f:
                s = line.rstrip()
                if s.startswith("hadiths["):
                    in_data = True
                    continue
                if not in_data or not s:
                    continue
                try:
                    if int(s.split(",")[0]) == hn:
                        return sec_id
                except:
                    pass
    return None


def main():
    print("Fetching missing translations from sunnah.com...")
    print()

    # First try API interception approach - fetch the page and extract
    # Let's test with one hadith first
    for book, hns in MISSING.items():
        slug = BOOK_SLUGS[book]
        print(f"\n{'='*50}")
        print(f"BOOK: {book} — {len(hns)} hadiths to fetch (hns {hns[0]}–{hns[-1]})")

        results = {}
        for hn in hns[:3]:  # Test with first 3
            print(f"  Trying hn {hn}...")

            # Method 1: Direct page scrape
            text = get_hadith_text(slug, hn)
            if text:
                results[hn] = text
                print(f"    ✓ Got from page: {text[:60]}...")
            else:
                # Method 2: API
                text = try_api_endpoint(slug, hn)
                if text:
                    results[hn] = text
                    print(f"    ✓ Got from API: {text[:60]}...")
                else:
                    print(f"    ✗ Not found")

            time.sleep(0.5)

        print(f"  Results: {len(results)}/{min(3,len(hns))} succeeded")
        if results:
            sample_hn = list(results.keys())[0]
            print(f"  Sample text for hn {sample_hn}: {results[sample_hn][:120]}")


if __name__ == "__main__":
    main()
