#!/usr/bin/env python3
"""
Tier 0.6 (revised) — malik EN + UR merge from ~/code/hadith-api-toon-alt/malik/{en,ur}.json
via a "reference" field join, not the earlier-assumed hadithnumber join.

Validated in a sandbox first (/tmp/opencode/malik_sandbox/) before running here:
  - en: 33/33 changes substantive (real content recovery), verified against
        Arabic narrator chains (e.g. HN179401: Malik->Nafi'->Abdullah bin Umar
        ->Umar ibn al-Khattab silk-garment story, confirmed correct).
  - ur: 9/9 changes substantive.
  - bn: 356/357 changes were cosmetic-only (a harmless but valueless
        "রেওয়ায়ত N." prefix addition, not real truncation-fix) -- DELIBERATELY
        EXCLUDED from this real-repo run, not worth the diff noise for 1 real fix.
  - fr/id/tr: 0 changes in sandbox -- this alt-repo source is itself equally
        short/truncated for those 3 languages, no benefit -- DELIBERATELY
        EXCLUDED.

Join mechanics: editions/malik's `reference` column ("Muwatta Imam Malik N")
is parsed to extract N, matched against the alt-repo's own `reference` field
(same convention). For editions/malik's split sub-hadiths (hadithnumber
BBBHH+subindex, e.g. 42801/42802 sharing reference N=428), sub-index is
resolved by sorting all HNs sharing that reference number and assigning
1,2,3... — matches the alt-repo's own hadithnumber decimal-suffix convention
(N.1, N.2...) by ordinal position, confirmed correct via manual spot-check
in sandbox research phase.
"""
import sys, os, json, glob, re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, apply_merge

REPO = '/home/saboor/code/hadith-api-toon'
ALT = os.path.expanduser('~/code/hadith-api-toon-alt/malik')
LOG_DIR = f'{REPO}/fix_scripts_2026/logs'

LANGS = ['en', 'ur']
REF_RE = re.compile(r'(\d+)$')

# Scraper-residue suffix found in this alt-repo source itself (already
# documented in KNOWN_ISSUES.md for malik's fr/bn — confirmed here also
# present in ur: 257/2762 entries, 9.3%; en: 1/2762). MUST be stripped
# before comparing/applying text, or we re-introduce known corruption.
RESIDUE_PATTERNS = {
    'ur': re.compile(r'\\n\s*موطا امام مالک\s*حدیث:\s*\d+\s*عربی\s*حدیث:\s*$'),
    'en': re.compile(r'\\n\s*Mouta Imam Malik\s*Hadith:\s*\d+\s*Arabic Hadith:\s*$'),
    'fr': re.compile(r'\\n\s*Mouta Imam Malik\s*Hadith\s*:\s*\d+\s*Hadith arabe\s*:\s*$'),
    'bn': re.compile(r'\\n?\s*মুত্তা\s*ইমাম\s*মালিক?\s*হাদিস:\s*\d+\s*আরবি:\s*$'),
}


def strip_residue(lang, text):
    pattern = RESIDUE_PATTERNS.get(lang)
    if pattern:
        return pattern.sub('', text).rstrip()
    return text


def build_ref_index(lang):
    """reference_number(str int) -> {sub_index: text}, residue-stripped."""
    with open(f'{ALT}/{lang}.json', encoding='utf-8') as f:
        data = json.load(f)
    by_ref = defaultdict(dict)
    contaminated_count = 0
    for x in data:
        hn = x['hadithnumber']
        ref = x.get('reference', '')
        m = REF_RE.search(ref)
        if not m:
            continue
        ref_num = m.group(1)
        sub = int(hn.split('.')[1]) if '.' in hn else 1
        text = x.get('text', '')
        if text:
            cleaned = strip_residue(lang, text)
            if cleaned != text:
                contaminated_count += 1
            by_ref[ref_num][sub] = cleaned
    if contaminated_count:
        print(f'  [{lang}] stripped scraper-residue suffix from {contaminated_count} source entries before use')
    return by_ref


def build_hn_to_subindex():
    """editions/malik hadithnumber -> (reference_number, sub_index), resolved
    by sorting all HNs sharing a reference number and assigning 1,2,3..."""
    hn_to_ref = {}
    for path in sorted(glob.glob(f'{REPO}/editions/malik/sections/*.toon')):
        d = read_toon(path)
        for _, fields in d['spans']:
            hn = fields[0]
            ref = fields[3]
            m = REF_RE.search(ref)
            if m:
                hn_to_ref[hn] = m.group(1)

    ref_to_all_hns = defaultdict(list)
    for hn, ref_num in hn_to_ref.items():
        ref_to_all_hns[ref_num].append(hn)

    hn_to_subindex = {}
    for ref_num, hns in ref_to_all_hns.items():
        for i, hn in enumerate(sorted(hns), start=1):
            hn_to_subindex[hn] = i

    return hn_to_ref, hn_to_subindex


def merge_lang(lang, hn_to_ref, hn_to_subindex):
    ref_index = build_ref_index(lang)

    updates = {}
    for hn, ref_num in hn_to_ref.items():
        sub = hn_to_subindex[hn]
        candidates = ref_index.get(ref_num, {})
        text = candidates.get(sub) or candidates.get(1) or (list(candidates.values())[0] if candidates else None)
        if text:
            updates[hn] = text

    target_dir = f'{REPO}/editions/malik/translations/{lang}/sections'
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
    print(f'{lang}: {total} rows updated across {len(all_logs)} files (candidates: {len(updates)})')
    return all_logs, total


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    hn_to_ref, hn_to_subindex = build_hn_to_subindex()

    grand_total = 0
    for lang in LANGS:
        logs, total = merge_lang(lang, hn_to_ref, hn_to_subindex)
        grand_total += total
        with open(f'{LOG_DIR}/tier0_6_malik_{lang}.log.json', 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    print(f'\nGrand total rows changed: {grand_total}')


if __name__ == '__main__':
    main()
