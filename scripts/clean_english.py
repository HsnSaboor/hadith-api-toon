#!/usr/bin/env python3
"""Clean and merge English translations for lulu-wal-marjan.
Uses clean Bukhari/Muslim English where available, cleans PDF OCR for rest."""
import os, re, json

BASE = os.path.dirname(os.path.dirname(__file__))

def clean_pdf_text(text):
    """Aggressively clean OCR artifacts from PDF English text."""
    # Remove hadith number prefix like "1. Narrated X: " or "5. Narrated X:"
    text = re.sub(r'^\d+\.\s*Narrated\s+[^:]+:\s*', '', text)
    # Also match "Narrated X ;" variants
    text = re.sub(r'^\d+\.\s*Narrated\s+[^:]+?;\s*', '', text)
    
    # Remove Arabic script fragments (sequences of isolated Arabic chars)
    text = re.sub(r'[\u0600-\u06FF]{2,}', '', text)
    
    # Remove chapter heading artifacts
    text = re.sub(r'(?i)(\d+\.\s*)?(THE\s+BOOK\s+OF|CHAPTER\s+\d+|THE\s+BOOK\s+ABOUT)[^.]*\.?\s*', '', text)
    text = re.sub(r'(?i)(tne|the|tte|tnr)\s+(nooX|nook|hoot|boox|boot|book|b00k|gook)\s+of\s+[a-z]+\s*', '', text)
    text = re.sub(r'(?i)(tne|the|tte|tnr)\s+(nooX|nook|hoot|boox|boot|book|b00k|gook)\s+or[^\s]*\s*', '', text)
    
    # Remove parenthetical Sahih references
    text = re.sub(r'\(Sah[hi]+[^)]*\)', '', text)
    text = re.sub(r'\(Sahth[^)]*\)', '', text)
    text = re.sub(r'\(Sahfh[^)]*\)', '', text)
    text = re.sub(r'\(Hadtth[^)]*\)', '', text)
    text = re.sub(r'\(Hadith[^)]*\)', '', text)
    
    # Remove page artifacts like standalone numbers
    text = re.sub(r'\b\d{3,4}\b', '', text)  # 3-4 digit numbers alone
    
    # Fix common OCR word corruptions
    replacements = {
        'All0h': 'Allah', 'All6h': 'Allah', 'All6': 'Allah',
        'A[ah': 'Allah', 'Alah': 'Allah', 'Alldh': 'Allah',
        'Isl6m': 'Islam', 'Isl6': 'Islam', 'IslAm': 'Islam',
        'Islffm': 'Islam', 'lslam': 'Islam',
        "Qur'6n": "Qur'an", "Qur'6": "Qur'an",
        'Ahddfth': 'Hadith', 'Hadtth': 'Hadith', 'Ahddith': 'Ahadith',
        'Abt': 'Abu', 'Ab0': 'Abu', 'Abf': 'Abu', 'AbD': 'Abu',
        'Messengl': 'Messenger', 'Messengel': 'Messenger',
        'Prophe': 'Prophet', 'Proph et': 'Prophet',
        'suerly': 'surely', 'su rely': 'surely',
        'li ': 'lie ', 'a li': 'a lie', 'tel ': 'tell ',
        'wi ': 'will ', 'entthe': 'enter the',
        'whoevtells': 'whoever tells', 'whoevtel': 'whoever tells',
        'whoeve': 'whoever',
        'ocupy': 'occupy', 'ocu y': 'occupy',
        'Hel': 'Hell', 'hel': 'hell',
        'ffi€': '', 'ffi': '',
        'gre a': 'great', 'grea': 'great',
        'numbof': 'number of', 'numbe ': 'number ',
        'numb': 'number',
        'th Prophet': 'the Prophet',
        'Th Prophet': 'The Prophet',
        'All6h\'s': "Allah's",
        'a[1l': 'all',
        'o ': 'of ',
        'o\' ': 'of ',
        'o,f ': 'of ',
        'o. ': '',
        'th e': 'the',
        'th eir': 'their',
        'thi ': 'this ',
        'tha ': 'that ',
        'an ': 'and ',
        'an d': 'and',
        'an,': 'and',
        'ar ': 'are ',
        'o\'r': 'or',
        'o u ': 'our ',
        'o u r': 'our',
        'yo u ': 'you ',
        'u ': ' ',
        ',r,': '',
        ' a ': ' a ',
        'r ': ' ',
        ', ': ', ',
    }
    # Sort by length (longest first) to avoid partial replacements
    for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    
    # Fix remaining "h" at start of words (OCR artifact)
    text = re.sub(r'\bh e\b', 'the', text)
    text = re.sub(r'\bh im\b', 'him', text)
    text = re.sub(r'\bh is\b', 'his', text)
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove leading/trailing punctuation
    text = text.strip('.,;:!?-"\' ')
    
    return text

