#!/usr/bin/env python3
"""
Tier 0.5 — ibnmajah merge from scripts/cache/{eng,ben,ind,tur,fra}-ibnmajah.min.json
Per DATASET_FIX_PLAN_2026.md, verified 0/150 narrator mismatch across en/bn/id/tr/fr.
ur/roman-ur/hi already fully recovered per plan — not touched.
"""
import sys, os, json, glob

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge

REPO = '/home/saboor/code/hadith-api-toon'
LOG_DIR = f'{REPO}/fix_scripts_2026/logs'

SOURCE_MAP = {
    'en': 'eng-ibnmajah.min.json',
    'bn': 'ben-ibnmajah.min.json',
    'id': 'ind-ibnmajah.min.json',
    'tr': 'tur-ibnmajah.min.json',
    'fr': 'fra-ibnmajah.min.json',
}


def merge_lang(repo_lang, source_file):
    with open(f'{REPO}/scripts/cache/{source_file}', encoding='utf-8') as f:
        data = json.load(f)
    updates = {str(h['hadithnumber']): h['text'] for h in data['hadiths'] if h.get('text')}

    target_dir = f'{REPO}/editions/ibnmajah/translations/{repo_lang}/sections'
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
    print(f'{repo_lang}: {total} rows updated across {len(all_logs)} files')
    return all_logs, total


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    grand_total = 0
    for repo_lang, source_file in SOURCE_MAP.items():
        logs, total = merge_lang(repo_lang, source_file)
        grand_total += total
        with open(f'{LOG_DIR}/tier0_5_ibnmajah_{repo_lang}.log.json', 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f'\nGrand total rows changed: {grand_total}')


if __name__ == '__main__':
    main()
