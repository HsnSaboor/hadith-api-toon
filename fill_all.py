#!/usr/bin/env python3
"""Fill ALL ar/en/ur translations at 100% with no cap. 128 workers."""

import asyncio, os, re, sys, collections
import httpx

BASE_URL = "https://quranohadith.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
WORKERS = 128
TEXTAREA_RE = re.compile(r'<textarea[^>]*ID="content-(\w+)-(\d+)"[^>]*>(.*?)</textarea>', re.DOTALL | re.IGNORECASE)

SLUG_MAP = {
    "abudawud": "abu-dawood", "aladab-almufrad": "aladab-almufrad",
    "bayhaqi": "bayhaqi", "bukhari": "bukhari", "bulugh-al-maram": "bulugh-al-maram",
    "fatah-alrabani": "fatah-alrabani", "ibnmajah": "ibn-e-maja",
    "lulu-wal-marjan": "lulu-wal-marjan", "malik": "imam-malik",
    "mishkat": "mishkat", "muajam-tabarani-saghir": "muajam-tabarani-saghir",
    "musannaf-ibn-abi-shaybah": "musannaf-ibn-abi-shaybah",
    "muslim": "muslim", "musnad-ahmed": "musnad-ahmed",
    "mustadrak": "mustadrak", "nasai": "nisai",
    "sahih-ibn-khuzaymah": "sahih-ibn-khuzaymah",
    "shamail-tirmazi": "shamail-tirmazi", "silsila-sahih": "silsila-sahih",
    "sunan-al-daraqutni": "sunan-al-daraqutni", "sunan-darmi": "sunan-darmi",
    "tirmidhi": "tirmazi",
}

LANG_MAP = {"ur": "urd", "en": "eng", "ar": "arb"}
EDITIONS = "editions"

def extract_textareas(html):
    result = {}
    for m in TEXTAREA_RE.finditer(html):
        lang = m.group(1).lower()
        text = m.group(3)
        text = text.replace("&#13;", "").replace("&#10;", "\n")
        for e in [("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'"),("&apos;","'")]:
            text = text.replace(*e)
        text = text.strip()
        if text:
            result.setdefault(lang, set()).add(text)
    return result

def get_existing_hadith(book, lang):
    existing = set()
    d = os.path.join(EDITIONS, book, "translations", lang, "sections")
    if not os.path.isdir(d):
        return existing
    for fn in os.listdir(d):
        if not fn.endswith(".toon"):
            continue
        with open(os.path.join(d, fn)) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("hadiths"):
                    continue
                if "," in line:
                    parts = line.split(",", 1)
                    try:
                        n = int(parts[0].strip('"'))
                        t = parts[1].strip().strip('"\' ')
                        if len(t) > 10:
                            existing.add(n)
                    except ValueError:
                        pass
    return existing

def build_hadith_to_section(book):
    mapping = {}
    d = os.path.join(EDITIONS, book, "sections")
    if not os.path.isdir(d):
        return mapping
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".toon"):
            continue
        with open(os.path.join(d, fn)) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("hadiths"):
                    continue
                if "," in line:
                    parts = line.split(",", 1)
                    try:
                        n = int(parts[0].strip('"'))
                        mapping[n] = fn
                    except ValueError:
                        pass
    return mapping

async def fetch_one(client, slug, num, sem):
    async with sem:
        url = f"{BASE_URL}/{slug}/{num}"
        try:
            r = await client.get(url, timeout=30)
            r.raise_for_status()
            ta = extract_textareas(r.text)
            urd = next((v for v in ta.get("urd", set()) if len(v) > 50), "")
            eng = next((v for v in ta.get("eng", set()) if len(v) > 50), "")
            arb = next((v for v in ta.get("arb", set()) if len(v) > 50), "")
            return num, urd, eng, arb, None
        except Exception as e:
            return num, "", "", "", str(e)

async def scrape_book(client, slug, missing_set):
    if not missing_set:
        return {}
    print(f"    scraping {len(missing_set)} hadith...", flush=True)
    sem = asyncio.Semaphore(WORKERS)
    tasks = [fetch_one(client, slug, i, sem) for i in sorted(missing_set)]
    results = {}
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        num, urd, eng, arb, err = await coro
        results[num] = {"urd": urd, "eng": eng, "arb": arb}
        if i % 1000 == 0 or i == len(tasks):
            print(f"      {i}/{len(tasks)}", flush=True)
    return results

