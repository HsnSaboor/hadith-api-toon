import csv
import io
import os
import glob
import re

SECTIONS_DIR = 'editions/muajam-tabarani-saghir/sections'

def has_arabic(text):
    for c in text:
        if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F' or '\u08A0' <= c <= '\u08FF':
            return True
    return False

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.strip():
        return 0

    header_end = content.index('}: ')
    data = content[header_end + 3:]

    all_fields = next(csv.reader(io.StringIO(data)))

    if not all_fields:
        return 0

    numeric_indices = [
        i for i, f in enumerate(all_fields)
        if re.match(r'^\d+(?:\s+\d+)?$', f.strip())
    ]

    if len(numeric_indices) < 2:
        return 0

    records = []
    for i in range(len(numeric_indices) - 1):
        start = numeric_indices[i]
        end = numeric_indices[i + 1]

        if i == 0:
            hadith = all_fields[start]
            interior = all_fields[start + 1:end]
        else:
            prev_merged = all_fields[start].strip().split()
            hadith = prev_merged[1] if len(prev_merged) > 1 else ''
            interior = all_fields[start + 1:end]

        merged = all_fields[end].strip().split()
        chapter = merged[0]

        arabic = interior[0] if len(interior) > 0 else ''
        grades = interior[1] if len(interior) > 1 else ''
        ref = interior[2] if len(interior) > 2 else ''
        intl = interior[3] if len(interior) > 3 else ''

        records.append([hadith, arabic, grades, ref, intl, '', chapter])

    valid = [r for r in records
             if r[0].strip().isdigit()
             and len(r[1]) > 20
             and has_arabic(r[1])]

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(f'hadiths[{len(valid)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
        writer = csv.writer(f)
        writer.writerows(valid)

    return len(valid)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

files = sorted(glob.glob(f'{SECTIONS_DIR}/*.toon'))
total = 0
for fp in files:
    n = fix_file(fp)
    print(f'{os.path.basename(fp)}: {n} valid hadiths')
    total += n
print(f'\nTotal valid hadiths across all files: {total}')
