#!/usr/bin/env python3
"""
Tier 0.3 (secondary) — fix the 6 additional 8-column CSV-overflow AR rows in
muslim, same root cause/fix as the already-documented HN5103: a leaked Urdu
metadata string ("صحیح مسلم حدیث: N عربی حدیث: M") got merged into the grades
field with a trailing stray quote, shifting every subsequent field over by one
and producing 8 columns instead of the schema's 7
(hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro).

Fix: drop the leaked-metadata field (index 2), take the real grade value from
index 3 (currently prefixed with a stray ": ", e.g. ": Sahih" -> "Sahih"),
and shift reference/international_number/narrator_chain/chapter_intro back
into their correct positions.
"""
import sys, os, csv, io, re

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import serialize_row

REPO = '/home/saboor/code/hadith-api-toon'
TARGETS = [
    ('5', '1267'), ('28', '4383'), ('32', '4526'),
    ('37', '5484'), ('50', '6981'), ('55', '7502'),
]


def fix_row(fields):
    """fields has 8 entries: [hn, arabic, leaked_metadata, ': Sahih', reference,
    intl_number, narrator_chain, chapter_intro] -> 7 correct fields."""
    assert len(fields) == 8, f'expected 8 fields, got {len(fields)}: {fields}'
    hn, arabic, _leaked, grade_raw, reference, intl_number, narrator_chain, chapter_intro = fields
    grade = grade_raw.lstrip(':').strip()
    return [hn, arabic, grade, reference, intl_number, narrator_chain, chapter_intro]


def main():
    for section_num, hn in TARGETS:
        path = f'{REPO}/editions/muslim/sections/{section_num}.toon'
        with open(path, encoding='utf-8') as f:
            content = f.read()
        header_line, rest = content.split('\n', 1)

        # locate + fix surgically: parse whole file into rows via csv reader
        # but rebuild raw text preserving all untouched rows byte-for-byte.
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

        changed = False
        new_spans = []
        for raw, fields in spans:
            if fields and fields[0] == hn and len(fields) == 8:
                fixed_fields = fix_row(fields)
                new_raw = serialize_row(fixed_fields)
                new_spans.append((new_raw, fixed_fields))
                changed = True
                print(f'section {section_num} HN {hn}: fixed 8->7 fields, grade="{fixed_fields[2]}"')
            else:
                new_spans.append((raw, fields))

        if changed:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(header_line + '\n')
                f.write('\n'.join(raw for raw, _ in new_spans))
                f.write('\n')
        else:
            print(f'section {section_num} HN {hn}: NOT FOUND OR ALREADY FIXED')


if __name__ == '__main__':
    main()
