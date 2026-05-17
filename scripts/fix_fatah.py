#!/usr/bin/env python3
"""Fix Fatah Alrabani - same inline CSV format issue as Mustadrak."""
import os, re, csv
from io import StringIO

ed = 'editions/fatah-alrabani'
sec = f'{ed}/sections'

for fn in sorted(os.listdir(sec), key=lambda x: int(x.split('.')[0])):
    fpath = f'{sec}/{fn}'
    with open(fpath) as f:
        content = f.read()
    
    idx = content.find('}: ')
    if idx < 0:
        print(f'{fn}: no header separator')
        continue
    
    header = content[:idx]
    data = content[idx+3:]
    
    # Parse section id
    sid = int(fn.split('.')[0])
    
    # Convert inline records to separate lines
    data_with_nl = re.sub(r'",,,', r'",,,\n', data)
    
    reader = csv.reader(StringIO(data_with_nl))
    rows = []
    for row in reader:
        if row and row[0].strip().isdigit():
            rows.append(row)
    
    if not rows:
        print(f'{fn}: no rows')
        continue
    
    first = int(rows[0][0])
    last = int(rows[-1][0])
    count = len(rows)
    
    new_lines = [f'hadiths[{count}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:']
    for row in rows:
        while len(row) < 7:
            row.append('')
        new_lines.append(','.join(row))
    
    with open(fpath, 'w') as f:
        f.write('\n'.join(new_lines) + '\n')
    
    print(f'{fn}: {count} hadiths ({first}-{last})')

# Fix info.toon
with open(f'{ed}/info.toon') as f:
    content = f.read()

ar_count = count  # from last loop
sections_line = f'sections[1]{{...}}: 1,...,{first},{last}'
# Simple replace
import re
content_updated = re.sub(r'sections\[\d+\]{.*}:.*', f'sections[1]{{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}}: 1,"Fatah Al-Rabani","فتح الربانی","Fatah Al-Rabani","Fatah Al-Rabani","Fatah Al-Rabani","Fatah Al-Rabani","Фатх аль-Рабани","Fethu\'r-Rabbani","فتح الربانی",{first},{last}', content)

with open(f'{ed}/info.toon', 'w') as f:
    f.write(content_updated)

# Update main info.toon
with open('info.toon') as f:
    mc = f.read()
mc = re.sub(
    r'fatah-alrabani,Fatah Alrabani,\d+,"ar,en,ur",editions/fatah-alrabani',
    f'fatah-alrabani,Fatah Alrabani,{count},"ar,en,ur",editions/fatah-alrabani',
    mc
)
with open('info.toon', 'w') as f:
    f.write(mc)

print(f'\nUpdated: {count} Arabic hadiths')
