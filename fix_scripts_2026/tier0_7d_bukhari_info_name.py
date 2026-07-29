#!/usr/bin/env python3
"""
Tier 0.7d — bukhari info.toon: populate the generic `name` field with the
correct `name_en` value for the 6 sections where it was left in raw Arabic
(sections 27, 40, 43, 67, 70, 72). name_en is already correct for all 97
sections; only the generic fallback `name` column lags for these 6.
"""
import sys, os, csv, io

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import serialize_row

REPO = '/home/saboor/code/hadith-api-toon'
PATH = f'{REPO}/editions/bukhari/info.toon'
TARGET_IDS = {'27', '40', '43', '67', '70', '72'}


def main():
    with open(PATH, encoding='utf-8') as f:
        content = f.read()

    idx = content.find('sections[')
    header_end = content.find(':', idx) + 1
    prefix = content[:header_end]  # everything up to and including the sections header colon
    rest = content[header_end:].lstrip('\n')

    lines = rest.split('\n')
    spans = []
    buf = []
    for line in lines:
        if not buf and line == '':
            continue
        buf.append(line)
        combined = '\n'.join(buf)
        if combined.replace('""', '').count('"') % 2 == 0:
            parsed = next(csv.reader(io.StringIO(combined)), [])
            if parsed:
                spans.append((combined, parsed))
            buf = []

    changed = 0
    new_spans = []
    for raw, fields in spans:
        if fields and fields[0] in TARGET_IDS:
            new_fields = list(fields)
            new_fields[1] = new_fields[4]  # name <- name_en
            new_raw = serialize_row(new_fields)
            new_spans.append((new_raw, new_fields))
            changed += 1
            print(f'section {fields[0]}: name <- "{new_fields[4]}"')
        else:
            new_spans.append((raw, fields))

    new_rest = '\n'.join(raw for raw, _ in new_spans) + '\n'
    with open(PATH, 'w', encoding='utf-8', newline='') as f:
        f.write(prefix + '\n' + new_rest)

    print(f'\n{changed} sections updated')


if __name__ == '__main__':
    main()
