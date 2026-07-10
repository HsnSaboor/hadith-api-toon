#!/usr/bin/env python3
"""Download Urdu, Bangla, Indonesian from sunnah.com AJAX API only."""

import json, os, sys, time, urllib.request

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sunnah.com-download")
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://sunnah.com/"}

def fetch(lang, col, page):
    try:
        req = urllib.request.Request(f"https://sunnah.com/ajax/{lang}/{col}/{page}", headers=H)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except:
        return None

def save(slug, lang_code, hadiths):
    path = os.path.join(OUT, slug, f"{lang_code}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = {}
    if os.path.exists(path):
        with open(path) as f:
            for h in json.load(f):
                existing[h["hadithnumber"]] = h
    for h in hadiths:
        if h.get("text"):
            existing[h["hadithnumber"]] = h
    ordered = sorted(existing.values(), key=lambda x: x["hadithnumber"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
    return len(ordered)

# Known page counts from probe
tasks = [
    ("bukhari", "urdu", "ur", 63),
    ("abudawud", "urdu", "ur", 1),
    ("bukhari", "bangla", "bn", 97),
    ("bukhari", "indonesian", "id", 63),
    ("nasai", "indonesian", "id", 51),
    ("abudawud", "indonesian", "id", 1),
]

for slug, lang, code, max_p in tasks:
    print(f"\n{slug}/{lang} ({code}): {max_p} pages")
    all_h = {}
    for p in range(1, max_p + 1):
        d = fetch(lang, slug, p)
        if d:
            for item in d:
                hn = str(item.get("hadithNumber", ""))
                text = (item.get("hadithText", "") or "").replace('<span class="arabic_sanad">', "").replace("</span>", "")
                if hn and text:
                    all_h[hn] = {"hadithnumber": hn, "text": text}
        if p % 10 == 0 or p == max_p:
            print(f"  page {p}/{max_p}, hadiths: {len(all_h)}")
        time.sleep(0.4)
    total = save(slug, code, list(all_h.values()))
    print(f"  Saved {total} hadiths to {slug}/{code}.json")
    time.sleep(2)

print("\nDone!")
