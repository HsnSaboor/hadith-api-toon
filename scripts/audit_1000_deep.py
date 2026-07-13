#!/usr/bin/env python3
"""
Lite audit for hadith-api-toon — full text, reduced sample count.
Keeps output under 900K tokens by sampling ~25 hadiths per book.
NO text truncation — all arabic, translations, chapter names, intros are full.
"""
import os, re, csv, random, hashlib, sys, io
from collections import defaultdict, Counter

BASE = "/home/saboor/code/hadith-api-toon"
EDITIONS = os.path.join(BASE, "editions")
OUT = os.path.join(BASE, "audit_1000_deep.toon.md")
SEED = 42
SAMPLE = 10  # Reduced to keep strictly under 800K tokens with full text (per user request)

# ---- regex helpers -------------------------------------------------------
ZW = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]')
HTML_RE = re.compile(r'<[^>]+>')
CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
AR = re.compile(r'[\u0600-\u06ff\ufe70-\ufefe\u0750-\u077f]')
LATIN = re.compile(r'[A-Za-z]')
HONOR = set('\ufdfa\ufdfb\ufdfc\ufdfd\ufdfe\ufeffﷺﷻﵞ')
PLACEHOLDER = re.compile(
    r'^(same as|similar to|as above|see (the )?hadith|narration about|'
    r'wrong same as|\.\.\.\\s*$|\(as hadith|refer to hadith|same\b|see above|'
    r'mentioned above|same hadith)', re.I)
MOJIBAKE = re.compile(r'Ã.|â€|ï¿½|â€™|â€œ|â€\x9d|�')
REPLACEMENT = '\ufffd'
ARABIC_SCRIPT_LANGS = {'ar', 'ur', 'fa', 'ps'}


def read_toon_rows(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'^([A-Za-z_]+)\[(\w+)\]\{(.*?)\}\s*:', text, re.DOTALL)
    if not m:
        return None, [], []
    name = m.group(1)
    fields = [x.strip() for x in m.group(3).split(',')]
    rest = text[m.end():]
    reader = csv.reader(io.StringIO(rest))
    rows = []
    for r in reader:
        if not r:
            continue
        if len(r) < len(fields):
            r = r + [''] * (len(fields) - len(r))
        rows.append(dict(zip(fields, r)))
    return name, fields, rows


