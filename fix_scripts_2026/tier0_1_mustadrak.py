#!/usr/bin/env python3
"""
Tier 0.1 — mustadrak EN merge from ~/code/hadith-api-toon-alt/hakim/en.json
Per DATASET_FIX_PLAN_2026.md, verified 0% narrator mismatch on 30-row sample.
No-shrink guardrail enforced by toon_io.apply_merge (min_growth_ratio=1.3).
"""
import sys, os, json, glob

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge

REPO = '/home/saboor/code/hadith-api-toon'
SOURCE = os.path.expanduser('~/code/hadith-api-toon-alt/hakim/en.json')
TARGET_DIR = f'{REPO}/editions/mustadrak/translations/en/sections'
LOG_PATH = f'{REPO}/fix_scripts_2026/logs/tier0_1_mustadrak.log.json'


def main():
    with open(SOURCE, encoding='utf-8') as f:
        source_rows = json.load(f)
    updates = {row['hadithnumber']: row['text'] for row in source_rows if row.get('text')}
    print(f'Loaded {len(updates)} candidate updates from source')

    all_logs = []
    files = sorted(glob.glob(f'{TARGET_DIR}/*.toon'), key=lambda p: int(os.path.basename(p).split('.')[0]))
    total_changed = 0
    for path in files:
        d = read_toon(path)
        new_spans, log = apply_merge(d['spans'], key_col_idx=0, updates=updates)
        if log:
            write_toon(path, d['header_line'], d['block_name'], d['columns'], new_spans)
            total_changed += len(log)
            all_logs.append({'file': os.path.basename(path), 'changes': log})
            print(f'{os.path.basename(path)}: {len(log)} rows updated')

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_logs, f, indent=2, ensure_ascii=False)
    print(f'\nTotal rows changed: {total_changed}')
    print(f'Log written to {LOG_PATH}')


if __name__ == '__main__':
    main()
