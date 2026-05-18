#!/usr/bin/env python3
"""Fill ALL remaining Arabic to 100% from quranohadith.com + sunnah.com."""

import asyncio, os, re, collections
import httpx

QURAN = "https://quranohadith.com"
SUNNA = "https://sunnah.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
WORKERS = 128
TEXTAREA_RE = re.compile(r'<textarea[^>]*ID="content-(\w+)-(\d+)"[^>]*>(.*?)</textarea>', re.DOTALL | re.IGNORECASE)

EDITIONS = "editions"

# Books on quranohadith.com
QURAN_SLUGS = {
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

# Books on sunnah.com
SUNNA_SLUGS = {
    "qudsi": "qudsi40",      # 40 hadith
    "nawawi": "nawawi40",    # 42 hadith
}

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

def extract_sunnah_arabic(html):
    """Extract Arabic text from sunnah.com page."""
    # Find div with Arabic text content (character detection)
    for m in re.finditer(r'<div[^>]*>(.*?)</div>', html, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06ff' or '\u0750' <= c <= '\u077f')
        if arabic_chars > 20 and len(text) > 50:
            return text
    return ""

def build_hadith_to_section(book):
    """Map hadith number -> section filename."""
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
                    try:
                        n = int(line.split(",", 1)[0].strip('"'))
                        mapping[n] = fn
                    except ValueError:
                        pass
    return mapping

def get_existing_ar(book):
    """Return set of hadith numbers already filled in ar translations."""
    existing = set()
    d = os.path.join(EDITIONS, book, "translations", "ar", "sections")
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
                    try:
                        n = int(line.split(",", 1)[0].strip('"'))
                        t = line.split(",", 1)[1].strip().strip('"\' ')
                        if len(t) > 10:
                            existing.add(n)
                    except ValueError:
                        pass
    return existing

async def fetch_arabic_qa(client, slug, num, sem):
    """Fetch Arabic from quranohadith.com."""
    async with sem:
        try:
            r = await client.get(f"{QURAN}/{slug}/{num}", timeout=30)
            ta = extract_textareas(r.text)
            if isinstance(ta, dict):
                arb = next((v for v in ta.get("arb", set()) if len(v) > 50), "")
                return num, arb, None
            return num, "", "no_textareas"
        except Exception as e:
            return num, "", str(e)

async def fetch_arabic_sunna(client, sunna_slug, num, sem):
    """Fetch Arabic from sunnah.com."""
    async with sem:
        try:
            r = await client.get(f"{SUNNA}/{sunna_slug}/{num}", timeout=30)
            arabic = extract_sunnah_arabic(r.text)
            return num, arabic, None
        except Exception as e:
            return num, "", str(e)

async def scrape_all_arabic(client, slug, total, existing_set, source="quran", sunna_slug=None):
    """Scrape ALL missing Arabic for a book."""
    needed = set(range(1, total+1)) - existing_set
    if not needed:
        return {}
    print(f"    scraping {len(needed)} missing Arabic hadith...", flush=True)
    sem = asyncio.Semaphore(WORKERS)
    
    if source == "quran":
        tasks = [fetch_arabic_qa(client, slug, i, sem) for i in sorted(needed)]
    else:
        tasks = [fetch_arabic_sunna(client, sunna_slug, i, sem) for i in sorted(needed)]
    
    results = {}
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        num, arabic, err = await coro
        if len(arabic) > 50:
            results[num] = arabic
        if i % 1000 == 0 or i == len(tasks):
            print(f"      {i}/{len(tasks)}", flush=True)
    return results

def write_arabic(book, results, h2s):
    """Write Arabic to proper section files. Numbers not in sections -> 0.toon flat."""
    out_dir = os.path.join(EDITIONS, book, "translations", "ar", "sections")
    os.makedirs(out_dir, exist_ok=True)
    
    by_sec = collections.defaultdict(dict)
    orphans = {}
    for n, text in sorted(results.items()):
        fn = h2s.get(n)
        if fn:
            by_sec[fn][n] = text
        else:
            orphans[n] = text
    
    written = 0
    for fn, entries in by_sec.items():
        ofn = os.path.join(out_dir, fn)
        existing = open(ofn).read() if os.path.exists(ofn) else ""
        dat = existing.strip().split("\n")[1:] if existing.strip().startswith("hadiths[") else []
        
        ex = {}
        for dl in dat:
            dl = dl.strip()
            if not dl: continue
            try:
                ex[int(dl.split(",", 1)[0].strip('"'))] = dl
            except: pass
        
        for n, text in entries.items():
            if n in ex: continue
            ex[n] = f'"{n}","{text.replace(chr(10),"\\n").replace(chr(34),chr(34)+chr(34))}"'
        
        sk = sorted(ex)
        with open(ofn, "w") as f:
            f.write(f"hadiths[{len(sk)}]{{hadithnumber,text}}:\n")
            for k in sk:
                f.write(ex[k] + "\n")
        written += len(entries)
    
    if orphans:
        ofn = os.path.join(out_dir, "0.toon")
        existing = open(ofn).read() if os.path.exists(ofn) else ""
        dat = existing.strip().split("\n")[1:] if existing.strip().startswith("hadiths[") else []
        
        ex = {}
        for dl in dat:
            dl = dl.strip()
            if not dl: continue
            try:
                ex[int(dl.split(",", 1)[0].strip('"'))] = dl
            except: pass
        
        for n, text in sorted(orphans.items()):
            if n in ex: continue
            ex[n] = f'"{n}","{text.replace(chr(10),"\\n").replace(chr(34),chr(34)+chr(34))}"'
        
        sk = sorted(ex)
        with open(ofn, "w") as f:
            f.write(f"hadiths[{len(sk)}]{{hadithnumber,text}}:\n")
            for k in sk:
                f.write(ex[k] + "\n")
        written += len(orphans)
        print(f"      wrote {len(orphans)} arabic to 0.toon", flush=True)
    
    return written

def copy_arabic_from_main(book, total=None):
    """Copy Arabic from main sections to translations/ar/ using simple CSV parse."""
    src_dir = os.path.join(EDITIONS, book, "sections")
    dst_dir = os.path.join(EDITIONS, book, "translations", "ar", "sections")
    if not os.path.isdir(src_dir):
        return 0
    os.makedirs(dst_dir, exist_ok=True)
    
    written = 0
    for fn in sorted(os.listdir(src_dir)):
        if not fn.endswith(".toon"):
            continue
        src_c = open(os.path.join(src_dir, fn)).read()
        lines = src_c.strip().split("\n")
        if not lines or not lines[0].startswith("hadiths["):
            continue
        
        dst_fn = os.path.join(dst_dir, fn)
        existing = open(dst_fn).read() if os.path.exists(dst_fn) else ""
        
        existing_entries = {}
        if existing:
            for dl in existing.strip().split("\n")[1:]:
                dl = dl.strip()
                if not dl: continue
                try:
                    en = int(dl.split(",", 1)[0].strip('"'))
                    existing_entries[en] = dl
                except: pass
        
        added = 0
        for dl in lines[1:]:
            dl = dl.strip()
            if not dl: continue
            try:
                n = int(dl.split(",", 1)[0].strip('"'))
            except: continue
            if n in existing_entries:
                continue
            
            # Find arabic field (between first and second comma)
            parts = dl.split(",", 2)
            if len(parts) < 3:
                continue
            arabic = parts[1].strip().strip('"')
            # Handle quoted arabic with inner commas
            if parts[1].startswith('"') and not parts[1].endswith('"'):
                # Arabic has commas, use regex
                m = re.match(r'^"((?:[^"]|"")*)"', dl.split(",", 1)[1])
                if m:
                    arabic = m.group(1)
                else:
                    continue
            
            if len(arabic) > 10:
                entry = f'"{n}","{arabic.replace(chr(10),"\\n").replace(chr(34),chr(34)+chr(34))}"'
                existing_entries[n] = entry
                added += 1
        
        if added:
            sorted_entries = [existing_entries[k] for k in sorted(existing_entries)]
            with open(dst_fn, "w") as f:
                f.write(f"hadiths[{len(sorted_entries)}]{{hadithnumber,text}}:\n")
                for e in sorted_entries:
                    f.write(e + "\n")
            written += added
    
    return written

async def main():
    print("=== Phase 1: Fill remaining Arabic from quranohadith.com ===", flush=True)
    
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        # Get site totals
        async def get_total(slug):
            r = await client.get(f"{QURAN}/hadees-name/{slug}/0", timeout=30)
            m = re.search(r'([\d,]+)\s*Narrations?', r.text)
            return int(m.group(1).replace(",","")) if m else 0
        
        for our, slug in QURAN_SLUGS.items():
            total = await get_total(slug)
            if total == 0:
                continue
            
            print(f"\n--- {our} ({slug}) - {total} hadith ---", flush=True)
            h2s = build_hadith_to_section(our)
            existing = get_existing_ar(our)
            print(f"  existing ar: {len(existing)}, sections: {len(h2s)}, site total: {total}", flush=True)
            
            needed = set(range(1, total+1)) - existing
            if not needed:
                print("  already complete!", flush=True)
                continue
            
            print(f"  {len(needed)} Arabic hadith missing", flush=True)
            
            # Peek: does site have Arabic?
            peek = await client.get(f"{QURAN}/{slug}/1", timeout=30)
            ta = extract_textareas(peek.text)
            if isinstance(ta, dict):
                sample = next((v for v in ta.get("arb", set()) if len(v) > 50), "")
            else:
                sample = ""
            
            if not sample:
                print("  no Arabic on site for this book, skip", flush=True)
                continue
            
            results = await scrape_all_arabic(client, slug, total, existing, source="quran")
            if not results:
                print("  no new Arabic from site", flush=True)
                continue
            
            written = write_arabic(our, results, h2s)
            print(f"  wrote {written} new Arabic hadith", flush=True)
    
    print("\n=== Phase 2: Fill Arabic from sunnah.com ===", flush=True)
    
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for our, slug in SUNNA_SLUGS.items():
            total = 42 if our == "nawawi" else 40  # known counts
            print(f"\n--- {our} ({slug}) - {total} hadith ---", flush=True)
            
            h2s = build_hadith_to_section(our)
            existing = get_existing_ar(our)
            print(f"  existing ar: {len(existing)}", flush=True)
            
            needed = set(range(1, total+1)) - existing
            if not needed:
                print("  already complete!", flush=True)
                continue
            
            results = await scrape_all_arabic(client, slug, total, existing, source="sunna", sunna_slug=slug)
            if not results:
                print("  no new Arabic from sunnah.com", flush=True)
                continue
            
            written = write_arabic(our, results, h2s)
            print(f"  wrote {written} new Arabic hadith", flush=True)
    
    print("\n=== Phase 3: Copy Arabic from main sections for small books ===", flush=True)
    for book in ["dehlawi", "nawawi", "qudsi"]:
        written = copy_arabic_from_main(book)
        print(f"  {book}: copied {written} Arabic hadith from main sections", flush=True)
    
    print("\n=== Final Summary ===", flush=True)
    for book in sorted(os.listdir(EDITIONS)):
        tr = os.path.join(EDITIONS, book, "translations", "ar", "sections")
        if not os.path.isdir(tr):
            continue
        filled = 0
        for fn in sorted(os.listdir(tr)):
            if not fn.endswith(".toon"):
                continue
            c = open(os.path.join(tr, fn)).read()
            for line in c.split("\n"):
                line = line.strip()
                if not line or line.startswith("hadiths"):
                    continue
                if "," in line:
                    t = line.split(",", 1)[1].strip().strip('"\' ')
                    if len(t) > 10:
                        filled += 1
        print(f"  {book}/ar: {filled}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
