#!/usr/bin/env python3
"""Build English translations for lulu-wal-marjan from Bukhari AND Muslim English data."""
import os, re, json

BASE = os.path.dirname(os.path.dirname(__file__))

def normalize(text):
    text = re.sub(r'[^\u0621-\u064A\s]', '', text)
    text = text.replace('\u0649', '\u064A')  # alif maqsura -> yeh
    text = text.replace('\u0626', '\u0625')  # hamza
    text = text.replace('\u0623', '\u0627')  # hamza above alif -> alif
    text = text.replace('\u0625', '\u0627')  # hamza below alif -> alif
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_prophetic_saying(text):
    norm = normalize(text)
    patterns = [
        r'قال\s*(?:رسول\s+الله|النبي)\s*[^:]*:(.*)',
        r'قال\s*(?:رسول\s+الله|النبي)\s*(.*)',
        r'يقول\s*(?:رسول\s+الله|النبي)\s*(.*)',
        r'أن\s+(?:رسول\s+الله|النبي)\s*قال\s*(.*)',
        r'سمعت\s+(?:رسول\s+الله|النبي)\s*(?:يقول)?\s*(.*)',
    ]
    for pat in patterns:
        m = re.search(pat, norm)
        if m:
            content = m.group(1).strip()
            if len(content) > 15:
                return content
    return norm

def index_book(arabic_dir, english_dir):
    """Index a book's Arabic and English data."""
    prophetic = {}  # prophetic saying -> hadith number
    english = {}    # hadith number -> english text
    
    # Build Arabic index
    for fn in sorted(os.listdir(arabic_dir), key=lambda x: int(x.split('.')[0])):
        with open(os.path.join(arabic_dir, fn), encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('hadiths['):
                    p = line.split(',', 1)
                    if p[0].strip().isdigit():
                        hnum = p[0].strip()
                        arabic = p[1].strip() if len(p) > 1 else ''
                        if arabic:
                            core = extract_prophetic_saying(arabic)
                            if len(core) > 30:
                                prophetic[core] = hnum
    
    # Build English index
    for fn in sorted(os.listdir(english_dir), key=lambda x: int(x.split('.')[0])):
        with open(os.path.join(english_dir, fn), encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('hadiths['):
                    p = line.split(',', 1)
                    if p[0].strip().isdigit():
                        english[p[0].strip()] = p[1].strip() if len(p) > 1 else ''
    
    return prophetic, english

print("Indexing Bukhari...")
bukh_prophetic, bukh_english = index_book('editions/bukhari/sections', 'editions/bukhari/translations/en/sections')

print("Indexing Muslim...")
muslim_prophetic, muslim_english = index_book('editions/muslim/sections', 'editions/muslim/translations/en/sections')

print(f"  Bukhari: {len(bukh_prophetic)} prophetic sayings, {len(bukh_english)} English")
print(f"  Muslim: {len(muslim_prophetic)} prophetic sayings, {len(muslim_english)} English")

# Build fingerprint index from both books
fingerprints = {}  # fp -> (source, hadith_number)
for core, hnum in bukh_prophetic.items():
    for i in range(0, len(core) - 40, 15):
        fp = core[i:i+40]
        if fp not in fingerprints:
            fingerprints[fp] = ('bukhari', hnum)
for core, hnum in muslim_prophetic.items():
    for i in range(0, len(core) - 40, 15):
        fp = core[i:i+40]
        if fp not in fingerprints:
            fingerprints[fp] = ('muslim', hnum)

print(f"  Combined fingerprints: {len(fingerprints)}")

# Load lulu data
with open('scraped_data/lulu-wal-marjan_full.json', encoding='utf-8') as f:
    lulu_data = json.load(f)

SECTIONS_DIR = os.path.join(BASE, "editions", "lulu-wal-marjan", "sections")
EN_SECTIONS_DIR = os.path.join(BASE, "editions", "lulu-wal-marjan", "translations", "en", "sections")
os.makedirs(EN_SECTIONS_DIR, exist_ok=True)

for f in os.listdir(EN_SECTIONS_DIR):
    os.remove(os.path.join(EN_SECTIONS_DIR, f))

total = matched = bukhari_from = muslim_from = 0

for fname in sorted(os.listdir(SECTIONS_DIR), key=lambda x: int(x.split('.')[0])):
    ch_id = int(fname.split('.')[0])
    fpath = os.path.join(SECTIONS_DIR, fname)
    
    ch_hadiths = []
    with open(fpath, encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit():
                    ch_hadiths.append((p[0].strip(), p[1].strip() if len(p) > 1 else ''))
    
    ch_matched = 0
    ch_entries = []
    
    for hnum, arabic in ch_hadiths:
        total += 1
        lulu_core = extract_prophetic_saying(arabic)
        
        found_en = ""
        source = ""
        if lulu_core and len(lulu_core) > 40:
            # Try matching with fingerprints
            for i in range(0, len(lulu_core) - 40, 10):
                fp = lulu_core[i:i+40]
                if fp in fingerprints:
                    src, bhnum = fingerprints[fp]
                    if src == 'bukhari' and bhnum in bukh_english:
                        found_en = bukh_english[bhnum]
                        source = 'bukhari'
                    elif src == 'muslim' and bhnum in muslim_english:
                        found_en = muslim_english[bhnum]
                        source = 'muslim'
                    if found_en:
                        break
        
        if found_en:
            ch_entries.append((hnum, found_en))
            matched += 1
            ch_matched += 1
            if source == 'bukhari':
                bukhari_from += 1
            else:
                muslim_from += 1
        else:
            ch_entries.append((hnum, ""))
    
    outf = os.path.join(EN_SECTIONS_DIR, f"{ch_id}.toon")
    with open(outf, 'w', encoding='utf-8') as f:
        f.write(f"hadiths[{len(ch_entries)}]{{hadithnumber,text}}:\n")
        for hnum, en_text in ch_entries:
            if en_text:
                escaped = en_text.replace('"', '""')
                f.write(f'{hnum},"{escaped}"\n')
            else:
                f.write(f'{hnum},\n')
    
    print(f"  Ch {ch_id}: {ch_matched}/{len(ch_entries)}")

print(f"\nTotal: {matched}/{total} ({100*matched//total}%)")
print(f"  From Bukhari: {bukhari_from}")
print(f"  From Muslim: {muslim_from}")
