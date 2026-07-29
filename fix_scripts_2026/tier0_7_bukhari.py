#!/usr/bin/env python3
"""
Tier 0.7 — bukhari translation merge from scripts/cache/*-bukhari.min.json
across bn/en/id/tr/ur. Per DATASET_FIX_PLAN_2026.md, verified 132/132 clean
except one isolated Indonesian gap-shift at HN 3820/3821.

Indonesian (id) gap-shift handling:
  - cache['ind']['hadithnumber'==3820] is empty (real gap in the cache).
  - cache['ind']['hadithnumber'==3821]'s text actually belongs to HN 3820
    (confirmed: narrator chain "Qutaibah bin Sa'id -> Muhammad bin Fudlail ->
    Umarah -> Abu Zur'ah -> Abu Hurairah" matches live AR at HN 3820 exactly,
    not AR at HN 3821 which is a different Aisha/Hisham chain).
  - cache['ind']['hadithnumber'==3822] does NOT cleanly match AR-3821 either
    (deeper structural issue in the cache beyond a simple 1-off shift).
  - Fix: apply cache-3821's text to repo HN 3820. Leave repo HN 3821
    untouched (skip it from the id merge) rather than guess further shifts.
"""
import sys, os, json, glob

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge

REPO = '/home/saboor/code/hadith-api-toon'
LOG_DIR = f'{REPO}/fix_scripts_2026/logs'

SOURCE_MAP = {
    'bn': 'ben-bukhari.min.json',
    'en': 'eng-bukhari.min.json',
    'id': 'ind-bukhari.min.json',
    'tr': 'tur-bukhari.min.json',
    'ur': 'urd-bukhari.min.json',
}


def load_updates(source_file, repo_lang):
    with open(f'{REPO}/scripts/cache/{source_file}', encoding='utf-8') as f:
        data = json.load(f)
    updates = {str(h['hadithnumber']): h['text'] for h in data['hadiths'] if h.get('text')}

    if repo_lang == 'id':
        # apply the confirmed shift-correction for HN 3820 specifically
        updates['3820'] = updates.get('3821', '')
        # never let the (wrong-for-3821, right-for-3820) text also land on 3821
        updates.pop('3821', None)
        print('  [id] applied HN3820<-cache3821 shift-correction; skipped HN3821 (unresolved deeper shift)')

    return updates


def merge_lang(repo_lang, source_file):
    updates = load_updates(source_file, repo_lang)
    target_dir = f'{REPO}/editions/bukhari/translations/{repo_lang}/sections'
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
        with open(f'{LOG_DIR}/tier0_7_bukhari_{repo_lang}.log.json', 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f'\nGrand total rows changed: {grand_total}')


if __name__ == '__main__':
    main()
