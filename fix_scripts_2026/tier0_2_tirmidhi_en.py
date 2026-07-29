#!/usr/bin/env python3
"""
Tier 0.2 (EN ONLY, per verified plan) — tirmidhi merge from
~/code/hadith-api-toon-new/tirmidhi_final.json.

bn/id/tr are DELIBERATELY EXCLUDED here: verification found tirmidhi_final's
bn/id/tr translation arrays have a real, recurring structural off-by-one
drift relative to arabic/en (confirmed: key '840' translations.bn actually
belongs to hadith 841, systematic check found only ~53% self-aligned). That
needs a dedicated de-drifting script (Tier 1.10-adjacent), not this
mechanical merge. en was independently verified 0/30 mismatch and is safe.

Also strips the 34-row 'Jam e Tirmazi Hadees: N Arabic Hadees: N' scraper
residue suffix (32 en + 2 roman-ur) plus its malformed trailing quote,
across en AND roman-ur (roman-ur isn't otherwise touched by the merge).
"""
import sys, os, json, glob, re

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge, serialize_row

REPO = '/home/saboor/code/hadith-api-toon'
SOURCE = os.path.expanduser('~/code/hadith-api-toon-new/tirmidhi_final.json')
LOG_DIR = f'{REPO}/fix_scripts_2026/logs'

RESIDUE_RE = re.compile(r'\\?n?Jam e Tirmazi Hadees:\s*\d+\s*Arabic Hadees:\s*\d+"*\s*$')


def merge_en():
    with open(SOURCE, encoding='utf-8') as f:
        data = json.load(f)
    updates = {}
    for hn, v in data.items():
        text = v.get('translations', {}).get('en', '')
        if text:
            updates[hn] = text

    target_dir = f'{REPO}/editions/tirmidhi/translations/en/sections'
    files = sorted(glob.glob(f'{target_dir}/*.toon'), key=lambda p: int(os.path.basename(p).split('.')[0]))
    all_logs = []
    total = 0
    for path in files:
        d = read_toon(path)
        new_spans, log = apply_merge(d['spans'], key_col_idx=0, updates=updates)
        if log:
            write_toon(path, d['header_line'], d['block_name'], d['columns'], new_spans)
            total += len(log)
            all_logs.append({'file': os.path.basename(path), 'changes': log})
    print(f'en merge: {total} rows updated across {len(all_logs)} files')
    return all_logs, total


def strip_residue():
    total_stripped = 0
    for lang in ('en', 'roman-ur'):
        target_dir = f'{REPO}/editions/tirmidhi/translations/{lang}/sections'
        for path in sorted(glob.glob(f'{target_dir}/*.toon')):
            with open(path, encoding='utf-8') as f:
                content = f.read()
            header_line, rest = content.split('\n', 1)
            lines = rest.split('\n')
            spans = []
            buf = []
            for line in lines:
                if not buf and line == '':
                    continue
                buf.append(line)
                combined = '\n'.join(buf)
                if combined.replace('""', '').count('"') % 2 == 0:
                    import csv, io
                    parsed = next(csv.reader(io.StringIO(combined)), [])
                    if parsed:
                        spans.append((combined, parsed))
                    buf = []

            changed = False
            new_spans = []
            for raw, fields in spans:
                if fields and RESIDUE_RE.search(fields[-1]):
                    cleaned = RESIDUE_RE.sub('', fields[-1]).rstrip()
                    new_fields = list(fields)
                    new_fields[-1] = cleaned
                    new_raw = serialize_row(new_fields)
                    new_spans.append((new_raw, new_fields))
                    changed = True
                    total_stripped += 1
                else:
                    new_spans.append((raw, fields))

            if changed:
                with open(path, 'w', encoding='utf-8', newline='') as f:
                    f.write(header_line + '\n')
                    f.write('\n'.join(raw for raw, _ in new_spans))
                    f.write('\n')
                print(f'  stripped residue: {path}')

    print(f'Residue strip: {total_stripped} rows cleaned')
    return total_stripped


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    logs, total = merge_en()
    with open(f'{LOG_DIR}/tier0_2_tirmidhi_en.log.json', 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f'EN merge total: {total}')

    stripped = strip_residue()
    print(f'\nGrand total: {total} rows merged, {stripped} rows residue-stripped')


if __name__ == '__main__':
    main()
