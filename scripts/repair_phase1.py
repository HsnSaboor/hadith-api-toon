#!/usr/bin/env python3
"""
Phase 1 mechanical repairs for hadith-api-toon (safe, no external data).

1. ZERO_WIDTH + CONTROL_CHARS  -> strip from every text field in every .toon
   file (sections, translations/*/sections, metadata.toon, info.toon).
2. LANG_DIR_EXTRA              -> set info.toon `available_languages` to the
   union of translation dirs actually present (fixes undeclared langs).
3. Metadata reconciliation      -> set info.toon `total_hadiths` to the actual
   hadith count; set each translation `metadata.toon` `total_hadiths` to the
   actual row count. (The audit's TRANS_META_MISMATCH on the `sections` field
   is a false positive -- `sections` = section-FILE count, which is correct.)
4. EMPTY_CHAPTER_NAME          -> backfill chapter `name` from `name_ar`
   (then name_en) when empty.

Usage:
    python3 scripts/repair_phase1.py            # dry run (report only)
    python3 scripts/repair_phase1.py --apply     # write changes
"""
import os, re, csv, io, sys

BASE = "/home/saboor/code/hadith-api-toon"
EDITIONS = os.path.join(BASE, "editions")
APPLY = "--apply" in sys.argv

ZW = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]')
CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
BLOCK_RE = re.compile(r'^([A-Za-z_]+)\[\w+\]\{(.*?)\}\s*:', re.DOTALL)


def sanitize(s):
    return ZW.sub('', CTRL.sub('', s))


def read_rows(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    m = BLOCK_RE.search(text)
    if not m:
        return None, []
    fields = [x.strip() for x in m.group(2).split(',')]
    rows = []
    for r in csv.reader(text[m.end():].split('\n')):
        if not r:
            continue
        if len(r) < len(fields):
            r = r + [''] * (len(fields) - len(r))
        rows.append(dict(zip(fields, r)))
    return fields, rows


def count_rows(path):
    f, rows = read_rows(path)
    return len(rows) if f else 0


def set_meta_value(lines, key, newval):
    pat = re.compile(r'^(\s*' + re.escape(key) +
                     r'\s*:\s*)(?:"([^"]*)"|(\S*))(\s*)$')
    for i, l in enumerate(lines):
        mm = pat.match(l)
        if mm:
            old = mm.group(2) if mm.group(2) is not None else mm.group(3)
            if old == newval:
                return False
            if mm.group(2) is not None:
                lines[i] = mm.group(1) + '"' + newval + '"' + mm.group(4)
            else:
                lines[i] = mm.group(1) + newval + mm.group(4)
            return True
    return False


def row_to_line(d, flds):
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_ALL).writerow([d.get(f, '') for f in flds])
    return buf.getvalue().rstrip('\n')


def rewrite_block(lines, blockname, transform):
    """Rewrite data rows of the named block in `lines` (mutates in place).
    transform(d, flds) -> True if it changed the row. Returns # changed rows."""
    for i, l in enumerate(lines):
        if re.match(r'^' + re.escape(blockname) + r'\[\w+\]\{', l):
            fm = re.search(r'\{(.*?)\}\s*:', l, re.DOTALL)
            flds = [x.strip() for x in fm.group(1).split(',')] if fm else []
            j = i + 1
            rows = []
            while (j < len(lines) and lines[j].strip() and
                   not re.match(r'^[A-Za-z_]+\[\w+\]\{', lines[j]) and
                   not re.match(r'^metadata\s*:', lines[j])):
                r = next(csv.reader([lines[j]]))
                if len(r) < len(flds):
                    r = r + [''] * (len(flds) - len(r))
                rows.append(dict(zip(flds, r)))
                j += 1
            changed = 0
            for d in rows:
                if transform(d, flds):
                    changed += 1
            lines[i + 1:j] = [row_to_line(d, flds) for d in rows]
            return changed
    return 0


def main():
    stats = {'sanitized': 0, 'avail_lang': 0, 'info_total': 0,
             'chap_backfill': 0, 'trans_total': 0, 'written': 0}
    books = sorted(d for d in os.listdir(EDITIONS)
                   if os.path.isdir(os.path.join(EDITIONS, d)) and
                   os.path.exists(os.path.join(EDITIONS, d, 'info.toon')))

    # ---- precompute maps ----
    book_total, book_dirs, lang_rows = {}, {}, {}
    for book in books:
        bpath = os.path.join(EDITIONS, book)
        sdir = os.path.join(bpath, 'sections')
        tot = 0
        if os.path.isdir(sdir):
            for fn in os.listdir(sdir):
                if fn.endswith('.toon'):
                    tot += count_rows(os.path.join(sdir, fn))
        book_total[book] = tot
        tdir = os.path.join(bpath, 'translations')
        dirs = (sorted(d for d in os.listdir(tdir)
                       if os.path.isdir(os.path.join(tdir, d)))
                if os.path.isdir(tdir) else [])
        book_dirs[book] = dirs
        for lang in dirs:
            lsec = os.path.join(tdir, lang, 'sections')
            cnt = 0
            if os.path.isdir(lsec):
                for fn in os.listdir(lsec):
                    if fn.endswith('.toon'):
                        cnt += count_rows(os.path.join(lsec, fn))
            lang_rows[(book, lang)] = cnt

    # ---- process every .toon file (sanitize) ----
    for root, _, files in os.walk(EDITIONS):
        for fn in files:
            if not fn.endswith('.toon'):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding='utf-8') as f:
                text = f.read()
            newtext = sanitize(text)
            is_info = fn == 'info.toon'
            is_tmeta = fn == 'metadata.toon'
            changed = newtext != text

            book = os.path.relpath(root, EDITIONS).split(os.sep)[0]
            if is_info:
                lines = newtext.split('\n')
                # available_languages
                av = ','.join(book_dirs[book])
                if set_meta_value(lines, 'available_languages', av):
                    stats['avail_lang'] += 1
                # total_hadiths
                if set_meta_value(lines, 'total_hadiths', str(book_total[book])):
                    stats['info_total'] += 1
                # chapter name backfill
                n = rewrite_block(lines, 'sections', _chap_backfill)
                stats['chap_backfill'] += n
                newtext = '\n'.join(lines)
                changed = newtext != text
            elif is_tmeta:
                lang = os.path.basename(root)
                lines = newtext.split('\n')
                if set_meta_value(lines, 'total_hadiths',
                                  str(lang_rows.get((book, lang), 0))):
                    stats['trans_total'] += 1
                newtext = '\n'.join(lines)
                changed = newtext != text

            if changed:
                stats['sanitized'] += 1
                if APPLY:
                    with open(path, 'w', encoding='utf-8', newline='') as f:
                        f.write(newtext)
                    stats['written'] += 1

    print('DRY-RUN' if not APPLY else 'APPLIED')
    print(' files with any change :', stats['sanitized'])
    print('   written to disk     :', stats['written'])
    print(' info.toon avail_lang  :', stats['avail_lang'])
    print(' info.toon total_hadith:', stats['info_total'])
    print(' chapter names backfd  :', stats['chap_backfill'], 'rows')
    print(' trans metadata total  :', stats['trans_total'])


def _chap_backfill(d, flds):
    if not d.get('name', '').strip():
        for src in ('name_ar', 'name_en', 'name_ur'):
            if d.get(src, '').strip():
                d['name'] = d[src]
                return True
    return False


if __name__ == '__main__':
    main()
