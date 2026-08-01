#!/usr/bin/env python3
"""
Fix abudawud's 7 wrong-content BN rows (Tier 1.3): HN 1192, 1275, 4497,
4542, 4586, 4599, 4665 had real but MISFILED Bengali text — content
belonging to a different, unrelated hadith.

Source: ~/code/hadith-api-toon-new/abudawud_final.json, translations.be
field. IMPORTANT: this source's own dict-key numbering does NOT match
the live edition's hadithnumber (confirmed via direct AR-text search: the
source is offset inconsistently, +1 in early sections, +2 in later ones,
with at least one +432 anomaly around HN4497 suggesting a completely
different book-splitting scheme in that region). Never trust the source's
own key -- for each target live HN, its correct source-key was found by
searching the source's own `arabic` field for a substring match against
the LIVE Arabic text at that HN, then using THAT key's `be` translation.
Verified again independently: each resulting BE text's topic matches the
live EN text at the same HN (freeing slaves/eclipse, 2 rak'ahs after
prayer, qisas->remission, blood-money value, medicine-practice liability,
love/hate for Allah's sake, alternate-chain-same-effect).

Mapping (live_hn -> correct source_key, found via AR content match):
  1192 -> 1193
  1275 -> 1276
  4497 -> 4499
  4542 -> 4544
  4586 -> 4588
  4599 -> 4601
  4665 -> 4667
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, serialize_row

SRC_PATH = os.path.expanduser('~/code/hadith-api-toon-new/abudawud_final.json')
REPO = '/home/saboor/code/hadith-api-toon'

MAPPING = {
    '1192': '1193',
    '1275': '1276',
    '4497': '4499',
    '4542': '4544',
    '4586': '4588',
    '4599': '4601',
    '4665': '4667',
}


def main():
    with open(SRC_PATH, encoding='utf-8') as f:
        src = json.load(f)

    replacements = {}
    for live_hn, src_key in MAPPING.items():
        be = src[src_key]['translations']['be']
        replacements[live_hn] = be.strip()

    files = set()
    for live_hn in MAPPING:
        for path in [
            f'{REPO}/editions/abudawud/translations/bn/sections/{i}.toon' for i in range(1, 60)
        ]:
            pass  # placeholder, real lookup below

    import glob
    changed_total = 0
    for path in sorted(glob.glob(f'{REPO}/editions/abudawud/translations/bn/sections/*.toon')):
        d = read_toon(path)
        changed = 0
        new_spans = []
        for raw, fields in d['spans']:
            hn = fields[0].strip('"')
            if hn in replacements:
                new_fields = [hn, replacements[hn]]
                new_spans.append((serialize_row(new_fields), new_fields))
                changed += 1
            else:
                new_spans.append((raw, fields))
        if changed:
            write_toon(path, d['header_line'], d['block_name'], d['columns'], new_spans)
            print(f'{path}: {changed} row(s) replaced')
            changed_total += changed

    print(f'Total: {changed_total} rows replaced (expected 7)')


if __name__ == '__main__':
    main()
