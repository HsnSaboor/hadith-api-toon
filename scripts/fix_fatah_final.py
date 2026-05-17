#!/usr/bin/env python3
"""Parse Fatah Alrabani Arabic data and restructure properly."""
import os, re

BASE = 'editions/fatah-alrabani'

with open(f'{BASE}/sections/1.toon') as f:
    lines = f.readlines()

# Skip header
data = ''.join(lines[1:])

# Split by triple-comma or comma-number sequences that separate hadiths
# The format is complex. Let me extract hadiths using direct pattern matching on Arabic number markers

# Arabic-Indic digit conversion
ari_map = {'٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9'}
def ari_to_dec(s):
    return ''.join(ari_map.get(c, c) for c in s)

# Find all hadith entries by matching the pattern: 
# . (ARABIC_NUM) . ARABIC_TEXT (SOURCE: NUM)
# The number is in Arabic-Indic digits within parentheses after a period

hadiths = {}
# Pattern: optional separator before, then "۔ (NNN)۔" text "(" source: num ")"
pattern = re.compile(r'[\.\u0600-\u06FF]?\s*\(\s*([٠-٩]+)\s*\)\s*[\.\u0600-\u06FF]?\s*(.*?)(?:\(([^)]+:\s*\d+)\))', re.DOTALL)

for m in pattern.finditer(data):
    ari = m.group(1)
    hnum_str = ari_to_dec(ari)
    arabic = m.group(2).strip()
    source = m.group(3).strip() if m.group(3) else ''
    
    if not hnum_str.isdigit():
        continue
    hnum = int(hnum_str)
    
    # Clean the arabic text
    arabic = re.sub(r'\s+', ' ', arabic).strip()
    # Remove Urdu text that might be mixed in (text after the source reference)
    # The source pattern (Source: Num) marks the end of Arabic
    
    hadiths[hnum] = arabic

print(f"Found {len(hadiths)} Arabic hadiths")
if hadiths:
    nums = sorted(hadiths.keys())
    print(f"Range: {nums[0]}-{nums[-1]}")
    print(f"Sample 104: {hadiths[104][:100]}...")

# Load Urdu
urdu_all = {}
for sn in [2, 3, 1]:  # order: 1-50, 51-103, 104-192
    fpath = f'{BASE}/translations/ur/sections/{sn}.toon'
    if not os.path.exists(fpath):
        continue
    with open(fpath) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',', 1)
                if p[0].strip().isdigit() and len(p) > 1 and p[1].strip():
                    hnum = int(p[0].strip())
                    urdu_all[hnum] = p[1].strip().strip('"')

print(f"Urdu hadiths: {len(urdu_all)}")

# Write restructured files
sections = [
    (1, 1, 50, "ایمان اور اسلام", "Faith and Islam"),
    (2, 51, 103, "عبادات", "Worship"),
    (3, 104, 192, "متفرق احادیث", "Various Hadiths"),
]

SEC_DIR = f'{BASE}/sections'
UR_DIR = f'{BASE}/translations/ur/sections'

for d in [SEC_DIR, UR_DIR]:
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

ar_total = 0
ur_total = 0

for sid, first, last, name_ur, name_en in sections:
    ar_lines = []
    ur_lines = []
    
    for hnum in range(first, last+1):
        if hnum in hadiths:
            ar_lines.append(f'{hnum},{hadiths[hnum]},,,{hnum},,')
            ar_total += 1
        else:
            ar_lines.append(f'{hnum},,,,,,')
        
        if hnum in urdu_all:
            ur_lines.append(f'{hnum},"{urdu_all[hnum]}"')
            ur_total += 1
        else:
            ur_lines.append(f'{hnum},')
    
    with open(f'{SEC_DIR}/{sid}.toon', 'w') as f:
        f.write(f'hadiths[{len(ar_lines)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
        f.write('\n'.join(ar_lines) + '\n')
    
    with open(f'{UR_DIR}/{sid}.toon', 'w') as f:
        f.write(f'hadiths[{len(ur_lines)}]{{hadithnumber,text}}:\n')
        f.write('\n'.join(ur_lines) + '\n')

print(f"\nWritten: Arabic={ar_total}, Urdu={ur_total}")

# Update info.toon
with open(f'{BASE}/info.toon', 'w') as f:
    f.write(f"""
translations[2]{{language,sections,path}}:
en,0,translations/en
ur,3,translations/ur

sections[3]{{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}}:
1,"Faith and Islam","الإيمان والإسلام","Fatah Al-Rabani","Faith and Islam","Fatah Al-Rabbani","Fatah Al-Rabbani","Фатх ар-Раббани","Fetihü'r-Rabbani","ایمان اور اسلام",1,50
2,"Worship","العبادات","Fatah Al-Rabani","Worship","Fatah Al-Rabbani","Fatah Al-Rabbani","Фатх ар-Раббани","Fetihü'r-Rabbani","عبادات",51,103
3,"Various Hadiths","أحاديث متفرقة","Fatah Al-Rabani","Various Hadiths","Fatah Al-Rabbani","Fatah Al-Rabbani","Фатх ар-Раббани","Fetihü'r-Rabbani","متفرق احادیث",104,192
""".strip() + '\n')

# Update main info.toon
import re
with open('info.toon') as f:
    mc = f.read()
mc = re.sub(
    r'fatah-alrabani,Fatah Alrabani,\d+,"ar,en,ur",editions/fatah-alrabani',
    f'fatah-alrabani,Fatah Alrabani,{ar_total},"ar,en,ur",editions/fatah-alrabani',
    mc
)
with open('info.toon', 'w') as f:
    f.write(mc)

# Update Urdu metadata
with open(f'{BASE}/translations/ur/metadata.toon', 'w') as f:
    f.write(f"""metadata:
  language: ur
  language_name: "Urdu"
  script: "Arabic"
  total_hadiths: {ur_total}
  source: "Restructured from original data"
""")

print("Done!")
