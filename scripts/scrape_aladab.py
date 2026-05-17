#!/usr/bin/env python3
"""Scrape Al-Adab Al-Mufrad from sunnah.com (Arabic+English) and al-hadees.com (Urdu+takhreej)."""
import os, re, json, time
from urllib.request import urlopen, Request
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

BASE = 'editions/aladab-almufrad'
SEC = f'{BASE}/sections'
EN_DIR = f'{BASE}/translations/en/sections'
UR_DIR = f'{BASE}/translations/ur/sections'

os.makedirs(SEC, exist_ok=True)
os.makedirs(EN_DIR, exist_ok=True)
os.makedirs(UR_DIR, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0'}
CACHE = {}
CACHE_FILE = 'scraped_data/aladab_cache.json'
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE) as f:
        CACHE = json.load(f)

lock = Lock()

def fetch_sunnah_book(book_num):
    """Fetch a single book page from sunnah.com and extract hadiths."""
    url = f'https://sunnah.com/adab/{book_num}'
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        hadiths = []
        # Each hadith block starts with <a name=N>
        blocks = re.findall(r'<a name=(\d+)>(.*?)<div class=clear></div></div><!-- end actual hadith container -->', html, re.DOTALL)
        
        for hnum, block in blocks:
            # Extract English
            en_match = re.search(r'<div class="english_hadith_full">.*?<div class=text_details>(.*?)</b></div>', block, re.DOTALL)
            en_text = en_match.group(1).strip() if en_match else ''
            en_text = re.sub(r'<[^>]+>', '', en_text)  # Strip HTML
            en_text = en_text.replace('&quot;', '"').replace('&#039;', "'").replace('&amp;', '&')
            
            # Extract Arabic
            ar_match = re.search(r'<span class="arabic_text_details arabic">(.*?)</span>', block, re.DOTALL)
            ar_text = ar_match.group(1).strip() if ar_match else ''
            ar_text = re.sub(r'<[^>]+>', '', ar_text)
            
            hadiths.append((hnum, ar_text, en_text))
        
        return book_num, hadiths
    except Exception as e:
        print(f'  Book {book_num} error: {e}')
        return book_num, []

def fetch_alhadees(hnum):
    """Fetch Urdu and takhreej from al-hadees.com."""
    if hnum in CACHE:
        return hnum, CACHE[hnum]
    
    url = f'https://al-hadees.com/aladab-almufrad/{hnum}'
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        # Extract Urdu
        ur_match = re.search(r'<div class="card-body">\s*<div><h4 class="font-urdu">(.*?)</h4>', html, re.DOTALL)
        ur_text = ur_match.group(1).strip() if ur_match else ''
        ur_text = re.sub(r'<[^>]+>', '', ur_text)
        
        # Extract takhreej
        takh_match = re.search(r'Conclusion.*?<h3 class="m-0 font-arabic2">(.*?)</h3>', html, re.DOTALL)
        takhreej = takh_match.group(1).strip() if takh_match else ''
        
        # Extract grade
        grade = 'Sahih'
        if 'Sahih' in html:
            grade = 'Sahih'
        
        result = {'urdu': ur_text, 'takhreej': takhreej, 'grade': grade}
        
        with lock:
            CACHE[hnum] = result
            with open(CACHE_FILE, 'w') as f:
                json.dump(CACHE, f)
        
        return hnum, result
    except Exception as e:
        return hnum, {'urdu': '', 'takhreej': '', 'grade': ''}

# Step 1: Scrape sunnah.com books
print("Step 1: Scraping sunnah.com...")
all_hadiths = {}  # hnum -> (ar, en)
book_ranges = []  # (book_num, first_hnum, last_hnum)

# Sunnah.com has 51 books for Al-Adab Al-Mufrad
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(fetch_sunnah_book, bn): bn for bn in range(1, 52)}
    for future in as_completed(futures):
        bn, hadiths = future.result()
        if hadiths:
            first = int(hadiths[0][0])
            last = int(hadiths[-1][0])
            book_ranges.append((bn, first, last))
            for hnum, ar, en in hadiths:
                all_hadiths[hnum] = (ar, en)
            print(f'  Book {bn}: {len(hadiths)} hadiths ({first}-{last})')

print(f'\nTotal hadiths from sunnah.com: {len(all_hadiths)}')

# Step 2: Scrape al-hadees.com for Urdu
print('\nStep 2: Scraping al-hadees.com for Urdu...')
cache_misses = [h for h in all_hadiths if h not in CACHE]
print(f'  Need to fetch: {len(cache_misses)} hadiths')

