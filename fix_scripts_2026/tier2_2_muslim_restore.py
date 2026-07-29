#!/usr/bin/env python3
"""
Tier 2.2 — muslim: restore the 116 EN rows that were shrunk (but not fully
emptied) by commit a0a985da10 and never touched by any later commit.

Per DATASET_FIX_PLAN_2026.md: recompute the exact list fresh via git diff,
then restore each from a0a985da10~1 (pre-wipe) IF (and only if) the current
live text is still byte-identical to the post-wipe (shrunk) state — i.e.
only rows nobody has touched since. Never overwrite anything a later commit
already improved.
"""
import sys, os, subprocess, csv, io, json, re

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge, HEADER_RE

REPO = '/home/saboor/code/hadith-api-toon'
WIPE_COMMIT = 'a0a985da10'
LOG_PATH = f'{REPO}/fix_scripts_2026/logs/tier2_2_muslim_restore.log.json'


def git_show(commit, path):
    r = subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=REPO,
                        capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout


def parse_toon_text(content):
    if not content:
        return None, [], []
    parts = content.split('\n', 1)
    header_line = parts[0]
    rest = parts[1] if len(parts) > 1 else ''
    m = HEADER_RE.match(header_line.strip())
    if not m:
        return None, [], []
    reader = csv.reader(io.StringIO(rest))
    rows = [r for r in reader if r]
    return header_line, rows, m.group(2).split(',')


def main():
    files = subprocess.run(
        ['git', 'diff', '--name-only', f'{WIPE_COMMIT}~1', WIPE_COMMIT, '--',
         'editions/muslim/translations/en/sections/'],
        cwd=REPO, capture_output=True, text=True
    ).stdout.strip().split('\n')
    files = [f for f in files if f]
    print(f'{len(files)} files touched by wipe commit')

    restore_candidates = []  # (relpath, hn, pre_text, current_text)

    for relpath in files:
        pre_content = git_show(f'{WIPE_COMMIT}~1', relpath)
        post_content = git_show(WIPE_COMMIT, relpath)
        if pre_content is None or post_content is None:
            continue
        _, pre_rows, _ = parse_toon_text(pre_content)
        _, post_rows, _ = parse_toon_text(post_content)
        pre_by_hn = {r[0]: r[-1] for r in pre_rows if r}
        post_by_hn = {r[0]: r[-1] for r in post_rows if r}

        abspath = os.path.join(REPO, relpath)
        current_d = read_toon(abspath)
        current_by_hn = {f[0]: f[-1] for _, f in current_d['spans'] if f}

        for hn, pre_text in pre_by_hn.items():
            post_text = post_by_hn.get(hn, '')
            pre_len = len(pre_text)
            post_len = len(post_text)
            if pre_len == 0:
                continue
            if post_len < pre_len * 0.5:  # shrunk >50%, matches audit definition
                current_text = current_by_hn.get(hn, '')
                # only restore if current state == post-wipe state (untouched since)
                if current_text == post_text:
                    restore_candidates.append({
                        'file': relpath, 'hn': hn,
                        'pre_len': pre_len, 'post_len': post_len,
                        'current_len': len(current_text),
                    })

    print(f'{len(restore_candidates)} rows confirmed still-wiped and eligible for restore')

    # Group by file, apply restore
    by_file = {}
    for c in restore_candidates:
        by_file.setdefault(c['file'], []).append(c['hn'])

    all_logs = []
    total_changed = 0
    for relpath, hns in by_file.items():
        abspath = os.path.join(REPO, relpath)
        pre_content = git_show(f'{WIPE_COMMIT}~1', relpath)
        _, pre_rows, _ = parse_toon_text(pre_content)
        pre_by_hn = {r[0]: r[-1] for r in pre_rows if r}
        updates = {hn: pre_by_hn[hn] for hn in hns if hn in pre_by_hn}

        d = read_toon(abspath)
        # bypass normal growth-ratio guard (we KNOW these are legit restores,
        # not a new backup source) but still refuse actual shrinkage
        new_spans, log = apply_merge(d['spans'], key_col_idx=0, updates=updates,
                                       min_growth_ratio=1.0, min_abs_len=1)
        if log:
            write_toon(abspath, d['header_line'], d['block_name'], d['columns'], new_spans)
            total_changed += len(log)
            all_logs.append({'file': relpath, 'changes': log})
            print(f'{relpath}: {len(log)} rows restored')

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_logs, f, indent=2, ensure_ascii=False)
    print(f'\nTotal rows restored: {total_changed}')


if __name__ == '__main__':
    main()
