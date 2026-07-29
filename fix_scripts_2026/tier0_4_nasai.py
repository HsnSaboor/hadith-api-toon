#!/usr/bin/env python3
"""
Tier 0.4 — nasai merge from scripts/cache/*-nasai.min.json across
bn/en/fr/id/tr/ur. Per DATASET_FIX_PLAN_2026.md, this source was not
independently verified in the earlier pass -- pre-merge alignment spot-check
performed here (25 rows across en/ur) confirmed clean narrator-chain match
against AR (e.g. HN156 Al-Miqdad bin Al-Aswad/Ali, HN53 Anas/Bedouin,
HN219 Fatima bint Abi Hubaysh -- all confirmed exact matches).

Do NOT attempt the hi/roman-ur section-36 gap or the ru/ta book-wide
near-total-absence here -- those need actual translation work (Tier 1/3),
no cached translation exists for those language/section combinations.
"""
import sys, os, json, glob

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge

REPO = '/home/saboor/code/hadith-api-toon'
LOG_DIR = f'{REPO}/fix_scripts_2026/logs'

SOURCE_MAP = {
    'bn': 'ben-nasai.min.json',
    'en': 'eng-nasai.min.json',
    'fr': 'fra-nasai.min.json',
    'id': 'ind-nasai.min.json',
    'tr': 'tur-nasai.min.json',
    'ur': 'urd-nasai.min.json',
}


def merge_lang(repo_lang, source_file):
    with open(f'{REPO}/scripts/cache/{source_file}', encoding='utf-8') as f:
        data = json.load(f)
    updates = {str(h['hadithnumber']): h['text'] for h in data['hadiths'] if h.get('text')}

    target_dir = f'{REPO}/editions/nasai/translations/{repo_lang}/sections'
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
        with open(f'{LOG_DIR}/tier0_4_nasai_{repo_lang}.log.json', 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f'\nGrand total rows changed: {grand_total}')


if __name__ == '__main__':
    main()
