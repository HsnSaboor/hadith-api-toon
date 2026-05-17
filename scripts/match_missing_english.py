#!/usr/bin/env python3
"""Aggressively match remaining lulu hadiths to local Bukhari/Muslim English."""
import os, re, json
from concurrent.futures import ProcessPoolExecutor

BASE = os.path.dirname(os.path.dirname(__file__))

def normalize(t):
    t = re.sub(r'[^\u0621-\u064A\s]', '', t)
    t = t.replace('\u0649', '\u064A').replace('\u0626', '\u0625')
    t = t.replace('\u0623', '\u0627').replace('\u0625', '\u0627')
    return re.sub(r'\s+', ' ', t).strip()

def load_index(book, lang='ar'):
    """Load all hadiths from a book into a dict."""
    data = {}
    base = os.path.join(BASE, f'editions/{book}/sections' if lang == 'ar' else f'editions/{book}/translations/en/sections')
    if not os.path.exists(base):
        return data
    for fn in sorted(os.listdir(base), key=lambda x: int(x.split('.')[0])):
        with open(os.path.join(base, fn), encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.strip() and not line.startswith('hadiths['):
                    p = line.split(',', 1)
                    if p[0].strip().isdigit() and len(p) > 1:
                        data[p[0].strip()] = p[1].strip()
    return data

print("Loading Bukhari data...")
bukh_ar = load_index('bukhari', 'ar')
bukh_en = load_index('bukhari', 'en')
print(f"  Arabic: {len(bukh_ar)}, English: {len(bukh_en)}")

print("Loading Muslim data...")
mus_ar = load_index('muslim', 'ar')
mus_en = load_index('muslim', 'en')
print(f"  Arabic: {len(mus_ar)}, English: {len(mus_en)}")

# Normalize all Arabic texts
bukh_norm = {k: normalize(v) for k, v in bukh_ar.items()}
mus_norm = {k: normalize(v) for k, v in mus_ar.items()}

# Load lulu
with open(os.path.join(BASE, 'scraped_data/lulu-wal-marjan_full.json')) as f:
    lulu = json.load(f)

# Load current English to find missing
missing = []
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/lulu-wal-marjan/sections')), key=lambda x: int(x.split('.')[0])):
    ch = int(fn.split('.')[0])
    with open(os.path.join(BASE, f'editions/lulu-wal-marjan/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and (len(p) == 1 or not p[1].strip()):
                    missing.append((ch, p[0].strip()))

print(f"\nMissing: {len(missing)} hadiths")

# For each missing, try to match with improved algorithm
matched_from_bukh = 0
matched_from_mus = 0

for ch, hn in missing:
    if hn not in lulu:
        continue
    ar = lulu[hn].get('arabic', '')
    if not ar:
        continue
    
    norm_ar = normalize(ar)
    found_en = None
    source = None
    
    # Strategy 1: Look for a distinctive 60-char substring in the entire text
    # This handles hadiths where core extraction fails
    candidates = []
    
    # Search in Bukhari
    for i in range(0, max(1, len(norm_ar) - 55), 5):
        phrase = norm_ar[i:i+55]
        if len(phrase) >= 50:
            for bhn, bnorm in bukh_norm.items():
                if phrase in bnorm:
                    candidates.append((bhn, 'bukhari'))
                    break
    
    # Search in Muslim
    if not candidates:
        for i in range(0, max(1, len(norm_ar) - 55), 5):
            phrase = norm_ar[i:i+55]
            if len(phrase) >= 50:
                for mhn, mnorm in mus_norm.items():
                    if phrase in mnorm:
                        candidates.append((mhn, 'muslim'))
                        break
    
    # Get English for candidates
    for src_hn, src_book in candidates[:3]:
        if src_book == 'bukhari' and src_hn in bukh_en:
            found_en = bukh_en[src_hn]
            source = 'bukhari'
            break
        elif src_book == 'muslim' and src_hn in mus_en:
            found_en = mus_en[src_hn]
            source = 'muslim'
            break
    
    if found_en:
        if source == 'bukhari':
            matched_from_bukh += 1
        else:
            matched_from_mus += 1
        
        # Write to English section file
        en_fn = os.path.join(BASE, f'editions/lulu-wal-marjan/translations/en/sections/{ch}.toon')
        with open(en_fn, 'r') as f:
            content = f.read()
        # Replace the line for this hadith
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith(f'{hn},') or line.startswith(f'{hn},"'):
                escaped = found_en.replace('"', '""')
                new_lines.append(f'{hn},"{escaped}"')
            else:
                new_lines.append(line)
        with open(en_fn, 'w') as f:
            f.write('\n'.join(new_lines))

print(f"\nNew matches: Bukhari={matched_from_bukh}, Muslim={matched_from_mus}")
print(f"Total new: {matched_from_bukh + matched_from_mus}")

# Final count
total = matched = 0
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/lulu-wal-marjan/sections')), key=lambda x: int(x.split('.')[0])):
    ch = int(fn.split('.')[0])
    with open(os.path.join(BASE, f'editions/lulu-wal-marjan/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                total += 1
    with open(os.path.join(BASE, f'editions/lulu-wal-marjan/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if len(p) > 1 and p[1].strip():
                    matched += 1

print(f"\nFinal English: {matched}/{total} ({100*matched//total}%)")
