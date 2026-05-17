#!/usr/bin/env python3
"""Fix Mustadrak - parse the inline CSV format into proper multi-line section files."""
import os, re, csv
from io import StringIO

ED = 'editions/mustadrak'
SEC = f'{ED}/sections'

total_all = 0
sections_info = []

for fn in sorted(os.listdir(SEC), key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 0):
    fpath = f'{SEC}/{fn}'
    with open(fpath) as f:
        content = f.read()
    
    # Split at '}: '
    idx = content.find('}: ')
    if idx < 0:
        print(f'{fn}: Cannot find header-data separator')
        continue
    
    header = content[:idx]
    data = content[idx+3:]
    
    # Parse header to get section id
    sid = int(fn.split('.')[0])
    
    # The data is a single line with CSV records. Parse with csv reader.
    # But csv.reader expects newlines. So we add a newline after each record.
    # The pattern is: NUMBER,"TEXT",fields,...,LAST_NUMBER
    # Records are separated by the pattern: ",,,NUMBER
    # Replace '",,,' with '",,,\n' to split records
    data_with_nl = re.sub(r'",,,(\d+)', r'",,,\1\n', data)
    
    # Now parse with CSV
    reader = csv.reader(StringIO(data_with_nl))
    rows = []
    for row in reader:
        if row and row[0].strip().isdigit():
            rows.append(row)
    
    if not rows:
        print(f'{fn}: No rows parsed')
        continue
    
    # Verify hadith numbers
    first = int(rows[0][0])
    last = int(rows[-1][0])
    count = len(rows)
    total_all += count
    
    # Write properly formatted file
    new_lines = [f'hadiths[{count}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:']
    for row in rows:
        # Pad to 7 fields
        while len(row) < 7:
            row.append('')
        new_lines.append(','.join(row))
    
    with open(fpath, 'w') as f:
        f.write('\n'.join(new_lines) + '\n')
    
    sections_info.append((sid, first, last, count))
    print(f'{fn}: {count} hadiths ({first}-{last})')

# Update info.toon
if sections_info:
    sections_info.sort(key=lambda x: x[0])
    
    lines = [
        "",
        "translations[2]{language,sections,path}:",
        "en,52,translations/en",
        "ur,52,translations/ur",
        "",
        f"sections[{len(sections_info)}]{{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}}:",
    ]
    for sid, first, last, count in sections_info:
        lines.append(f'{sid},"Al-Mustadrak","المستدرک علی الصحیحین","Al-Mustadrak","Al-Mustadrak","Al-Mustadrak","Al-Mustadrak","Аль-Мустадрак","El-Müstedrek","المستدرک علی الصحیحین",{first},{last}')
    
    with open(f'{ED}/info.toon', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    
    # Update main info.toon
    main_path = 'info.toon'
    with open(main_path) as f:
        mc = f.read()
    mc = re.sub(
        r'mustadrak,Mustadrak,\d+,"ar,en,ur",editions/mustadrak',
        f'mustadrak,Mustadrak,{total_all},"ar,en,ur",editions/mustadrak',
        mc
    )
    with open(main_path, 'w') as f:
        f.write(mc)
    
    print(f'\nTotal: {total_all} hadiths across {len(sections_info)} sections')
    print('Updated info.toon files')
