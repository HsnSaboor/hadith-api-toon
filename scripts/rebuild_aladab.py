#!/usr/bin/env python3
"""Regenerate Aladab section files from cached data."""
import os, json

BASE = 'editions/aladab-almufrad'
SEC = f'{BASE}/sections'
EN_DIR = f'{BASE}/translations/en/sections'
UR_DIR = f'{BASE}/translations/ur/sections'

os.makedirs(SEC, exist_ok=True)
os.makedirs(UR_DIR, exist_ok=True)

# Load cache
with open('scraped_data/aladab_alhadees.json') as f:
    cache = json.load(f)

# Load existing English
en_data = {}
for fn in sorted(os.listdir(EN_DIR), key=lambda x: int(x.split('.')[0])):
    with open(f'{EN_DIR}/{fn}') as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1 and p[1].strip():
                    en_data[p[0].strip()] = p[1].strip()

# Define sections based on sunnah.com book structure for Aladab
# 57 sections with hadith ranges from the original data
sections = [
    (1, 1, 46), (2, 47, 73), (3, 74, 75), (4, 76, 83), (5, 84, 100),
    (6, 101, 128), (7, 129, 142), (8, 143, 155), (9, 156, 211), (10, 212, 220),
    (11, 221, 237), (12, 238, 255), (13, 256, 259), (14, 260, 309), (15, 310, 333),
    (16, 334, 344), (17, 345, 354), (18, 355, 363), (19, 364, 375), (20, 376, 386),
    (21, 387, 398), (22, 399, 416), (23, 417, 420), (24, 421, 443), (25, 444, 463),
    (26, 464, 476), (27, 477, 484), (28, 485, 492), (29, 493, 539), (30, 540, 607),
    (31, 608, 742), (32, 743, 757), (33, 758, 814), (34, 815, 845), (35, 846, 859),
    (36, 860, 878), (37, 879, 891), (38, 892, 910), (39, 911, 922), (40, 923, 955),
    (41, 956, 968), (42, 969, 1054), (43, 1055, 1105), (44, 1106, 1121), (45, 1122, 1140),
    (46, 1141, 1157), (47, 1158, 1179), (48, 1180, 1203), (49, 1204, 1209), (50, 1210, 1236),
    (51, 1237, 1242), (52, 1243, 1248), (53, 1249, 1263), (54, 1264, 1286), (55, 1287, 1309),
    (56, 1310, 1321), (57, 1322, 1329)
]

# Clear and write
for d in [SEC, UR_DIR]:
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

ar_total = ur_total = en_total = 0

for sid, first, last in sections:
    ar_lines = []
    ur_lines = []
    en_lines = []
    
    for hnum in range(first, last+1):
        s = str(hnum)
        
        # Arabic + Urdu from cache
        if s in cache:
            d = cache[s]
            arabic = d.get('arabic', '')
            urdu = d.get('urdu', '')
            grade = d.get('grade', '')
            takhreej = d.get('takhreej', '')
            intl = d.get('international', s)
            
            if arabic:
                ar_lines.append(f'{hnum},{arabic},{grade},{takhreej},{intl},,')
                ar_total += 1
            else:
                ar_lines.append(f'{hnum},,,,,,')
            
            if urdu:
                ur_lines.append(f'{hnum},"{urdu}"')
                ur_total += 1
            else:
                ur_lines.append(f'{hnum},')
        else:
            ar_lines.append(f'{hnum},,,,,,')
            ur_lines.append(f'{hnum},')
        
        # English
        if s in en_data:
            en_lines.append(f'{s},"{en_data[s]}"')
            en_total += 1
        else:
            en_lines.append(f'{s},')
    
    # Write files
    with open(f'{SEC}/{sid}.toon', 'w') as f:
        f.write(f'hadiths[{len(ar_lines)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
        f.write('\n'.join(ar_lines) + '\n')
    
    with open(f'{UR_DIR}/{sid}.toon', 'w') as f:
        f.write(f'hadiths[{len(ur_lines)}]{{hadithnumber,text}}:\n')
        f.write('\n'.join(ur_lines) + '\n')
    
    # English already exists in EN_DIR, but let's make sure it's complete
    with open(f'{EN_DIR}/{sid}.toon', 'w') as f:
        f.write(f'hadiths[{len(en_lines)}]{{hadithnumber,text}}:\n')
        f.write('\n'.join(en_lines) + '\n')

print(f'Arabic: {ar_total}')
print(f'Urdu: {ur_total}')
print(f'English: {en_total}')

# Update info.toon
with open(f'{BASE}/info.toon') as f:
    info = f.read()

import re
info = re.sub(r'en,\d+,translations/en', f'en,{len(sections)},translations/en', info)
info = re.sub(r'ur,\d+,translations/ur', f'ur,{len(sections)},translations/ur', info)
info = re.sub(r'sections\[\d+\]', f'sections[{len(sections)}]', info)

# Update section lines
old_secs = re.findall(r'^\d+,.*,\d+,\d+$', info, re.MULTILINE)
for old in old_secs:
    info = info.replace(old, '')

# Add new section entries
info = info.rstrip()
info += '\n'
for sid, first, last in sections:
    info += f'{sid},"","","","","","","","","",{first},{last}\n'

with open(f'{BASE}/info.toon', 'w') as f:
    f.write(info)

print('\nDone!')
