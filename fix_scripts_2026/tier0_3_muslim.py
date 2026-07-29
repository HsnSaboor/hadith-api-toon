#!/usr/bin/env python3
"""
Tier 0.3 — muslim merge from scripts/cache/fz_muslim.json across bn/en/fr/id/ta/tr.
Per DATASET_FIX_PLAN_2026.md, verified 0/120 narrator mismatch across en/bn/id/tr.
ru/ur skipped per plan (fawaz sparse there; alt-repo fallback not attempted this
pass, out of scope for the mechanical Tier 0 sweep).
"""
import sys, os, json, glob

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge

REPO = '/home/saboor/code/hadith-api-toon'
SOURCE = f'{REPO}/scripts/cache/fz_muslim.json'
LOG_DIR = f'{REPO}/fix_scripts_2026/logs'

LANG_MAP = {
    'ben': 'bn',
    'eng': 'en',
    'fra': 'fr',
    'ind': 'id',
    'tam': 'ta',
    'tur': 'tr',
}


def merge_lang(fz_key, repo_lang, source_data):
    updates = {hn: v['text'] for hn, v in source_data.get(fz_key, {}).items() if v.get('text')}
    target_dir = f'{REPO}/editions/muslim/translations/{repo_lang}/sections'
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
    with open(SOURCE, encoding='utf-8') as f:
        source_data = json.load(f)

    os.makedirs(LOG_DIR, exist_ok=True)
    grand_total = 0
    for fz_key, repo_lang in LANG_MAP.items():
        logs, total = merge_lang(fz_key, repo_lang, source_data)
        grand_total += total
        with open(f'{LOG_DIR}/tier0_3_muslim_{repo_lang}.log.json', 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    print(f'\nGrand total rows changed across all 6 languages: {grand_total}')


if __name__ == '__main__':
    main()
