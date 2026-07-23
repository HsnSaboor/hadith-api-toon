#!/usr/bin/env python3
"""Fix 4 bukhari hadiths in section 0.toon (the special combined-hadith
appendix section) that use a dash-range key format (e.g. "5709-5712")
in the Arabic file but have separate individual keys in the English file.
All other combined entries in this section correctly use comma format
(e.g. "272, 273") with matching combined EN keys.

Fix: add a new EN row using the dash-range key, populated with the
existing (already correct) EN content at the range's lowest sub-number.
"""
import csv, io

ED = "/home/saboor/code/hadith-api-toon/editions/bukhari"
AR_PATH = f"{ED}/sections/0.toon"
EN_PATH = f"{ED}/translations/en/sections/0.toon"

DASH_KEYS = ['5709-5712', '5773-5775', '6073-6075', '6173-6175']


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def main():
    with open(EN_PATH, errors='replace') as f:
        en_text = f.read()
    r = csv.reader(io.StringIO(en_text))
    header = next(r)
    rows = list(r)
    en_dict = {row[0]: row[1] for row in rows if len(row) >= 2}

    added = 0
    for rng in DASH_KEYS:
        lo = rng.split('-')[0]
        if rng in en_dict:
            continue
        content = en_dict.get(lo, '')
        if not content:
            print(f"WARNING: no content found for low key {lo} of range {rng}")
            continue
        rows.append([rng, content])
        added += 1
        print(f"Added EN entry for '{rng}' using content from '{lo}'")

    # Rewrite file preserving original row order + new appended rows
    with open(AR_PATH, errors='replace') as f:
        ar_text = f.read()
    ar_r = csv.reader(io.StringIO(ar_text))
    next(ar_r)
    ar_count = sum(1 for row in ar_r if len(row) >= 2)

    lines = [f'"hadiths[{ar_count}]{{hadithnumber,text}}:"']
    for row in rows:
        # hadithnumber field may contain commas (e.g. "272, 273" combined
        # hadith keys) so it must also be quote-escaped for valid CSV.
        key_field = escape_toon_field(row[0]) if ',' in row[0] else row[0]
        lines.append(f"{key_field},{escape_toon_field(row[1])}")
    with open(EN_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"\nAdded {added} entries. Total EN rows now: {len(rows)} (AR has {ar_count})")


if __name__ == '__main__':
    main()
