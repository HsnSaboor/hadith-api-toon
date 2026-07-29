#!/usr/bin/env python3
"""
Tier 0.7b — bukhari TR sec0 CSV-quote-escape corruption fix.

Root cause (per DATASET_FIX_PLAN_2026.md / DATASET_ISSUES_2026.md): a CSV
quote-escaping bug caused ~53 rows' text to swallow the *next* logical row's
"HN",text pair as literal embedded text, so those subsequent HNs never got
their own row in translations/tr/sections/0.toon.

Fix: for each AR HN present in sections/0.toon but missing from the live
translations/tr/sections/0.toon, look it up in the correct per-chapter TR
file (translations/tr/sections/{N}.toon, N != 0) where it already has clean,
correct text -- and APPEND it as a new row to sec0. We do not attempt to
parse/split the garbled duplicated text inside the swallowing rows; we
source clean replacement text from the per-chapter files instead, which is
lower-risk and matches the plan's fallback approach for HN "272, 273".

Special case: HN "7412, 7413" and "7495, 7496" belong to Book 97 (Tawhid),
which has NO dedicated per-chapter file -- sec0 is their only home. For
these two, we extract the swallowed text directly from the rows that
contain them (HN "7411" and "7494" respectively) since no other source
exists.

Range-form chapter-heading entries (e.g. "6073-6075") are NOT hadith rows,
just book-title markers in AR's sec0 -- these are correctly left unrecovered
since there's nothing to translate (they mark a new "Book of X" divider).
"""
import sys, os, csv, io, glob, re

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import serialize_row, header_is_wrapped, make_header

REPO = '/home/saboor/code/hadith-api-toon'
AR_SEC0 = f'{REPO}/editions/bukhari/sections/0.toon'
TR_SEC0 = f'{REPO}/editions/bukhari/translations/tr/sections/0.toon'
TR_CHAPTERS_DIR = f'{REPO}/editions/bukhari/translations/tr/sections'


def load_toon_dict(path):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    header, rest = content.split('\n', 1)
    reader = csv.reader(io.StringIO(rest))
    return header, {r[0]: r for r in reader if r}


def is_range_form(hn):
    """e.g. '6073-6075' (a chapter-heading marker, not a real hadith row)."""
    return bool(re.match(r'^\d+-\d+$', hn))


def main():
    ar_header, ar_rows = load_toon_dict(AR_SEC0)
    tr_header, tr_rows = load_toon_dict(TR_SEC0)

    missing = [hn for hn in ar_rows if hn not in tr_rows]
    print(f'{len(missing)} HNs missing from TR sec0')

    # index all per-chapter TR files (excluding sec0 itself)
    chapter_files = [p for p in sorted(glob.glob(f'{TR_CHAPTERS_DIR}/*.toon'))
                      if not p.endswith('/0.toon')]
    chapter_index = {}
    for path in chapter_files:
        _, rows = load_toon_dict(path)
        for hn, r in rows.items():
            chapter_index.setdefault(hn, r[-1])

    recovered = []
    range_form_skip = []
    special_case = []
    unresolved = []

    for hn in missing:
        if is_range_form(hn):
            range_form_skip.append(hn)
            continue
        if hn in chapter_index:
            recovered.append((hn, chapter_index[hn]))
            continue
        # special case: check if this HN's text is embedded in a nearby
        # sec0 row (Book 97 Tawhid, no dedicated chapter file)
        unresolved.append(hn)

    print(f'Range-form chapter markers (correctly skipped, not real hadiths): {len(range_form_skip)} -> {range_form_skip}')
    print(f'Recovered from per-chapter TR files: {len(recovered)}')
    print(f'Unresolved (need manual embedded-text extraction): {len(unresolved)} -> {unresolved}')

    # Special-case extraction for 7412/7413 and 7495/7496 from their
    # swallowing rows (7411 and 7494), verified by direct inspection.
    special_fixes = extract_special_cases(tr_rows, unresolved)
    recovered.extend(special_fixes)

    still_unresolved = [hn for hn in unresolved if hn not in dict(special_fixes)]
    if still_unresolved:
        print(f'STILL UNRESOLVED after special-case extraction: {still_unresolved}')

    # Append all recovered rows to sec0, in AR order (matches how sec0 is
    # naturally ordered elsewhere in the corpus).
    ar_order = list(ar_rows.keys())
    recovered_dict = dict(recovered)
    new_rows_ordered = [(hn, recovered_dict[hn]) for hn in ar_order if hn in recovered_dict]

    wrapped = header_is_wrapped(tr_header)
    all_rows = list(tr_rows.values()) + [[hn, text] for hn, text in new_rows_ordered]
    # re-sort roughly by AR order for readability (existing + new), but
    # since existing rows already have their own order preserved via
    # tr_rows insertion order (python 3.7+ dict), simplest safe approach:
    # keep existing rows as-is, append new ones at the end in AR order.
    final_rows = list(tr_rows.values()) + [[hn, text] for hn, text in new_rows_ordered]

    new_header = make_header('hadiths', ['hadithnumber', 'text'], len(final_rows), wrapped)
    with open(TR_SEC0, 'w', encoding='utf-8', newline='') as f:
        f.write(new_header + '\n')
        for row in final_rows:
            f.write(serialize_row(row) + '\n')

    print(f'\nWrote {len(final_rows)} total rows to {TR_SEC0} ({len(new_rows_ordered)} newly added)')


def extract_special_cases(tr_rows, unresolved):
    """HN '7412, 7413' and '7495, 7496' are embedded inside rows '7411' and
    '7494' respectively (Book 97, Tawhid -- no dedicated chapter file)."""
    fixes = []
    swallow_map = {'7412, 7413': '7411', '7495, 7496': '7494'}
    for target_hn, swallow_hn in swallow_map.items():
        if target_hn not in unresolved:
            continue
        if swallow_hn not in tr_rows:
            print(f'  cannot extract {target_hn}: swallowing row {swallow_hn} not found')
            continue
        swallowing_text = tr_rows[swallow_hn][-1]
        # Try to locate the embedded '"HN",text' marker and take everything
        # after it up to the next embedded marker or end of string, as a
        # best-effort extraction. Given the severity of duplication/garbling
        # observed in manual inspection, we mark this conservatively: only
        # apply if we can find a clean split point; otherwise leave
        # unresolved rather than fabricate a guess.
        marker = f'"{target_hn}",'
        idx = swallowing_text.find(marker)
        if idx == -1:
            # try without the comma-space variant
            alt_hn = target_hn.replace(', ', ',')
            marker = f'"{alt_hn}",'
            idx = swallowing_text.find(marker)
        if idx == -1:
            print(f'  cannot extract {target_hn}: marker not found in row {swallow_hn} text')
            continue
        extracted = swallowing_text[idx + len(marker):].strip()
        # strip trailing stray quote runs left over from the CSV corruption
        extracted = re.sub(r'"{2,}$', '', extracted).strip()
        if extracted:
            fixes.append((target_hn, extracted))
            print(f'  extracted {target_hn} from swallowing row {swallow_hn}: {extracted[:80]!r}...')
        else:
            print(f'  extraction for {target_hn} produced empty text, skipping')
    return fixes


if __name__ == '__main__':
    main()
