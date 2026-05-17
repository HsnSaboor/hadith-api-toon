#!/usr/bin/env python3
"""Download Al-Adab Al-Mufrad from al-hadees.com - Arabic, Urdu, takhreej."""
import os, re, json, time
from urllib.request import urlopen, Request
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

BASE = 'editions/aladab-almufrad'
CACHE_FILE = 'scraped_data/aladab_alhadees.json'

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
lock = Lock()

# Load cache
cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE) as f:
        cache = json.load(f)
    print(f"Loaded {len(cache)} cached hadiths")

def fetch_hadith(hnum):
    s = str(hnum)
    if s in cache:
        return s, cache[s]
    
    url = f'https://al-hadees.com/aladab-almufrad/{hnum}'
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        # Extract Arabic
        ar_match = re.search(r'<h4 class="font-arabic2 text-center mb-4">(.*?)</h4>', html, re.DOTALL)
        arabic = ar_match.group(1).strip() if ar_match else ''
        arabic = re.sub(r'<[^>]+>', '', arabic)
        
        # Extract Urdu
        ur_match = re.search(r'<div class="card-body">\s*<div><h4 class="font-urdu">(.*?)</h4>', html, re.DOTALL)
        urdu = ur_match.group(1).strip() if ur_match else ''
        urdu = re.sub(r'<[^>]+>', '', urdu)
        
        # If Urdu not found, try alternative pattern
        if not urdu:
            ur_match = re.search(r'<h4 class="font-urdu">(.*?)</h4>', html, re.DOTALL)
            urdu = ur_match.group(1).strip() if ur_match else ''
            urdu = re.sub(r'<[^>]+>', '', urdu)
        
        # Extract takhreej
        takh_match = re.search(r'تخریج.*?<h3 class="m-0 font-arabic2">(.*?)</h3>', html, re.DOTALL)
        takhreej = takh_match.group(1).strip() if takh_match else ''
        takhreej = re.sub(r'<[^>]+>', '', takhreej)
        if not takhreej:
            takh_match = re.search(r'تخریج الحدیث[^<]*', html)
            takhreej = takh_match.group(0).strip() if takh_match else ''
        
        # Extract grade
        grade = ''
        g_match = re.search(r'Status[^<]*<p[^>]*>[^<]*<span[^>]*>(.*?)</span>', html, re.DOTALL)
        if g_match:
            grade = g_match.group(1).strip()
        if not grade:
            g_match = re.search(r'<span class="text-success">(.*?)</span>', html)
            if g_match:
                grade = g_match.group(1).strip()
        
        # Extract international number
        intl = str(hnum)
        intl_match = re.search(r'International:\s*(\d+)', html)
        if intl_match:
            intl = intl_match.group(1)
        
        result = {
            'arabic': arabic,
            'urdu': urdu,
            'takhreej': takhreej,
            'grade': grade,
            'international': intl
        }
        
        with lock:
            cache[s] = result
            if len(cache) % 50 == 0:
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f, ensure_ascii=False)
        
        return s, result
    except Exception as e:
        return s, None

# Fetch all hadiths
print("Fetching hadiths from al-hadees.com...")
to_fetch = [h for h in range(1, 1330) if str(h) not in cache]
print(f"Need to fetch: {len(to_fetch)} hadiths")

for i in range(0, len(to_fetch), 5):
    batch = to_fetch[i:i+5]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_hadith, h): h for h in batch}
        for future in as_completed(futures):
            pass
    if (i+5) % 100 == 0:
        print(f'  Progress: {min(i+5, len(to_fetch))}/{len(to_fetch)} ({len(cache)} cached)')
    time.sleep(0.3)

# Final save
with open(CACHE_FILE, 'w') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f'\nTotal cached: {len(cache)}')

# Now update the Arabic + Urdu section files
print('\nUpdating section files...')
# Read the current info.toon to get section structure
with open(f'{BASE}/info.toon') as f:
    info = f.read()

# Parse section names and ranges
sec_pattern = re.findall(r'^(\d+),"(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)",(\d+),(\d+)', info, re.MULTILINE)
secs = []
for m in sec_pattern:
    secs.append((int(m[0]), m[1], m[9], int(m[10]), int(m[11])))
secs.sort()

# Clear and rewrite section files
SEC_DIR = f'{BASE}/sections'
UR_DIR = f'{BASE}/translations/ur/sections'

# Delete old files
for d in [SEC_DIR, UR_DIR]:
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

for sid, name_en, name_ur, first, last in secs:
    ar_lines = []
    ur_lines = []
    
    for hnum in range(first, last+1):
        s = str(hnum)
        if s in cache:
            d = cache[s]
            arabic = d.get('arabic', '')
            urdu = d.get('urdu', '')
            grade = d.get('grade', '')
            takhreej = d.get('takhreej', '')
            intl = d.get('international', s)
            
            # Arabic
            ar_lines.append(f'{hnum},{arabic},{grade},{takhreej},{intl},,')
            
            # Urdu
            if urdu:
                ur_lines.append(f'{hnum},"{urdu}"')
            else:
                ur_lines.append(f'{hnum},')
        else:
            ar_lines.append(f'{hnum},,,,,,')
            ur_lines.append(f'{hnum},')
    
    # Write Arabic
    with open(f'{SEC_DIR}/{sid}.toon', 'w') as f:
        f.write(f'hadiths[{len(ar_lines)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
        f.write('\n'.join(ar_lines) + '\n')
    
    # Write Urdu
    with open(f'{UR_DIR}/{sid}.toon', 'w') as f:
        f.write(f'hadiths[{len(ur_lines)}]{{hadithnumber,text}}:\n')
        f.write('\n'.join(ur_lines) + '\n')

# Count totals
ar_total = sum(1 for d in cache.values() if d and d.get('arabic'))
ur_total = sum(1 for d in cache.values() if d and d.get('urdu'))
print(f'Arabic: {ar_total} hadiths')
print(f'Urdu: {ur_total} hadiths')

# Update Urdu sections count in info.toon
ur_sec_count = len(secs)
info = re.sub(r'ur,\d+,translations/ur', f'ur,{ur_sec_count},translations/ur', info)
with open(f'{BASE}/info.toon', 'w') as f:
    f.write(info)

# Update main info.toon
with open('info.toon') as f:
    mc = f.read()
mc = re.sub(
    r'aladab-almufrad,Aladab Almufrad,\d+,"ar,en,ur",editions/aladab-almufrad',
    f'aladab-almufrad,Aladab Almufrad,{ar_total},"ar,en,ur",editions/aladab-almufrad',
    mc
)
with open('info.toon', 'w') as f:
    f.write(mc)

print('\nDone!')
