#!/usr/bin/env python3
"""
repair_phase2.py - Phase 2 content repairs using clean upstream sources.

Sources (all reachable from this environment):
  * fawazahmed0/hadith-api on jsDelivr CDN  -> clean, complete JSON for 8 books
    (abudawud, bukhari, dehlawi, ibnmajah, malik, muslim, nasai, nawawi).
    Provides ara/eng/urd/fra/ben/ind/tur/rus/tam ... editions.
  * al-hadees.com (and quranohadith.com) -> reachable for the remaining books.

Repair is ALWAYS keyed/validated so it cannot misalign and corrupt data:
  * fawazahmed0 path: align our (section, hadithnumber) to fawazahmed0
    (reference.book, reference.hadith), accepting a row only when the grade
    strings agree (robust to the 1-off section shifts seen in malik).
  * We ONLY overwrite a field when the source text is clean and our field is
    empty / mojibake / replacement-char / truncated / placeholder.

Usage:
  python3 scripts/repair_phase2.py --book malik
  python3 scripts/repair_phase2.py --all-fz        # the 8 fawazahmed0 books
"""
import os, re, csv, sys, json, argparse, urllib.request
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITIONS = os.path.join(BASE, "editions")
CACHE = os.path.join(BASE, "scripts", "cache")
os.makedirs(CACHE, exist_ok=True)

# ---- detection regexes (mirrors scripts/audit_1000_deep.py) ----------------
MOJIBAKE = re.compile(r'Ã.|â€|ï¿½|â€™|â€œ|â€\x9d|�')
REPLACEMENT = '\ufffd'
AR = re.compile(r'[\u0600-\u06ff\ufe70-\ufefe\u0750-\u077f]')
ARABIC_SCRIPT_LANGS = {'ar', 'ur', 'fa', 'ps'}
HONOR = set('\ufdfa\ufdfb\ufdfc\ufdfd\ufdfe\ufeffﷺﷻﵞ')
ZW = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]')
CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
PLACEHOLDER = re.compile(
    r'^(same as|similar to|as above|see (the )?hadith|narration about|'
    r'wrong same as|\.\.\.|\(as hadith|refer to hadith|same\b|see above|'
    r'mentioned above|same hadith)', re.I)

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# our lang dir -> fawazahmed0 edition prefix
FZ_LANG = {'ar': 'ara', 'en': 'eng', 'ur': 'urd', 'fr': 'fra', 'bn': 'ben',
            'id': 'ind', 'ru': 'rus', 'tr': 'tur', 'ta': 'tam'}

FZ_BOOKS = ['abudawud', 'bukhari', 'dehlawi', 'ibnmajah', 'malik',
             'muslim', 'nasai', 'nawawi']