def write_all_translations(book, lang, hadith_texts, h2s):
    """Batch-write all new hadith per section file (O(n) instead of O(n²))."""
    # Group new entries by section file
    by_section = collections.defaultdict(list)
    for n, text in sorted(hadith_texts.items()):
        if len(text) <= 50:
            continue
        sec_fn = h2s.get(n)
        if not sec_fn:
            continue
        by_section[sec_fn].append((n, text))

    written = 0
    out_dir = os.path.join(EDITIONS, book, "translations", lang, "sections")
    os.makedirs(out_dir, exist_ok=True)

    for sec_fn, entries in by_section.items():
        out_fn = os.path.join(out_dir, sec_fn)
        if os.path.exists(out_fn):
            with open(out_fn) as f:
                existing = f.read()
        else:
            existing = ""

        lines = existing.strip().split("\n") if existing.strip() else []
        data_lines = lines[1:] if lines and lines[0].startswith("hadiths[") else lines

        # Parse existing entries
        existing_entries = {}
        for dl in data_lines:
            dl = dl.strip()
            if not dl:
                continue
            try:
                en = int(dl.split(",")[0].strip('"'))
                existing_entries[en] = dl
            except ValueError:
                pass

        # Merge new entries
        skip = 0
        for n, text in entries:
            if n in existing_entries:
                skip += 1
                continue
            entry = f'"{n}","{text.replace(chr(10),"\\n").replace(chr(34),chr(34)+chr(34))}"'
            existing_entries[n] = entry

        # Write back in sorted order
        if skip == len(entries):
            continue  # nothing new
        sorted_entries = [existing_entries[k] for k in sorted(existing_entries)]
        with open(out_fn, "w") as f:
            f.write(f"hadiths[{len(sorted_entries)}]{{hadithnumber,text}}:\n")
            for dl in sorted_entries:
                f.write(dl + "\n")
        written += len(entries) - skip

    return written

async def main():
    print("Getting site totals...", flush=True)
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        async def get_total(slug):
            r = await client.get(f"{BASE_URL}/hadees-name/{slug}/0", timeout=30)
            m = re.search(r'([\d,]+)\s*Narrations?', r.text)
            return int(m.group(1).replace(",","")) if m else 0

        totals = {}
        for our, slug in SLUG_MAP.items():
            totals[our] = await get_total(slug)
            print(f"  {our}: {totals[our]}", flush=True)

    for our, total in totals.items():
        if total == 0:
            print(f"\nSKIP {our}: no site data", flush=True)
            continue

        slug = SLUG_MAP[our]
        print(f"\n=== {our} ({slug}) - {total} hadith ===", flush=True)

        h2s = build_hadith_to_section(our)
        if not h2s:
            print("  no sections found, skip", flush=True)
            continue

        max_h = max(h2s.keys())
        all_needed = set(range(1, total+1)) & set(h2s.keys())
        print(f"  sections cover {len(h2s)} hadith nums (1-{max_h}), {len(all_needed)} overlap with site", flush=True)

        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
            peek = await client.get(f"{BASE_URL}/{slug}/1", timeout=30)
            ta = extract_textareas(peek.text)

            langs_to_fetch = {}
            for lang, site_key in LANG_MAP.items():
                lang_dir = os.path.join(EDITIONS, our, "translations", lang)
                if not os.path.isdir(lang_dir):
                    continue
                sample = next((v for v in ta.get(site_key, set()) if len(v) > 50), "")
                if not sample:
                    print(f"  {lang}: no content on site, skip", flush=True)
                    continue
                existing = get_existing_hadith(our, lang)
                missing = all_needed - existing
                if not missing:
                    print(f"  {lang}: {len(existing)} exist, complete", flush=True)
                    continue
                print(f"  {lang}: {len(existing)} exist, {len(missing)} missing", flush=True)
                langs_to_fetch[lang] = {"site_key": site_key, "missing": missing}

            if not langs_to_fetch:
                print("  nothing to fetch", flush=True)
                continue

            all_missing = set()
            for info in langs_to_fetch.values():
                all_missing |= info["missing"]
            print(f"  total unique hadith to scrape: {len(all_missing)}", flush=True)

            results = await scrape_book(client, slug, all_missing)
            if not results:
                continue

            for lang, info in langs_to_fetch.items():
                hadith_texts = {n: d[info["site_key"]] for n, d in results.items()
                                if n in info["missing"] and len(d.get(info["site_key"], "")) > 50}
                if not hadith_texts:
                    print(f"  {lang}: no new content from scrape", flush=True)
                    continue
                written = write_all_translations(our, lang, hadith_texts, h2s)
                print(f"  {lang}: wrote {written} new hadith", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
