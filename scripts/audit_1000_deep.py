#!/usr/bin/env python3
"""
Deep content audit for hadith-api-toon.

For every book under editions/:
  - sample up to 1000 random hadiths (seed=42)
  - dump each hadith's full content (arabic, grades, reference,
    international_number, narrator_chain, chapter_intro) and ALL available
    translation texts
  - include all chapter names + name translations and book intros +
    intro translations
  - run automated error detection (empty/truncated/placeholder/HTML/zero-width/
    mojibake/arabic-in-latin/duplicate/missing/metadata mismatches, etc.)
Output is a single .toon file with `end_<block>` markers so a third party can
read and verify each block independently.
"""
import os, re, csv, random, hashlib, sys
from collections import defaultdict, Counter

BASE = "/home/saboor/code/hadith-api-toon"
EDITIONS = os.path.join(BASE, "editions")
OUT = os.path.join(BASE, "audit_1000_deep.toon")
SEED = 42
SAMPLE = 1000

# ---- regex helpers -------------------------------------------------------
ZW = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]')
HTML = re.compile(r'<[^>]+>')
CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
AR = re.compile(r'[\u0600-\u06ff\ufe70-\ufefe\u0750-\u077f]')
LATIN = re.compile(r'[A-Za-z]')
HONOR = set('\ufdfa\ufdfb\ufdfc\ufdfd\ufdfe\ufeffﷺﷻﵞ')
PLACEHOLDER = re.compile(
    r'^(same as|similar to|as above|see (the )?hadith|narration about|'
    r'wrong same as|\.\.\.\s*$|\(as hadith|refer to hadith|same\b|see above|'
    r'mentioned above|same hadith)', re.I)
MOJIBAKE = re.compile(r'Ã.|â€|ï¿½|â€™|â€œ|â€\x9d|�')
REPLACEMENT = '\ufffd'

# languages whose script is NOT arabic -> stray arabic chars are errors
ARABIC_SCRIPT_LANGS = {'ar', 'ur', 'fa', 'ps'}

BLOCK_RE = re.compile(r'^([A-Za-z_]+)\[(\w+)\]')


