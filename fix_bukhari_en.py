import json
import csv
import os
import io

BASE = '/home/saboor/code/hadith-api-toon'
EN_SECTIONS_DIR = os.path.join(BASE, 'editions', 'bukhari', 'translations', 'en', 'sections')
AR_SECTIONS_DIR = os.path.join(BASE, 'editions', 'bukhari', 'sections')

with open('/tmp/eng-bukhari.json', encoding='utf-8') as f:
    eng_data = json.load(f)

eng_map = {}
for h in eng_data['hadiths']:
    eng_map[h['hadithnumber']] = h['text']

section_files = sorted(
    [f for f in os.listdir(AR_SECTIONS_DIR) if f.endswith('.toon')],
    key=lambda x: int(x.replace('.toon', ''))
)

total_hadiths_ar = 0
total_hadiths_en_before = 0
total_matched = 0
total_newly_written = 0

for sf in section_files:
    ar_path = os.path.join(AR_SECTIONS_DIR, sf)

    with open(ar_path, 'r', encoding='utf-8') as f:
        ar_content = f.read()

    lines = ar_content.split('\n')
    header = lines[0] if lines else ''
    data_lines = [l for l in lines[1:] if l.strip()]

    reader = csv.reader(io.StringIO('\n'.join(data_lines)))
    ar_rows = list(reader)

    en_path = os.path.join(EN_SECTIONS_DIR, sf)

    if os.path.exists(en_path):
        with open(en_path, 'r', encoding='utf-8') as f:
            en_content = f.read()
        en_lines = en_content.split('\n')
        en_header = en_lines[0] if en_lines else 'hadiths[count]{hadithnumber,text}:'
        existing_entries = {}
        if len(en_lines) > 1:
            en_reader = csv.reader(io.StringIO('\n'.join(en_lines[1:])))
            for en_row in en_reader:
                if en_row and en_row[0].strip():
                    try:
                        num = int(en_row[0].strip())
                        text = en_row[1] if len(en_row) > 1 else ''
                        existing_entries[num] = text
                    except ValueError:
                        pass
    else:
        en_header = 'hadiths[count]{hadithnumber,text}:'
        existing_entries = {}

    total_hadiths_en_before += len(existing_entries)

    new_entries = []
    for row in ar_rows:
        if not row or not row[0].strip():
            continue
        try:
            hnum = int(row[0].strip())
        except ValueError:
            continue

        total_hadiths_ar += 1
        eng_text = eng_map.get(hnum)

        if eng_text:
            total_matched += 1
            if hnum not in existing_entries or existing_entries[hnum] != eng_text:
                total_newly_written += 1
            new_entries.append((hnum, eng_text))
        elif hnum in existing_entries:
            new_entries.append((hnum, existing_entries[hnum]))
        else:
            new_entries.append((hnum, ''))

    new_entries.sort(key=lambda x: x[0])

    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    for num, text in new_entries:
        writer.writerow([str(num), text])
    csv_content = buf.getvalue()

    os.makedirs(os.path.dirname(en_path), exist_ok=True)
    with open(en_path, 'w', encoding='utf-8') as f:
        f.write(en_header + '\n')
        f.write(csv_content)

print(f'Sections processed: {len(section_files)}')
print(f'Hadiths in Arabic sections: {total_hadiths_ar}')
print(f'Hadiths with English (API match): {total_matched}')
print(f'Hadiths in English sections before: {total_hadiths_en_before}')
print(f'English translations written/updated: {total_newly_written}')
print(f'English fill rate: {total_matched}/{total_hadiths_ar} ({total_matched*100//total_hadiths_ar}%)')
