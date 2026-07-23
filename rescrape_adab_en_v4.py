#!/usr/bin/env python3
"""Re-scrape English translations for aladab-almufrad via ARABIC TEXT MATCHING.

Both number-based and position-based alignment approaches failed due to:
  - sunnah.com reference-number bugs (duplicate advertised numbers)
  - genuine chapter-boundary drift between our local data and sunnah.com's
    chapter groupings (varies unpredictably per chapter)

This script instead extracts (arabic_text, english_text) pairs from every
sunnah.com chapter page (1..57), then matches each pair to our local AR
.toon hadith by NORMALIZED ARABIC TEXT (stripping diacritics/punctuation),
which is the one thing guaranteed to be identical between sources
regardless of numbering/chapter differences.
"""
import csv, io, os, re, time, json
import urllib.request
from bs4 import BeautifulSoup

ED = "/home/saboor/code/hadith-api-toon/editions/aladab-almufrad"
AR_DIR = f"{ED}/sections"
EN_DIR = f"{ED}/translations/en/sections"
CACHE_PATH = "/home/saboor/code/hadith-api-toon/rescrape_adab_en_v3_cache.json"  # reuse chapter cache (has ar+en potential)
PAIRS_CACHE_PATH = "/home/saboor/code/hadith-api-toon/rescrape_adab_en_v4_pairs_cache.json"

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

ARABIC_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u200f\u200e]')
NON_ARABIC_LETTERS = re.compile(r'[^\u0621-\u064A ]')


def normalize_arabic(text):
    text = ARABIC_DIACRITICS.sub('', text)
    text = NON_ARABIC_LETTERS.sub(' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch(url, retries=4):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            print(f"  retry {i+1} for {url}: {e}", flush=True)
            time.sleep(4 + i * 3)
    return ""


def scrape_chapter_pairs(chapter_id):
    """Returns list of (arabic_text, english_text) tuples in page order."""
    url = f"https://sunnah.com/adab/{chapter_id}"
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    containers = soup.find_all('div', class_='actualHadithContainer')
    pairs = []
    for c in containers:
        ar_div = c.find('div', class_='arabic_hadith_full')
        en_div = c.find('div', class_='english_hadith_full')
        ar_text = ar_div.get_text().strip() if ar_div else ''
        en_text = en_div.get_text(separator='\n').strip() if en_div else ''
        pairs.append((ar_text, en_text))
    return pairs


def load_our_hadiths():
    """Returns list of (hadithnumber, section_id, arabic_text) across all sections."""
    items = []
    section_files = sorted(
        [f for f in os.listdir(AR_DIR) if f.endswith('.toon')],
        key=lambda f: int(f.replace('.toon', ''))
    )
    for fn in section_files:
        sid = fn.replace('.toon', '')
        with open(f"{AR_DIR}/{fn}") as f:
            text = f.read()
        r = csv.reader(io.StringIO(text))
        next(r)
        for row in r:
            if len(row) >= 2:
                items.append((row[0], sid, row[1]))
    return items


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def main():
    cache = {}
    if os.path.exists(PAIRS_CACHE_PATH):
        with open(PAIRS_CACHE_PATH) as f:
            cache = json.load(f)
        print(f"Loaded pairs cache with {len(cache)} chapters done", flush=True)

    for chapter_id in range(1, 58):
        sid = str(chapter_id)
        if sid in cache:
            continue
        print(f"Scraping chapter {sid}...", flush=True)
        pairs = scrape_chapter_pairs(sid)
        cache[sid] = pairs
        print(f"  chapter {sid}: got {len(pairs)} pairs", flush=True)
        with open(PAIRS_CACHE_PATH, 'w') as f:
            json.dump(cache, f, ensure_ascii=False)
        time.sleep(1.5)

    # Build normalized-arabic -> english lookup from all scraped pairs
    ar_to_en = {}
    dup_ar_keys = set()
    total_pairs = 0
    for sid, pairs in cache.items():
        for ar_text, en_text in pairs:
            total_pairs += 1
            norm = normalize_arabic(ar_text)
            if not norm:
                continue
            if norm in ar_to_en and ar_to_en[norm] != en_text:
                dup_ar_keys.add(norm)
            ar_to_en[norm] = en_text
    print(f"\nTotal scraped pairs: {total_pairs}, unique normalized AR keys: {len(ar_to_en)}, "
          f"duplicate-with-different-EN: {len(dup_ar_keys)}", flush=True)

    our_hadiths = load_our_hadiths()
    print(f"Our total hadiths: {len(our_hadiths)}", flush=True)

    matched = 0
    unmatched = []
    hn_to_text = {}
    for hn, sid, ar_text in our_hadiths:
        norm = normalize_arabic(ar_text)
        if norm in ar_to_en:
            hn_to_text[hn] = ar_to_en[norm]
            matched += 1
        else:
            unmatched.append(hn)

    print(f"Matched: {matched}, Unmatched: {len(unmatched)}", flush=True)
    if unmatched:
        print(f"Unmatched numbers: {unmatched[:30]}", flush=True)

    with open("/home/saboor/code/hadith-api-toon/rescrape_adab_en_v4_unmatched.json", 'w') as f:
        json.dump(unmatched, f)

    # Write section files
    os.makedirs(EN_DIR, exist_ok=True)
    section_files = sorted(
        [f for f in os.listdir(AR_DIR) if f.endswith('.toon')],
        key=lambda f: int(f.replace('.toon', ''))
    )
    written = 0
    empty_count = 0
    for fn in section_files:
        sid = fn.replace('.toon', '')
        with open(f"{AR_DIR}/{fn}") as f:
            text = f.read()
        r = csv.reader(io.StringIO(text))
        next(r)
        nums = [row[0] for row in r if len(row) >= 2]

        lines = [f'"hadiths[{len(nums)}]{{hadithnumber,text}}:"']
        for n in nums:
            t = hn_to_text.get(n, '')
            if not t.strip():
                empty_count += 1
            lines.append(f"{n},{escape_toon_field(t)}")
        out_path = f"{EN_DIR}/{fn}"
        with open(out_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        written += 1

    print(f"Wrote {written} section files. Empty entries: {empty_count}", flush=True)


if __name__ == '__main__':
    main()