def read_toon_rows(path):
    """Return (block_name, fields, [dict,...]) for a single-block toon file."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'^([A-Za-z_]+)\[(\w+)\]\{(.*?)\}\s*:', text, re.DOTALL)
    if not m:
        return None, [], []
    name = m.group(1)
    fields = [x.strip() for x in m.group(3).split(',')]
    # data starts after the header line
    rest = text[m.end():]
    reader = csv.reader(rest.split('\n'))
    rows = []
    for r in reader:
        if not r:
            continue
        if len(r) < len(fields):
            r = r + [''] * (len(fields) - len(r))
        rows.append(dict(zip(fields, r)))
    return name, fields, rows


def parse_info(path):
    """Return (metadata_dict, translations_list, sections_list)."""
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    meta, translations, sections = {}, [], []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        # metadata block
        if re.match(r'^metadata\s*:\s*$', line):
            i += 1
            while (i < n and lines[i].strip() and
                   not re.match(r'^[A-Za-z_]+\[', lines[i]) and
                   not re.match(r'^metadata\s*:', lines[i])):
                km = re.match(r'\s*([A-Za-z_]+)\s*:\s*(.*)$', lines[i])
                if km:
                    k, v = km.group(1), km.group(2).strip()
                    if len(v) >= 2 and v.startswith('"') and v.endswith('"'):
                        v = v[1:-1]
                    meta[k] = v
                i += 1
            continue
        # block header start
        hm = re.match(r'^([A-Za-z_]+)\[\w+\]\{', line)
        if hm:
            name = hm.group(1)
            j = i
            while j < n and not lines[j].rstrip().endswith('}:'):
                j += 1
            header_text = '\n'.join(lines[i:j + 1])
            bs = header_text.find('{')
            be = header_text.rfind('}')
            fields = ([x.strip() for x in header_text[bs + 1:be].split(',')]
                      if bs != -1 and be != -1 else [])
            i = j + 1
            raw = []
            while (i < n and lines[i].strip() and
                   not re.match(r'^[A-Za-z_]+\[', lines[i]) and
                   not re.match(r'^metadata\s*:', lines[i])):
                raw.append(lines[i])
                i += 1
            parsed = []
            for r in csv.reader(raw):
                if not r:
                    continue
                if len(r) < len(fields):
                    r = r + [''] * (len(fields) - len(r))
                parsed.append(dict(zip(fields, r)))
            if name == 'translations':
                translations = parsed
            elif name == 'sections':
                sections = parsed
            continue
        i += 1
    return meta, translations, sections


# ---- issue collection ----------------------------------------------------
issues = []  # (book, section, hn, lang, itype, desc)


def add(book, section, hn, lang, itype, desc):
    issues.append((book, section, str(hn), lang or '', itype, desc[:300]))


def main():
    random.seed(SEED)
    books = sorted(d for d in os.listdir(EDITIONS)
                   if os.path.isdir(os.path.join(EDITIONS, d)) and
                   os.path.exists(os.path.join(EDITIONS, d, 'info.toon')))

    total_sampled = 0
    book_summaries = []          # (id, name, langs, total_h, sampled, n_sections, n_issues)
    chapter_rows = []            # (book, cid, name, name_ar, name_bn, ..., first, last)
    intro_rows = []              # (book, intro, intro_ar, intro_en, ...)
    hadith_rows = []             # (book, hn, section, arabic, grades, ref, intl, narrator, chapter_intro)
    translation_rows = []        # (book, hn, lang, text)

    book_issue_counts = Counter()

    for book in books:
        bpath = os.path.join(EDITIONS, book)
        sections_dir = os.path.join(bpath, 'sections')
        trans_dir = os.path.join(bpath, 'translations')
        meta, translations_block, sections_block = parse_info(
            os.path.join(bpath, 'info.toon'))

        book_name = meta.get('book_name', book)
        declared_langs = [x.strip() for x in
                          meta.get('available_languages', '').split(',') if x.strip()]
        if os.path.isdir(trans_dir):
            lang_dirs = sorted(d for d in os.listdir(trans_dir)
                               if os.path.isdir(os.path.join(trans_dir, d)))
        else:
            lang_dirs = []

        # ----- chapters -------------------------------------------------
        for ch in sections_block:
            row = [book, ch.get('id', ''), ch.get('name', '')]
            for f in ('name_ar', 'name_bn', 'name_en', 'name_fr', 'name_id',
                      'name_ru', 'name_tr', 'name_ur'):
                row.append(ch.get(f, ''))
            row += [ch.get('hadith_first', ''), ch.get('hadith_last', '')]
            chapter_rows.append(row)
            # chapter checks
            if not ch.get('name', '').strip():
                add(book, '', ch.get('id', ''), 'chapter', 'EMPTY_CHAPTER_NAME',
                    'chapter has empty name')
            # missing name translations while english present
            en = ch.get('name_en', '').strip()
            if en:
                for f, lbl in (('name_ar', 'ar'), ('name_ur', 'ur'),
                               ('name_fr', 'fr'), ('name_id', 'id'),
                               ('name_bn', 'bn'), ('name_tr', 'tr'),
                               ('name_ru', 'ru')):
                    if not ch.get(f, '').strip() and f in lang_dirs:
                        add(book, '', ch.get('id', ''), 'chapter',
                            'MISSING_CHAPTER_NAME_TR',
                            f'chapter "{en[:40]}" missing name_{lbl}')

        # ----- intros ---------------------------------------------------
        intro = meta.get('intro', '')
        irow = [book, intro]
        for f in ('intro_ar', 'intro_en', 'intro_ur', 'intro_fr', 'intro_id',
                  'intro_bn', 'intro_tr', 'intro_ru', 'intro_hi', 'intro_ro',
                  'intro_de', 'intro_es', 'intro_sw', 'intro_ta', 'intro_te'):
            irow.append(meta.get(f, ''))
        intro_rows.append(irow)
        if intro and 'en' in lang_dirs and not meta.get('intro_en', '').strip():
            add(book, '', '', 'intro', 'MISSING_INTRO_EN',
                'book has intro but no intro_en though en available')
        if meta.get('intro_ar', '') and not AR.search(meta.get('intro_ar', '')):
            add(book, '', '', 'intro', 'BAD_INTRO_AR',
                'intro_ar present but contains no arabic script')

        # ----- collect hadiths from section files -----------------------
        hn_map = {}          # hn -> record dict (+ _section)
        all_hns = []
        if os.path.isdir(sections_dir):
            for fn in sorted(os.listdir(sections_dir)):
                if not fn.endswith('.toon'):
                    continue
                sid = fn[:-5]
                _, _, rows = read_toon_rows(os.path.join(sections_dir, fn))
                for r in rows:
                    hn = r.get('hadithnumber', '').strip()
                    if not hn:
                        continue
                    r['_section'] = sid
                    hn_map[hn] = r
                    all_hns.append(hn)
        all_hns = sorted(set(all_hns), key=lambda x: (len(x), x))

        # ----- translation maps ----------------------------------------
        # lang -> {(section, hn): text}
        trans_maps = {}
        ar_from_file = False
        for lang in lang_dirs:
            lsec = os.path.join(trans_dir, lang, 'sections')
            m = {}
            if os.path.isdir(lsec):
                for fn in sorted(os.listdir(lsec)):
                    if not fn.endswith('.toon'):
                        continue
                    sid = fn[:-5]
                    _, _, rows = read_toon_rows(os.path.join(lsec, fn))
                    for r in rows:
                        hn = r.get('hadithnumber', '').strip()
                        if hn:
                            m[(sid, hn)] = r.get('text', '')
            trans_maps[lang] = m
            if lang == 'ar' and m:
                ar_from_file = True

        # metadata mismatch: total hadiths
        try:
            declared_total = int(meta.get('total_hadiths', '0'))
        except ValueError:
            declared_total = -1
        if declared_total > 0 and abs(declared_total - len(all_hns)) > max(5, declared_total * 0.02):
            add(book, '', '', 'metadata', 'TOTAL_HADITHS_MISMATCH',
                f'info total_hadiths={declared_total} but actual={len(all_hns)}')

        # language mismatch: declared vs present dirs
        present_set = set(lang_dirs) | {'ar'}
        declared_set = set(declared_langs) | {'ar'}
        missing_dirs = declared_set - present_set
        extra_dirs = present_set - declared_set
        if missing_dirs:
            add(book, '', '', 'metadata', 'LANG_DIR_MISSING',
                f'declared langs without dir: {sorted(missing_dirs)}')
        if extra_dirs:
            add(book, '', '', 'metadata', 'LANG_DIR_EXTRA',
                f'dirs present not declared: {sorted(extra_dirs)}')

        # per-lang metadata total mismatch
        for tb in translations_block:
            lang = tb.get('language', '')
            try:
                mt = int(tb.get('sections', '0'))
            except ValueError:
                mt = -1
            # count actual translation files
            lsec = os.path.join(trans_dir, lang, 'sections')
            actual_sections = 0
            if os.path.isdir(lsec):
                actual_sections = len([fn for fn in os.listdir(lsec) if fn.endswith('.toon')])
            if mt > 0 and mt != actual_sections:
                add(book, '', '', lang, 'TRANS_META_MISMATCH',
                    f'lang {lang} metadata sections={mt} actual={actual_sections}')

        # ----- sample ---------------------------------------------------
        sample_n = min(SAMPLE, len(all_hns))
        sampled = random.sample(all_hns, sample_n) if all_hns else []
        total_sampled += len(sampled)

        # duplicate tracking within this book per lang
        dup_hashes = defaultdict(list)

        for hn in sampled:
            rec = hn_map[hn]
            sid = rec.get('_section', '')
            arabic = rec.get('arabic', '') or ''
            grades = rec.get('grades', '') or ''
            ref = rec.get('reference', '') or ''
            intl = rec.get('international_number', '') or ''
            narrator = rec.get('narrator_chain', '') or ''
            ch_intro = rec.get('chapter_intro', '') or ''

            hadith_rows.append([book, hn, sid, arabic, grades, ref,
                                intl, narrator, ch_intro])

            # ---- arabic checks ----
            if not arabic.strip():
                add(book, sid, hn, 'ar', 'EMPTY_ARABIC', 'arabic text empty')
            elif not AR.search(arabic):
                add(book, sid, hn, 'ar', 'NO_ARABIC_SCRIPT',
                    'arabic field has no arabic characters')
            else:
                latin_ratio = (len(LATIN.findall(arabic)) /
                               max(1, len(arabic)))
                if latin_ratio > 0.5 and len(arabic) > 30:
                    add(book, sid, hn, 'ar', 'LATIN_IN_ARABIC',
                        f'high latin ratio {latin_ratio:.2f} in arabic field')
            for bad_re, itype in ((ZW, 'ZERO_WIDTH'), (HTML, 'HTML_TAGS'),
                                  (CTRL, 'CONTROL_CHARS'),
                                  (MOJIBAKE, 'MOJIBAKE')):
                if bad_re.search(arabic):
                    add(book, sid, hn, 'ar', itype, 'in arabic field')
            if REPLACEMENT in arabic:
                add(book, sid, hn, 'ar', 'REPLACEMENT_CHAR', 'U+FFFD in arabic')

            # ---- per-language translation checks ----
            present_langs = []
            for lang in lang_dirs:
                if lang == 'ar' and ar_from_file:
                    txt = trans_maps['ar'].get((sid, hn), '')
                else:
                    txt = trans_maps[lang].get((sid, hn), '')
                present_langs.append(lang)
                translation_rows.append([book, hn, lang, txt])

                if not txt.strip():
                    # missing if another lang present
                    add(book, sid, hn, lang, 'EMPTY_TRANSLATION',
                        'translation text empty')
                    continue
                for bad_re, itype in ((ZW, 'ZERO_WIDTH'), (HTML, 'HTML_TAGS'),
                                      (CTRL, 'CONTROL_CHARS'),
                                      (MOJIBAKE, 'MOJIBAKE')):
                    if bad_re.search(txt):
                        add(book, sid, hn, lang, itype, f'in {lang} translation')
                if REPLACEMENT in txt:
                    add(book, sid, hn, lang, 'REPLACEMENT_CHAR',
                        f'U+FFFD in {lang}')
                if PLACEHOLDER.match(txt.strip()):
                    add(book, sid, hn, lang, 'PLACEHOLDER',
                        f'placeholder text in {lang}: "{txt.strip()[:60]}"')
                # arabic chars in non-arabic-script translations
                if lang not in ARABIC_SCRIPT_LANGS:
                    ar_chars = AR.findall(txt)
                    non_hon = [c for c in ar_chars if c not in HONOR]
                    if non_hon and len(non_hon) > max(8, len(txt) * 0.10):
                        add(book, sid, hn, lang, 'ARABIC_IN_TRANSLATION',
                            f'{len(non_hon)} arabic chars in {lang} text')
                # truncated relative to arabic
                if arabic.strip() and lang not in ('ar',):
                    if (len(arabic) > 200 and len(txt) < 80 and
                            len(txt) < 0.1 * len(arabic)):
                        add(book, sid, hn, lang, 'TRUNCATED',
                            f'{lang} len {len(txt)} vs arabic {len(arabic)}')
                # duplicate within book/lang
                h = hashlib.md5(txt.encode('utf-8')).hexdigest()
                dup_hashes[(lang, h)].append(hn)

            # missing translation: a lang dir exists but hn absent there
            for lang in lang_dirs:
                if lang == 'ar' and ar_from_file:
                    has = (sid, hn) in trans_maps['ar']
                else:
                    has = (sid, hn) in trans_maps[lang]
                if not has and present_langs:
                    add(book, sid, hn, lang, 'MISSING_TRANSLATION',
                        f'{lang} translation file lacks hadith {hn}')

        # record duplicates (cap 200/book/lang)
        for (lang, h), hns in dup_hashes.items():
            if len(hns) > 1:
                for hn in hns[:200]:
                    add(book, hn_map.get(hn, {}).get('_section', ''), hn,
                        lang, 'DUPLICATE_TEXT',
                        f'identical {lang} text shared by {len(hns)} hadiths')

        n_iss = sum(1 for x in issues if x[0] == book)
        book_issue_counts[book] = n_iss
        book_summaries.append((book, book_name,
                               ','.join(declared_langs) or ','.join(lang_dirs),
                               len(all_hns), len(sampled),
                               len(sections_block), n_iss))
        print(f'  {book}: sampled {len(sampled)}, issues {n_iss}', flush=True)

    # ---- write output --------------------------------------------------
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)

        # audit header
        f.write('audit{version,total_books,total_sampled,total_issues,seed}\n')
        w.writerow(['1', str(len(books)), str(total_sampled),
                    str(len(issues)), str(SEED)])
        f.write('end_audit\n\n')

        # book summary
        f.write('book_summary{id,name,declared_languages,total_hadiths,'
                'sampled,sections,issues}\n')
        for b in book_summaries:
            w.writerow(list(b))
        f.write('end_book_summary\n\n')

        # chapters
        f.write('chapters{book,chapter_id,name,name_ar,name_bn,name_en,'
                'name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,'
                'hadith_last}\n')
        for r in chapter_rows:
            w.writerow(r)
        f.write('end_chapters\n\n')

        # intros
        f.write('intros{book,intro,intro_ar,intro_en,intro_ur,intro_fr,'
                'intro_id,intro_bn,intro_tr,intro_ru,intro_hi,intro_ro,'
                'intro_de,intro_es,intro_sw,intro_ta,intro_te}\n')
        for r in intro_rows:
            w.writerow(r)
        f.write('end_intros\n\n')

        # hadith dump (full content)
        f.write('hadith{book,hadithnumber,section,arabic,grades,reference,'
                'international_number,narrator_chain,chapter_intro}\n')
        for r in hadith_rows:
            w.writerow(r)
        f.write('end_hadith\n\n')

        # translation dump (full text)
        f.write('translation{book,hadithnumber,lang,text}\n')
        for r in translation_rows:
            w.writerow(r)
        f.write('end_translation\n\n')

        # issues
        f.write('issues{total}\n')
        w.writerow([str(len(issues))])
        f.write('end_issues\n\n')

        # breakdown
        bd = Counter(x[4] for x in issues)
        f.write('issue_breakdown{type,count}\n')
        for t, c in sorted(bd.items(), key=lambda kv: -kv[1]):
            w.writerow([t, str(c)])
        f.write('end_issue_breakdown\n\n')

        # details
        f.write('issue_details{book,section,hadithnumber,language,'
                'issue_type,description}\n')
        for x in issues:
            w.writerow(list(x))
        f.write('end_issue_details\n')

    print(f'\nWROTE {OUT}')
    print(f'books={len(books)} sampled={total_sampled} issues={len(issues)}')
    print('breakdown:', dict(bd))


if __name__ == '__main__':
    main()
