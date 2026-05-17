#!/usr/bin/env python3
"""Fix Aladab: split inline first hadith, fix JSON translations."""
import os, re, ast, csv
from io import StringIO

BASE = 'editions/aladab-almufrad'

# Fix all section files
print("=== Fixing Arabic sections ===")
ar_total = 0
sec_info = []

for fn in sorted(os.listdir(f'{BASE}/sections'), key=lambda x: int(x.split('.')[0])):
    fpath = f'{BASE}/sections/{fn}'
    with open(fpath) as f:
        content = f.read()
    
    # Split at '}: '
    m = re.match(r'(hadiths\[\w+\]\{[^}]+\}:\s*)(.*)', content, re.DOTALL)
    if not m:
        continue
    
    header = m.group(1)
    rest = m.group(2)
    
    # Add newline after header
    rest_with_nl = rest.replace(',,,', ',,,\n')
    
    # Parse
    reader = csv.reader(StringIO(rest_with_nl))
    rows = []
    for row in reader:
        if row and row[0].strip().isdigit():
            rows.append(row)
    
    if not rows:
        continue
    
    # Fix header count
    count = len(rows)
    new_header = re.sub(r'hadiths\[\w+\]', f'hadiths[{count}]', header)
    
    lines = [new_header]
    for row in rows:
        while len(row) < 7:
            row.append('')
        lines.append(','.join(row))
    
    with open(fpath, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    
    first = int(rows[0][0])
    last = int(rows[-1][0])
    ar_total += count
    sec_info.append((int(fn.split('.')[0]), first, last, count))
    print(f'  Section {fn[:-5]}: {count} hadiths ({first}-{last})')

print(f'\n=== Fixing English translations ===')
en_total = 0
for fn in sorted(os.listdir(f'{BASE}/translations/en/sections'), key=lambda x: int(x.split('.')[0])):
    fpath = f'{BASE}/translations/en/sections/{fn}'
    with open(fpath) as f:
        raw = f.read()
    
    entries = []
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            d = ast.literal_eval(line)
            if isinstance(d, dict) and 'hadithnumber' in d:
                entries.append((d['hadithnumber'], d.get('text', '')))
        except:
            pass
    
    if not entries:
        continue
    
    en_total += len(entries)
    lines = [f'hadiths[{len(entries)}]{{hadithnumber,text}}:']
    for hn, txt in entries:
        lines.append(f'{hn},"{txt.replace(chr(34), chr(34)+chr(34))}"')
    
    with open(fpath, 'w') as f:
        f.write('\n'.join(lines) + '\n')

print(f'  Total English: {en_total}')

print(f'\n=== Fixing Urdu translations ===')
ur_total = 0
for fn in sorted(os.listdir(f'{BASE}/translations/ur/sections'), key=lambda x: int(x.split('.')[0])):
    fpath = f'{BASE}/translations/ur/sections/{fn}'
    with open(fpath) as f:
        raw = f.read()
    
    entries = []
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            d = ast.literal_eval(line)
            if isinstance(d, dict) and 'hadithnumber' in d:
                entries.append((d['hadithnumber'], d.get('text', '')))
        except:
            pass
    
    if not entries:
        continue
    
    ur_total += len(entries)
    lines = [f'hadiths[{len(entries)}]{{hadithnumber,text}}:']
    for hn, txt in entries:
        lines.append(f'{hn},"{txt.replace(chr(34), chr(34)+chr(34))}"')
    
    with open(fpath, 'w') as f:
        f.write('\n'.join(lines) + '\n')

print(f'  Total Urdu: {ur_total}')

print(f'\n=== Updating info.toon ===')
# Count sections
en_sections = len([f for f in os.listdir(f'{BASE}/translations/en/sections') if f.endswith('.toon')])
ur_sections = len([f for f in os.listdir(f'{BASE}/translations/ur/sections') if f.endswith('.toon')])

with open(f'{BASE}/info.toon') as f:
    content = f.read()

content = re.sub(r'en,\d+,translations/en', f'en,{en_sections},translations/en', content)
content = re.sub(r'ur,\d+,translations/ur', f'ur,{ur_sections},translations/ur', content)

with open(f'{BASE}/info.toon', 'w') as f:
    f.write(content)

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

print(f'Final: Arabic={ar_total}, English={en_total}, Urdu={ur_total}')
print(f'Sections: {len(sec_info)} Arabic, {en_sections} English, {ur_sections} Urdu')
