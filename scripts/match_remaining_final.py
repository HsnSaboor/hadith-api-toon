#!/usr/bin/env python3
"""Match remaining hadiths using shorter substring matching."""
import os, re, json

BASE = os.path.dirname(os.path.dirname(__file__))

def normalize(t):
    t = re.sub(r'[^\u0621-\u064A\s]', '', t)
    t = t.replace('\u0649', '\u064A').replace('\u0626', '\u0625')
    t = t.replace('\u0623', '\u0627').replace('\u0625', '\u0627')
    return re.sub(r'\s+', ' ', t).strip()

# Load all English
bukh_en = {}
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/bukhari/translations/en/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/bukhari/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1 and p[1].strip():
                    bukh_en[p[0].strip()] = p[1].strip()

mus_en = {}
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/muslim/translations/en/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/muslim/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1 and p[1].strip():
                    mus_en[p[0].strip()] = p[1].strip()

# Build a simple index: for each bukhari/muslim arabic, store its number
# Use 20-char fingerprints
bukh_fp = {}
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/bukhari/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/bukhari/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1:
                    norm = normalize(p[1])
                    for i in range(0, max(1, len(norm)-15), 3):
                        fp = norm[i:i+20]
                        if len(fp) >= 15 and fp not in bukh_fp:
                            bukh_fp[fp] = p[0].strip()

mus_fp = {}
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/muslim/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/muslim/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1:
                    norm = normalize(p[1])
                    for i in range(0, max(1, len(norm)-15), 3):
                        fp = norm[i:i+20]
                        if len(fp) >= 15 and fp not in mus_fp:
                            mus_fp[fp] = p[0].strip()

print(f"Bukhari fingerprints: {len(bukh_fp)}")
print(f"Muslim fingerprints: {len(mus_fp)}")

with open(os.path.join(BASE, 'scraped_data/lulu-wal-marjan_full.json')) as f:
    lulu = json.load(f)

# Find missing
missing = []
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/lulu-wal-marjan/sections')), key=lambda x: int(x.split('.')[0])):
    ch = int(fn.split('.')[0])
    with open(os.path.join(BASE, f'editions/lulu-wal-marjan/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and (len(p) == 1 or not p[1].strip()):
                    missing.append((ch, p[0].strip()))

print(f"Missing: {len(missing)}")

matched = 0
for ch, hn in missing:
    if hn not in lulu:
        continue
    ar = lulu[hn].get('arabic', '')
    if not ar:
        continue
    norm_ar = normalize(ar)
    
    found_src = None
    
    # Try 20-char fingerprints in Bukhari
    for i in range(0, max(1, len(norm_ar)-15), 3):
        fp = norm_ar[i:i+20]
        if len(fp) >= 15 and fp in bukh_fp:
            src_hn = bukh_fp[fp]
            if src_hn in bukh_en:
                found_src = ('bukhari', src_hn, bukh_en[src_hn])
                break
    
    # Try Muslim if not found
    if not found_src:
        for i in range(0, max(1, len(norm_ar)-15), 3):
            fp = norm_ar[i:i+20]
            if len(fp) >= 15 and fp in mus_fp:
                src_hn = mus_fp[fp]
                if src_hn in mus_en:
                    found_src = ('muslim', src_hn, mus_en[src_hn])
                    break
    
    if found_src:
        matched += 1
        en_fn = os.path.join(BASE, f'editions/lulu-wal-marjan/translations/en/sections/{ch}.toon')
        with open(en_fn, 'r') as f:
            content = f.read()
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith(f'{hn},') or line.startswith(f'{hn},"'):
                escaped = found_src[2].replace('"', '""')
                new_lines.append(f'{hn},"{escaped}"')
            else:
                new_lines.append(line)
        with open(en_fn, 'w') as f:
            f.write('\n'.join(new_lines))

print(f"New matches: {matched}")

# Final tally
total = matched2 = 0
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/lulu-wal-marjan/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/lulu-wal-marjan/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                total += 1
    with open(os.path.join(BASE, f'editions/lulu-wal-marjan/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if len(p) > 1 and p[1].strip():
                    matched2 += 1

print(f"Final: {matched2}/{total} ({100*matched2//total}%)")
