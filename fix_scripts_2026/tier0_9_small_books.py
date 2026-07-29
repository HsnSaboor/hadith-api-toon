#!/usr/bin/env python3
"""
Tier 0.9 — small books alt-repo merges. Per DATASET_FIX_PLAN_2026.md:
daraqutni, aladab-almufrad (en+ur), sunan-darimi, nasai-kubra (en+ur),
sahih-ibn-khuzaymah (ur), mishkat (en). ~264 total rows expected.

All sources are list-of-dicts keyed by 'hadithnumber', same schema.
"""
import sys, os, json, glob

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge

REPO = '/home/saboor/code/hadith-api-toon'
ALT = os.path.expanduser('~/code/hadith-api-toon-alt')
LOG_DIR = f'{REPO}/fix_scripts_2026/logs'

JOBS = [
    ('sunan-al-daraqutni', 'en', f'{ALT}/daraqutni/en.json'),
    ('aladab-almufrad', 'en', f'{ALT}/adab/en.json'),
    ('aladab-almufrad', 'ur', f'{ALT}/adab/ur.json'),
    ('sunan-darimi', 'en', f'{ALT}/darimi/en.json'),
    ('nasai-kubra', 'en', f'{ALT}/nasaikubra/en.json'),
    ('nasai-kubra', 'ur', f'{ALT}/nasaikubra/ur.json'),
    ('sahih-ibn-khuzaymah', 'ur', f'{ALT}/ibnkhuzayma/ur.json'),
    ('mishkat', 'en', f'{ALT}/mishkat/en.json'),
]


def load_updates(source_path):
    with open(source_path, encoding='utf-8') as f:
        data = json.load(f)
    return {str(h['hadithnumber']): h['text'] for h in data if h.get('text')}


def merge_job(book, lang, source_path):
    updates = load_updates(source_path)
    target_dir = f'{REPO}/editions/{book}/translations/{lang}/sections'
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
    print(f'{book}/{lang}: {total} rows updated across {len(all_logs)} files')
    return all_logs, total


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    grand_total = 0
    for book, lang, source_path in JOBS:
        logs, total = merge_job(book, lang, source_path)
        grand_total += total
        safe_book = book.replace('-', '_')
        with open(f'{LOG_DIR}/tier0_9_{safe_book}_{lang}.log.json', 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f'\nGrand total rows changed: {grand_total}')


if __name__ == '__main__':
    main()
