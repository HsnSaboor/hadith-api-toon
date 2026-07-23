#!/usr/bin/env python3
"""Fuzzy-match the 149 unmatched aladab-almufrad hadiths against sunnah.com's
scraped AR+EN pairs, using difflib similarity on normalized Arabic (robust to
minor whitespace/punctuation differences that break exact string matching,
e.g. missing space around line breaks in poetry verses).

For genuinely supplementary hadiths not on sunnah.com at all (348, 1323-1329),
falls back to the LLM translation already generated in
llm_translate_adab_gaps_cache.json.

A high similarity threshold (0.90) is used to avoid falsely matching a
different-but-similar hadith (there are many formulaic openings like
"Abu Hurayra reported that the Prophet... said").
"""
import re, csv, io, os, json
import difflib

ED = "/home/saboor/code/hadith-api-toon/editions/aladab-almufrad"
AR_DIR = f"{ED}/sections"
EN_DIR = f"{ED}/translations/en/sections"
PAIRS_CACHE = "/home/saboor/code/hadith-api-toon/rescrape_adab_en_v4_pairs_cache.json"
UNMATCHED_PATH = "/home/saboor/code/hadith-api-toon/rescrape_adab_en_v4_unmatched.json"
LLM_CACHE = "/home/saboor/code/hadith-api-toon/llm_translate_adab_gaps_cache.json"
EXACT_MATCH_REPORT = "/home/saboor/code/hadith-api-toon/fuzzy_match_report.json"

ARABIC_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u200f\u200e]')
NON_ARABIC_LETTERS = re.compile(r'[^\u0621-\u064A ]')

SIMILARITY_THRESHOLD = 0.90


def normalize_arabic(text):
    text = ARABIC_DIACRITICS.sub('', text)
    text = NON_ARABIC_LETTERS.sub(' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def load_our_hadiths():
    items = {}
    for fn in sorted(os.listdir(AR_DIR)):
        if not fn.endswith('.toon'):
            continue
        with open(f"{AR_DIR}/{fn}") as f:
            text = f.read()
        r = csv.reader(io.StringIO(text))
        next(r)
        for row in r:
            if len(row) >= 2:
                items[row[0]] = row[1]
    return items


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def main():
    with open(UNMATCHED_PATH) as f:
        unmatched = json.load(f)
    with open(PAIRS_CACHE) as f:
        pairs_cache = json.load(f)
    llm_cache = {}
    if os.path.exists(LLM_CACHE):
        with open(LLM_CACHE) as f:
            llm_cache = json.load(f)

    hn_to_ar = load_our_hadiths()

    # Build flat list of (normalized_ar, en) from all sunnah.com chapters
    all_sunnah_pairs = []
    for cid in range(1, 58):
        for ar, en in pairs_cache[str(cid)]:
            norm = normalize_arabic(ar)
            if norm:
                all_sunnah_pairs.append((norm, en))

    print(f"Sunnah.com pairs pool: {len(all_sunnah_pairs)}", flush=True)
    print(f"Unmatched to resolve: {len(unmatched)}", flush=True)

    report = []
    final_texts = {}
    fuzzy_matched = 0
    llm_fallback = 0
    no_source = 0

    for hn in unmatched:
        our_ar = hn_to_ar.get(hn, '')
        our_norm = normalize_arabic(our_ar)
        if not our_norm:
            no_source += 1
            continue

        best_ratio = 0.0
        best_en = None
        best_ar_norm = None
        for sunnah_norm, en in all_sunnah_pairs:
            # length-based short-circuit for speed
            if abs(len(sunnah_norm) - len(our_norm)) > max(30, len(our_norm) * 0.3):
                continue
            ratio = difflib.SequenceMatcher(None, our_norm, sunnah_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_en = en
                best_ar_norm = sunnah_norm

        if best_ratio >= SIMILARITY_THRESHOLD:
            final_texts[hn] = best_en
            fuzzy_matched += 1
            report.append({'hn': hn, 'method': 'fuzzy', 'ratio': round(best_ratio, 3)})
        else:
            llm_text = llm_cache.get(hn, '')
            if llm_text.strip():
                final_texts[hn] = llm_text
                llm_fallback += 1
                report.append({'hn': hn, 'method': 'llm', 'best_fuzzy_ratio': round(best_ratio, 3)})
            else:
                report.append({'hn': hn, 'method': 'FAILED', 'best_fuzzy_ratio': round(best_ratio, 3)})

    print(f"\nFuzzy matched (>= {SIMILARITY_THRESHOLD}): {fuzzy_matched}", flush=True)
    print(f"LLM fallback: {llm_fallback}", flush=True)
    print(f"No source text: {no_source}", flush=True)
    print(f"Total resolved: {len(final_texts)}/{len(unmatched)}", flush=True)

    with open(EXACT_MATCH_REPORT, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    # Now merge with the already-written exact matches from v4 (which are
    # already in the .toon files) - just need to patch in these resolved ones.
    section_files = sorted(
        [f for f in os.listdir(AR_DIR) if f.endswith('.toon')],
        key=lambda f: int(f.replace('.toon', ''))
    )
    written = 0
    patched = 0
    for fn in section_files:
        en_path = f"{EN_DIR}/{fn}"
        if not os.path.exists(en_path):
            continue
        with open(en_path) as f:
            text = f.read()
        r = csv.reader(io.StringIO(text))
        header = next(r)
        rows = list(r)

        changed = False
        new_rows = []
        for row in rows:
            hn = row[0]
            if hn in final_texts and hn in unmatched:
                new_rows.append([hn, final_texts[hn]])
                changed = True
                patched += 1
            else:
                new_rows.append(row)

        if changed:
            lines = [header[0] if isinstance(header[0], str) else header]
            out_lines = ['"' + header[0].strip('"') + '"'] if False else None
            # Reconstruct header line properly
            with open(f"{AR_DIR}/{fn}") as f:
                ar_text = f.read()
            ar_r = csv.reader(io.StringIO(ar_text))
            next(ar_r)
            count = sum(1 for _ in ar_r)
            out_lines = [f'"hadiths[{count}]{{hadithnumber,text}}:"']
            for row in new_rows:
                out_lines.append(f"{row[0]},{escape_toon_field(row[1])}")
            with open(en_path, 'w') as f:
                f.write('\n'.join(out_lines) + '\n')
            written += 1

    print(f"\nPatched {patched} entries across {written} section files", flush=True)


if __name__ == '__main__':
    main()