# Load current PDF English sections
print("Loading current English sections (from PDF)...")
pdf_english = {}
en_dir = os.path.join(BASE, "editions", "lulu-wal-marjan", "translations", "en", "sections")
for fn in sorted(os.listdir(en_dir), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(en_dir, fn)) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                parts = line.split(',', 1)
                if parts[0].strip().isdigit() and len(parts) > 1 and parts[1].strip():
                    hnum = parts[0].strip()
                    text = parts[1].strip().strip('"')
                    pdf_english[hnum] = text

print(f"  {len(pdf_english)} hadiths loaded")

# Clean all PDF text
print("Cleaning OCR text...")
for hnum in pdf_english:
    pdf_english[hnum] = clean_pdf_text(pdf_english[hnum])

# Now rebuild Bukhari/Muslim clean English
print("Building clean Bukhari/Muslim English index...")
def normalize(t):
    return re.sub(r'\s+', ' ', re.sub(r'[^\u0621-\u064A\s]', '', t)).strip()

def extract_core(t):
    n = normalize(t)
    for p in [r'قال\s*(?:رسول\s+الله|النبي)\s*[^:]*:(.*)', r'قال\s*(?:رسول\s+الله|النبي)\s*(.*)']:
        m = re.search(p, n)
        if m and len(m.group(1).strip()) > 15:
            return m.group(1).strip()
    return n

# Build Bukhari fingerprints
bukh_fp = {}
bukh_en = {}
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/bukhari/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/bukhari/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit():
                    c = extract_core(p[1]) if len(p) > 1 else ''
                    if len(c) > 30:
                        for i in range(0, len(c)-35, 15):
                            bukh_fp[c[i:i+35]] = p[0].strip()
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/bukhari/translations/en/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/bukhari/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1 and p[1].strip():
                    bukh_en[p[0].strip()] = p[1].strip()

mus_fp = {}
mus_en = {}
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/muslim/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/muslim/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit():
                    c = extract_core(p[1]) if len(p) > 1 else ''
                    if len(c) > 30:
                        for i in range(0, len(c)-35, 15):
                            mus_fp[c[i:i+35]] = p[0].strip()
for fn in sorted(os.listdir(os.path.join(BASE, 'editions/muslim/translations/en/sections')), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(BASE, f'editions/muslim/translations/en/sections/{fn}')) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1 and p[1].strip():
                    mus_en[p[0].strip()] = p[1].strip()

# Load lulu Arabic for matching
with open(os.path.join(BASE, 'scraped_data/lulu-wal-marjan_full.json')) as f:
    lulu = json.load(f)

# Match to clean English
clean_en = {}
for hn_s in pdf_english:
    if hn_s not in lulu:
        continue
    ar = lulu[hn_s].get('arabic', '')
    core = extract_core(ar)
    if core and len(core) > 35:
        for i in range(0, len(core)-35, 10):
            fp = core[i:i+35]
            if fp in bukh_fp and bukh_fp[fp] in bukh_en:
                clean_en[hn_s] = bukh_en[bukh_fp[fp]]
                break
            if fp in mus_fp and mus_fp[fp] in mus_en:
                clean_en[hn_s] = mus_en[mus_fp[fp]]
                break

print(f"  Clean Bukhari/Muslim matches: {len(clean_en)}")

# Merge: prefer clean, fall back to cleaned PDF
merged = {}
for hn_s in pdf_english:
    if hn_s in clean_en:
        merged[hn_s] = clean_en[hn_s]
    else:
        t = pdf_english[hn_s]
        if len(t) > 15:
            merged[hn_s] = t

print(f"  Merged total: {len(merged)}")

# Write final sections
sections_dir = os.path.join(BASE, "editions", "lulu-wal-marjan", "sections")
en_dir = os.path.join(BASE, "editions", "lulu-wal-marjan", "translations", "en", "sections")
os.makedirs(en_dir, exist_ok=True)
for f in os.listdir(en_dir):
    os.remove(os.path.join(en_dir, f))

total = matched = 0
for fn in sorted(os.listdir(sections_dir), key=lambda x: int(x.split('.')[0])):
    ch = int(fn.split('.')[0])
    nums = []
    with open(os.path.join(sections_dir, fn)) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit():
                    nums.append(p[0].strip())
    entries = []
    cm = 0
    for n in nums:
        total += 1
        if n in merged:
            entries.append((n, merged[n]))
            cm += 1
            matched += 1
        else:
            entries.append((n, ''))
    with open(os.path.join(en_dir, f'{ch}.toon'), 'w') as f:
        f.write(f'hadiths[{len(entries)}]{{hadithnumber,text}}:\n')
        for n, t in entries:
            if t:
                f.write(f'{n},"{t}"\n')
            else:
                f.write(f'{n},\n')
    print(f'  Ch {ch}: {cm}/{len(nums)}')

print(f'\nFinal: {matched}/{total} ({100*matched//total}%)')
