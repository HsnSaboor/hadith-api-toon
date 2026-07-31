#!/usr/bin/env python3
"""
Strip scraper-residue suffix from editions/nasai/translations/fr/sections/0.toon.

Pattern: " Sunan an-Nisa'i Hadith : N Hadith arabe : N" appended directly
(no separator) onto the end of the real translation text. Found in 20 rows
(HN 3884-3903), pre-existing before any 2026 fix touched this book (confirmed
via git history). Logged in KNOWN_ISSUES.md nasai item 5.

This is a strip, not a merge — no external source needed, we're removing
known-junk suffix text, not replacing content.
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, serialize_row

PATH = '/home/saboor/code/hadith-api-toon/editions/nasai/translations/fr/sections/0.toon'
PATTERN = re.compile(r"\s*Sunan an-Nisa'i Hadith\s*:\s*\d+\s*Hadith arabe\s*:\s*\d*\s*$")


def main():
    d = read_toon(PATH)
    new_spans = []
    changed = 0
    for raw, fields in d['spans']:
        text = fields[-1]
        stripped = PATTERN.sub('', text)
        if stripped != text:
            changed += 1
            new_fields = fields[:-1] + [stripped]
            new_spans.append((serialize_row(new_fields), new_fields))
        else:
            new_spans.append((raw, fields))

    write_toon(PATH, d['header_line'], d['block_name'], d['columns'], new_spans)
    print(f'changed: {changed} rows across 1 file')


if __name__ == '__main__':
    main()