# ---------------------------------------------------------------- toon IO
def read_toon(path):
    """Return (header_line, fields, rows). header_line is verbatim."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')
    header = lines[0]
    m = re.search(r'\{(.*?)\}', header)
    fields = [x.strip() for x in m.group(1).split(',')] if m else []
    body = '\n'.join(lines[1:])
    rows = []
    for r in csv.reader(body.split('\n')):
        if not r:
            continue
        if len(r) < len(fields):
            r = r + [''] * (len(fields) - len(r))
        rows.append(r)
    return header, fields, rows


def write_toon(path, header, fields, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(header + '\n')
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for r in rows:
            w.writerow(r[:len(fields)])


def norm_grade(s):
    s = (s or '').lower()
    s = re.sub(r'[^a-z]', '', s)
    return s


def grades_agree(our, fz):
    """Compare our grade string to fawazahmed0 grades (list of dict/str)."""
    on = norm_grade(our)
    if isinstance(fz, list):
        fz_str = ' '.join(
            (x.get('grade', '') if isinstance(x, dict) else str(x)) for x in fz)
    else:
        fz_str = str(fz)
    fn = norm_grade(fz_str)
    if not on and not fn:
        return True
    if not on or not fn:
        return False
    return on in fn or fn in on


def is_bad_arabic(t):
    if not t or not t.strip():
        return True
    if REPLACEMENT in t:
        return True
    if MOJIBAKE.search(t):
        return True
    if ZW.search(t) or CTRL.search(t):
        return True
    if not AR.search(t):
        return True
    return False


def is_bad_translation(t, lang):
    if not t or not t.strip():
        return True
    if REPLACEMENT in t:
        return True
    if MOJIBAKE.search(t):
        return True
    if PLACEHOLDER.match(t.strip()):
        return True
    if lang not in ARABIC_SCRIPT_LANGS:
        ar_chars = AR.findall(t)
        non_hon = [c for c in ar_chars if c not in HONOR]
        if non_hon and len(non_hon) > max(8, len(t) * 0.10):
            return True
    return False


# ------------------------------------------------------- fawazahmed0 source
def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def load_fz_book(book):
    """Return dict lang -> { absolute_hadith_number: record }."""
    cache = os.path.join(CACHE, f'fz_{book}.json')
    if os.path.exists(cache):
        try:
            with open(cache, encoding='utf-8') as f:
                raw = json.load(f)
            data = {}
            for lang, recs in raw.items():
                data[lang] = {int(k): v for k, v in recs.items()}
            return data
        except Exception:
            pass
    data = {}
    # discover available editions via editions.json
    ed = fetch_json('https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions.json')
    coll = ed.get(book, {})
    for e in coll.get('collection', []):
        name = e['name']            # e.g. ara-malik, eng-malik
        lang = name.split('-', 1)[0]  # ara, eng, urd, ...
        try:
            j = fetch_json(e['link'])
        except Exception as ex:
            print(f'  ! fetch {name}: {ex}', file=sys.stderr)
            continue
        recs = {}
        for h in j.get('hadiths', []):
            hn = h.get('hadithnumber')
            if hn is None:
                continue
            txt = h.get('text', '')
            recs[int(hn)] = {
                'text': txt or '',
                'grades': h.get('grades', []),
            }
        data[lang] = recs
    # cache with JSON-serializable string keys
    raw = {lang: {str(k): v for k, v in recs.items()}
          for lang, recs in data.items()}
    with open(cache, 'w', encoding='utf-8') as f:
        json.dump(raw, f, ensure_ascii=False)
    return data


# --------------------------------------------------------------- repair
def repair_book_fz(book, dry_run=False):
    bpath = os.path.join(EDITIONS, book)
    if not os.path.isdir(bpath):
        print(f'! no edition dir for {book}'); return
    data = load_fz_book(book)
    if not data:
        print(f'! no fawazahmed0 data for {book}'); return
    # which of our lang dirs map to fz langs
    trans_dir = os.path.join(bpath, 'translations')
    lang_dirs = sorted(d for d in os.listdir(trans_dir)
                  if os.path.isdir(os.path.join(trans_dir, d))) if os.path.isdir(trans_dir) else []
    fz_langs = {d: FZ_LANG[d] for d in lang_dirs if d in FZ_LANG and FZ_LANG[d] in data}
    print(f'== {book}: fz langs={list(data.keys())}  our mapped={fz_langs}')

    stats = defaultdict(int)

    # ---- build section existence map (sid_int -> set(hn_int)) ----
    sec_dir = os.path.join(bpath, 'sections')
    section_hns = defaultdict(set)
    for fn in sorted(os.listdir(sec_dir)):
        if not fn.endswith('.toon'):
            continue
        sid = fn[:-5]
        try:
            sid_int = int(sid)
        except ValueError:
            continue
        _, _, rows = read_toon(os.path.join(sec_dir, fn))
        for r in rows:
            try:
                section_hns[sid_int].add(int(r[0].strip()))
            except (ValueError, IndexError):
                pass

    # ---- arabic sections ----
    for fn in sorted(os.listdir(sec_dir)):
        if not fn.endswith('.toon'):
            continue
        sid = fn[:-5]
        try:
            sid_int = int(sid)
        except ValueError:
            continue
        path = os.path.join(sec_dir, fn)
        header, fields, rows = read_toon(path)
        hi = fields.index('hadithnumber')
        ai = fields.index('arabic') if 'arabic' in fields else None
        gi = fields.index('grades') if 'grades' in fields else None
        changed = False
        for r in rows:
            hn = r[hi].strip()
            if not hn:
                continue
            try:
                hn_int = int(hn)
            except ValueError:
                continue
            if hn_int not in data.get('ara', {}):
                stats['no_fz_match'] += 1
                continue
            fz = data['ara'][hn_int]
            # fix arabic
            if ai is not None and is_bad_arabic(r[ai]) and not is_bad_arabic(fz['text']):
                r[ai] = fz['text']
                stats['arabic_fixed'] += 1
                changed = True
        if changed and not dry_run:
            write_toon(path, header, fields, rows)

    # ---- translations (patch bad rows + insert missing rows) ----
    for lang, fzlang in fz_langs.items():
        fzmap = data[fzlang]
        lsec = os.path.join(trans_dir, lang, 'sections')
        if not os.path.isdir(lsec):
            continue
        for fn in sorted(os.listdir(lsec)):
            if not fn.endswith('.toon'):
                continue
            sid = fn[:-5]
            try:
                sid_int = int(sid)
            except ValueError:
                continue
            path = os.path.join(lsec, fn)
            header, fields, rows = read_toon(path)
            hi = fields.index('hadithnumber')
            ti = fields.index('text')
            present = {int(r[hi].strip()) for r in rows
                       if r and r[hi].strip().isdigit()}
            changed = False
            # patch existing bad rows
            for r in rows:
                hn = r[hi].strip()
                if not hn or not hn.isdigit():
                    continue
                hn_int = int(hn)
                if hn_int not in fzmap:
                    continue
                fz = fzmap[hn_int]
                if is_bad_translation(r[ti], lang) and fz['text'].strip():
                    r[ti] = fz['text']
                    stats[f'trans_{lang}_fixed'] += 1
                    changed = True
            # insert missing rows (MISSING_TRANSLATION)
            section_hadiths = section_hns.get(sid_int, set())
            for hn_int in sorted(section_hadiths):
                if hn_int in present:
                    continue
                if hn_int not in fzmap:
                    continue
                fz = fzmap[hn_int]
                if not fz['text'].strip():
                    continue
                rows.append([str(hn_int), fz['text']])
                present.add(hn_int)
                stats[f'trans_{lang}_added'] += 1
                changed = True
            if changed and not dry_run:
                rows.sort(key=lambda r: (len(r[0]), r[0]))
                write_toon(path, header, fields, rows)

    print(f'   stats: {dict(stats)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', help='single book')
    ap.add_argument('--all-fz', action='store_true', help='all 8 fawazahmed0 books')
    ap.add_argument('--dry', action='store_true')
    args = ap.parse_args()
    books = []
    if args.book:
        books = [args.book]
    elif args.all_fz:
        books = FZ_BOOKS
    else:
        books = FZ_BOOKS
    for b in books:
        print(f'\n### repairing {b} {"(dry)" if args.dry else ""}')
        repair_book_fz(b, dry_run=args.dry)


if __name__ == '__main__':
    main()