for i in range(0, len(cache_misses), 5):
    batch = cache_misses[i:i+5]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_alhadees, h): h for h in batch}
        for future in as_completed(futures):
            pass
    if (i+5) % 50 == 0:
        print(f'  Progress: {min(i+5, len(cache_misses))}/{len(cache_misses)}')
    time.sleep(0.3)

print(f'  Cached: {len(CACHE)} hadiths')

# Step 3: Write section files
print('\nStep 3: Writing section files...')

# Clear old files
for d in [SEC, EN_DIR, UR_DIR]:
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

# Write each book as a section
for bn, first, last in sorted(book_ranges, key=lambda x: x[0]):
    hadiths_in_book = [(h, all_hadiths[h]) for h in range(first, last+1) if h in all_hadiths]
    
    ar_lines = []
    en_lines = []
    ur_lines = []
    
    for hnum, (ar, en) in hadiths_in_book:
        ur_data = CACHE.get(hnum, {})
        ur_text = ur_data.get('urdu', '')
        takhreej = ur_data.get('takhreej', '')
        grade = ur_data.get('grade', '')
        intl = hnum
        
        # Arabic
        if ar:
            ar_lines.append(f'{hnum},{ar},{grade},{takhreej},{intl},,')
        else:
            ar_lines.append(f'{hnum},,,,,,')
        
        # English
        if en:
            en_lines.append(f'{hnum},"{en}"')
        else:
            en_lines.append(f'{hnum},')
        
        # Urdu
        if ur_text:
            ur_lines.append(f'{hnum},"{ur_text}"')
        else:
            ur_lines.append(f'{hnum},')
    
    # Write Arabic
    with open(f'{SEC}/{bn}.toon', 'w') as f:
        f.write(f'hadiths[{len(ar_lines)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
        f.write('\n'.join(ar_lines) + '\n')
    
    # Write English
    with open(f'{EN_DIR}/{bn}.toon', 'w') as f:
        f.write(f'hadiths[{len(en_lines)}]{{hadithnumber,text}}:\n')
        f.write('\n'.join(en_lines) + '\n')
    
    # Write Urdu
    with open(f'{UR_DIR}/{bn}.toon', 'w') as f:
        f.write(f'hadiths[{len(ur_lines)}]{{hadithnumber,text}}:\n')
        f.write('\n'.join(ur_lines) + '\n')
    
    print(f'  Book {bn}: {len(hadiths_in_book)} hadiths')

print('\nStep 4: Updating info.toon...')
# Write info.toon with proper sections
# Use existing chapter names from current data
with open(f'{BASE}/info.toon') as f:
    current_info = f.read()

# Extract section names from current info
sec_names = {}
sec_pattern = re.findall(r'^(\d+),"(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)",\d+,\d+', current_info, re.MULTILINE)
for m in sec_pattern:
    sid = int(m[0])
    sec_names[sid] = {
        'name_en': m[1], 'name_ar': m[2], 'name_bn': m[3],
        'name_fr': m[5], 'name_id': m[6], 'name_ru': m[7], 'name_tr': m[8], 'name_ur': m[9]
    }

# Build new info
num_secs = len(book_ranges)
lines = [
    '',
    'translations[3]{language,sections,path}:',
    f'en,{num_secs},translations/en',
    f'ur,{num_secs},translations/ur',
    '',
    f'sections[{num_secs}]{{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}}:',
]
for bn, first, last in sorted(book_ranges, key=lambda x: x[0]):
    names = sec_names.get(bn, {})
    lines.append(f'{bn},"{names.get("name_en","")}","{names.get("name_ar","")}","{names.get("name_bn","")}","{names.get("name_en","")}","{names.get("name_fr","")}","{names.get("name_id","")}","{names.get("name_ru","")}","{names.get("name_tr","")}","{names.get("name_ur","")}",{first},{last}')

with open(f'{BASE}/info.toon', 'w') as f:
    f.write('\n'.join(lines) + '\n')

# Update main info.toon total
with open('info.toon') as f:
    mc = f.read()
mc = re.sub(
    r'aladab-almufrad,Aladab Almufrad,\d+,"ar,en,ur",editions/aladab-almufrad',
    f'aladab-almufrad,Aladab Almufrad,{len(all_hadiths)},"ar,en,ur",editions/aladab-almufrad',
    mc
)
with open('info.toon', 'w') as f:
    f.write(mc)

print(f'\nDone! Total: {len(all_hadiths)} hadiths across {len(book_ranges)} sections')
