#!/usr/bin/env python3
"""Download Arabic for remaining partial books from sunnah.com AJAX API."""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sunnah.com-download")
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://sunnah.com/"}

def fetch(lang, slug, page):
    try:
        req = urllib.request.Request(f"https://sunnah.com/ajax/{lang}/{slug}/{page}", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except:
        return None

def max_page(col, lang="arabic", limit=100):
    lo, hi = 1, 2
    # exponential search
    while hi <= limit:
        d = fetch(lang, col, hi)
        if not d or len(d) == 0:
            break
        lo, hi = hi, hi * 2
        time.sleep(0.2)
    hi = min(hi, limit)
    # binary search
    while lo < hi:
        mid = (lo + hi + 1) // 2
        d = fetch(lang, col, mid)
        if d and len(d) > 0:
            lo = mid
        else:
            hi = mid - 1
        time.sleep(0.2)
    return lo

def save(slug, lang_code, hadiths):
    path = os.path.join(OUT_DIR, slug, f"{lang_code}.json")
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

cols = ["darimi", "ibnkhuzayma", "hakim", "ibnabishayba", "daraqutni", "bayhaqi"]

for col in cols:
    mp = max_page(col)
    print(f"{col}: max page = {mp}")
    all_h = {}
    for p in range(1, mp + 1):
        d = fetch("arabic", col, p)
        if not d:
            continue
        for item in d:
            hn = str(item.get("hadithNumber", ""))
            text = (item.get("hadithText", "") or "").replace('<span class="arabic_sanad">', "").replace("</span>", "")
            if hn and text:
                all_h[hn] = {"hadithnumber": hn, "text": text}
        time.sleep(0.3)
    total = save(col, "ar", list(all_h.values()))
    print(f"  Saved {total} hadiths")
    time.sleep(1)

print("\nDone!")