def parse_info(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    meta = {}
    translations = []
    sections = []

    meta_match = re.search(r'^metadata\s*:\s*\n(.*?)(?=\n[A-Za-z_]+\[|\Z)', text, re.DOTALL | re.MULTILINE)
    if meta_match:
        meta_block = meta_match.group(1)
        lines = meta_block.split('\n')
        current_key = None
        current_val = []
        in_quote = False
        for line in lines:
            if not line.strip() and not in_quote:
                continue
            if not in_quote:
                m = re.match(r'^\s*([A-Za-z_]+)\s*:\s*(.*)$', line)
                if m:
                    if current_key:
                        meta[current_key] = "\n".join(current_val).strip()
                    current_key = m.group(1)
                    val_part = m.group(2).strip()
                    if val_part.startswith('"'):
                        in_quote = True
                        cleaned = val_part.replace('\\"', '').replace('""', '')
                        if cleaned.count('"') % 2 == 0:
                            in_quote = False
                            if val_part.endswith('"'):
                                val_part = val_part[1:-1]
                        else:
                            val_part = val_part[1:]
                    current_val = [val_part]
                else:
                    if current_key:
                        current_val.append(line)
            else:
                cleaned = line.replace('\\"', '').replace('""', '')
                if cleaned.count('"') % 2 == 1:
                    in_quote = False
                    val_part = line.strip()
                    if val_part.endswith('"'):
                        val_part = val_part[:-1]
                    current_val.append(val_part)
                else:
                    current_val.append(line)
        if current_key:
            meta[current_key] = "\n".join(current_val).strip()

    blocks = re.finditer(r'^([A-Za-z_]+)\[\w+\]\{(.*?)\}\s*:', text, re.DOTALL | re.MULTILINE)
    block_positions = []
    for b in blocks:
        block_positions.append((b.group(1), b.group(2), b.start(), b.end()))
    for idx, (b_name, b_fields_str, b_start, b_end) in enumerate(block_positions):
        fields = [x.strip() for x in b_fields_str.split(',')]
        content_start = b_end
        content_end = block_positions[idx+1][2] if idx + 1 < len(block_positions) else len(text)
        block_text = text[content_start:content_end].strip()
        reader = csv.reader(io.StringIO(block_text))
        parsed = []
        for r in reader:
            if not r:
                continue
            if len(r) < len(fields):
                r = r + [''] * (len(fields) - len(r))
            parsed.append(dict(zip(fields, r)))
        if b_name == 'translations':
            translations = parsed
        elif b_name == 'sections':
            sections = parsed
    return meta, translations, sections


issues = []

def add(book, section, hn, lang, itype, desc):
    issues.append((book, section, str(hn), lang or '', itype, desc[:300]))


def main():
    random.seed(SEED)
    books = sorted(d for d in os.listdir(EDITIONS)
                   if os.path.isdir(os.path.join(EDITIONS, d)) and
                   os.path.exists(os.path.join(EDITIONS, d, 'info.toon')))

    total_sampled = 0
    book_summaries = []
    chapter_rows = []
    intro_rows = []
    hadith_rows = []
    translation_rows = []
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
            info_langs = sorted(tb.get('language', '') for tb in translations_block if tb.get('language'))
            lang_dirs = sorted(d for d in info_langs
                               if os.path.isdir(os.path.join(trans_dir, d)))
        else:
            lang_dirs = []

        # chapters - full text
        for ch in sections_block:
            row = [book, ch.get('id', ''), ch.get('name', '')]
            for f in ('name_ar', 'name_bn', 'name_en', 'name_fr', 'name_id',
                      'name_ru', 'name_tr', 'name_ur'):
                row.append(ch.get(f, ''))
            row += [ch.get('hadith_first', ''), ch.get('hadith_last', '')]
            chapter_rows.append(row)

        # intros - full text
        intro = meta.get('intro', '')
        irow = [book, intro]
        for f in ('intro_ar', 'intro_en', 'intro_ur', 'intro_fr', 'intro_id',
                  'intro_bn', 'intro_tr', 'intro_ru', 'intro_hi', 'intro_ro',
                  'intro_de', 'intro_es', 'intro_sw', 'intro_ta', 'intro_te'):
            irow.append(meta.get(f, ''))
        intro_rows.append(irow)

        # collect ALL hadiths (for issue detection across full book)
        hn_map = {}
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

        # translation maps
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

        empty_langs = set()
        for lang, m in trans_maps.items():
            non_empty_count = sum(1 for val in m.values() if val.strip())
            if len(all_hns) > 0 and (non_empty_count / len(all_hns)) < 0.95:
                empty_langs.add(lang)

        # metadata checks
        try:
            declared_total = int(meta.get('total_hadiths', '0'))
        except ValueError:
            declared_total = -1
        if declared_total > 0 and abs(declared_total - len(all_hns)) > max(5, declared_total * 0.02):
            add(book, '', '', 'metadata', 'TOTAL_HADITHS_MISMATCH',
                f'info total_hadiths={declared_total} but actual={len(all_hns)}')

        # sample - reduced count but FULL text
        sample_n = min(SAMPLE, len(all_hns))
        sampled = random.sample(all_hns, sample_n) if all_hns else []
        total_sampled += len(sampled)

        dup_hashes = defaultdict(list)

        for hn in sampled:
            rec = hn_map[hn]
            sid = rec.get('_section', '')
            arabic = rec.get('arabic', '') or rec.get('text', '') or ''
            grades = rec.get('grades', '') or ''
            ref = rec.get('reference', '') or ''
            intl = rec.get('international_number', '') or ''
            narrator = rec.get('narrator_chain', '') or ''
            ch_intro = rec.get('chapter_intro', '') or ''

            # Full text - no truncation
            hadith_rows.append([book, hn, sid, arabic, grades, ref,
                                intl, narrator, ch_intro])

            # arabic checks
            if not arabic.strip():
                add(book, sid, hn, 'ar', 'EMPTY_ARABIC', 'arabic text empty')
            elif not AR.search(arabic):
                add(book, sid, hn, 'ar', 'NO_ARABIC_SCRIPT',
                    'arabic field has no arabic characters')
            for bad_re, itype in ((ZW, 'ZERO_WIDTH'), (HTML_RE, 'HTML_TAGS'),
                                  (CTRL, 'CONTROL_CHARS'), (MOJIBAKE, 'MOJIBAKE')):
                if bad_re.search(arabic):
                    add(book, sid, hn, 'ar', itype, 'in arabic field')
            if REPLACEMENT in arabic:
                add(book, sid, hn, 'ar', 'REPLACEMENT_CHAR', 'U+FFFD in arabic')

            # translation checks - full text
            for lang in lang_dirs:
                txt = trans_maps[lang].get((sid, hn), '')
                # Full text in output
                translation_rows.append([book, hn, lang, txt])

                if not txt.strip():
                    if lang not in empty_langs:
                        add(book, sid, hn, lang, 'EMPTY_TRANSLATION',
                            'translation text empty')
                    continue
                for bad_re, itype in ((ZW, 'ZERO_WIDTH'), (HTML_RE, 'HTML_TAGS'),
                                      (CTRL, 'CONTROL_CHARS'), (MOJIBAKE, 'MOJIBAKE')):
                    if bad_re.search(txt):
                        add(book, sid, hn, lang, itype, f'in {lang} translation')
                if REPLACEMENT in txt:
                    add(book, sid, hn, lang, 'REPLACEMENT_CHAR', f'U+FFFD in {lang}')
                if PLACEHOLDER.match(txt.strip()):
                    add(book, sid, hn, lang, 'PLACEHOLDER',
                        f'placeholder text in {lang}: "{txt.strip()[:60]}"')
                if lang not in ARABIC_SCRIPT_LANGS:
                    ar_chars = AR.findall(txt)
                    non_hon = [c for c in ar_chars if c not in HONOR]
                    if non_hon and len(non_hon) > max(8, len(txt) * 0.10):
                        add(book, sid, hn, lang, 'ARABIC_IN_TRANSLATION',
                            f'{len(non_hon)} arabic chars in {lang} text')
                if arabic.strip() and lang not in ('ar',):
                    if (len(arabic) > 200 and len(txt) < 80 and
                            len(txt) < 0.1 * len(arabic)):
                        is_citation = (
                            "گذشتہ حدیث" in txt or "مروی ہے" in txt or
                            "حسب سابق" in txt or "پچھلی حدیث" in txt or
                            any(w in txt.lower() for w in ["same as", "as above", "similar to", "refer to", "narrated"])
                        )
                        if not is_citation:
                            add(book, sid, hn, lang, 'TRUNCATED',
                                f'{lang} len {len(txt)} vs arabic {len(arabic)}')
                if txt.strip():
                    h = hashlib.md5(txt.encode('utf-8')).hexdigest()
                    dup_hashes[(lang, h)].append(hn)

            for lang in lang_dirs:
                if lang in empty_langs:
                    continue
                if (sid, hn) not in trans_maps.get(lang, {}):
                    add(book, sid, hn, lang, 'MISSING_TRANSLATION',
                        f'{lang} translation file lacks hadith {hn}')

        # duplicates
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

        f.write('audit{version,total_books,total_sampled,total_issues,seed}\n')
        w.writerow(['2-lite-fulltext', str(len(books)), str(total_sampled),
                     str(len(issues)), str(SEED)])
        f.write('end_audit\n\n')

        f.write('book_summary{id,name,declared_languages,total_hadiths,'
                'sampled,sections,issues}\n')
        for b in book_summaries:
            w.writerow(list(b))
        f.write('end_book_summary\n\n')

        f.write('chapters{book,chapter_id,name,name_ar,name_bn,name_en,'
                'name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,'
                'hadith_last}\n')
        for r in chapter_rows:
            w.writerow(r)
        f.write('end_chapters\n\n')

        f.write('intros{book,intro,intro_ar,intro_en,intro_ur,intro_fr,'
                'intro_id,intro_bn,intro_tr,intro_ru,intro_hi,intro_ro,'
                'intro_de,intro_es,intro_sw,intro_ta,intro_te}\n')
        for r in intro_rows:
            w.writerow(r)
        f.write('end_intros\n\n')

        f.write('hadith{book,hadithnumber,section,arabic,grades,reference,'
                'international_number,narrator_chain,chapter_intro}\n')
        for r in hadith_rows:
            w.writerow(r)
        f.write('end_hadith\n\n')

        f.write('translation{book,hadithnumber,lang,text}\n')
        for r in translation_rows:
            w.writerow(r)
        f.write('end_translation\n\n')

        f.write('issues{total}\n')
        w.writerow([str(len(issues))])
        f.write('end_issues\n\n')

        bd = Counter(x[4] for x in issues)
        f.write('issue_breakdown{type,count}\n')
        for t, c in sorted(bd.items(), key=lambda kv: -kv[1]):
            w.writerow([t, str(c)])
        f.write('end_issue_breakdown\n\n')

        f.write('issue_details{book,section,hadithnumber,language,'
                'issue_type,description}\n')
        for x in issues:
            w.writerow(list(x))
        f.write('end_issue_details\n')

    size_bytes = os.path.getsize(OUT)
    est_tokens = size_bytes // 4
    print(f'\nWROTE {OUT}')
    print(f'Size: {size_bytes:,} bytes (~{est_tokens:,} tokens)')
    print(f'books={len(books)} sampled={total_sampled} issues={len(issues)}')
    print('breakdown:', dict(bd))


if __name__ == '__main__':
    main()
