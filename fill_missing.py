#!/usr/bin/env python3
"""Fill missing Urdu/English/Arabic translations from quranohadith.com.

Uses httpx with 128 parallel workers.
Only fills books missing any of: urdu, english, arabic.
"""

import asyncio
import os
import re
import sys

import httpx

BASE_URL = "https://quranohadith.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}
WORKERS = 128
TEXTAREA_RE = re.compile(r'<textarea[^>]*ID="content-(\w+)-(\d+)"[^>]*>(.*?)</textarea>', re.DOTALL | re.IGNORECASE)

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

EDITIONS_DIR = "editions"

LANG_MAP = {
    "ur": ("urd", "urdu"),
    "en": ("eng", "english"),
    "ar": ("arb", "arabic"),
}

def extract_textareas(html):
    result = {}
    for m in TEXTAREA_RE.finditer(html):
        lang = m.group(1).lower()
        id_ = m.group(2)
        text = m.group(3)
        text = text.replace("&#13;", "").replace("&#10;", "\n")
        for e in [("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'"),("&apos;","'")]:
            text = text.replace(*e)
        text = text.strip()
        if text:
            result.setdefault(lang, {})[id_] = text
    return result

def check_missing():
    missing = {}
    for d in sorted(os.listdir(EDITIONS_DIR)):
        if not os.path.isdir(os.path.join(EDITIONS_DIR, d)):
            continue
        tr = os.path.join(EDITIONS_DIR, d, "translations")
        if not os.path.isdir(tr):
            continue
        counts = {}
        for lang in os.listdir(tr):
            sec = os.path.join(tr, lang, "sections")
            if not os.path.isdir(sec):
                continue
            filled = 0
            for fn in os.listdir(sec):
                if not fn.endswith(".toon"):
                    continue
                with open(os.path.join(sec, fn)) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("hadiths"):
                            continue
                        if "," in line:
                            t = line.split(",", 1)[1].strip().strip('"\' ')
                            if len(t) > 10:
                                filled += 1
            counts[lang] = filled
        need = {}
        for local, (site_key, _) in LANG_MAP.items():
            if counts.get(local, 0) < 10:
                need[local] = site_key
        if need:
            missing[d] = {"slug": SLUG_MAP.get(d, d), "counts": counts, "need": need}
    return missing

async def fetch_one(client, slug, num, sem):
    async with sem:
        url = f"{BASE_URL}/{slug}/{num}"
        try:
            r = await client.get(url, timeout=30)
            r.raise_for_status()
            ta = extract_textareas(r.text)
            # Take first non-empty text of each language (internal IDs may not match URL number)
            urd = next((v for v in ta.get("urd",{}).values() if len(v) > 50), "")
            eng = next((v for v in ta.get("eng",{}).values() if len(v) > 50), "")
            arb = next((v for v in ta.get("arb",{}).values() if len(v) > 50), "")
            return num, urd, eng, arb, None
        except Exception as e:
            return num, "", "", "", str(e)

async def scrape_book(client, our, al, limit=500):
    idx_url = f"{BASE_URL}/hadees-name/{al}/0"
    try:
        r = await client.get(idx_url, timeout=30)
        m = re.search(r'([\d,]+)\s*Narrations?', r.text)
        total = min(int(m.group(1).replace(",","")), limit) if m else limit
    except:
        total = limit

    print(f"  {our}: {total} hadith @ 128 workers...")
    sem = asyncio.Semaphore(WORKERS)
    tasks = [fetch_one(client, al, i, sem) for i in range(1, total+1)]

    results, d = {}, {"urd":0,"eng":0,"arb":0}
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        num, urd, eng, arb, err = await coro
        results[num] = {"urd":urd,"eng":eng,"arb":arb,"err":err}
        if len(urd)>50: d["urd"]+=1
        if len(eng)>50: d["eng"]+=1
        if len(arb)>50: d["arb"]+=1
        if i==1 or i%500==0 or i==total:
            print(f"    {i}/{total}: urd={d['urd']} eng={d['eng']} arb={d['arb']}")
    return results

def write_section(results, site_key, out_dir):
    items = [(n,r[site_key]) for n,r in sorted(results.items()) if len(r.get(site_key,""))>50]
    if not items:
        return 0
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir,"1.toon"), "w") as f:
        f.write(f"hadiths[{len(items)}]{{hadithnumber,text}}:\n")
        for n,t in items:
            f.write(f'"{n}","{t.replace(chr(10),"\\n").replace(chr(34),chr(34)+chr(34))}"\n')
    return len(items)

async def main():
    missing = check_missing()
    if not missing:
        print("All books have Urdu, English, and Arabic. Nothing to fill.")
        return

    print("Books needing work:")
    for b, info in missing.items():
        print(f"  {b}: {info['counts']} -> missing {info['need']}")
    print()

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for our, info in missing.items():
            if our not in SLUG_MAP:
                print(f"\nSKIP {our}: no slug mapping")
                continue
            al = info["slug"]
            print(f"\n--- {our} ({al}) ---")
            results = await scrape_book(client, our, al)

            for local, (site_key, name) in LANG_MAP.items():
                if local not in info["need"]:
                    continue
                out = os.path.join(EDITIONS_DIR, our, "translations", local, "sections")
                n = write_section(results, site_key, out)
                if n:
                    print(f"  FILLED {name}: {n} hadith -> {out}/1.toon")
                else:
                    print(f"  SKIP {name}: no real content from site")

if __name__ == "__main__":
    asyncio.run(main())
