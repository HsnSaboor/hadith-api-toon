#!/usr/bin/env python3
"""
Comprehensive .toon integrity scanner.
Detects 30+ issue categories across all editions.
Output: JSON to stdout (issues) + summary to stderr.
"""
import os, re, sys, json, collections

EDITIONS_DIR = "/home/saboor/code/hadith-api-toon/editions"

# Languages we expect, with unicode range hints for script-mismatch detection.
# lang -> (name, set of allowed primary scripts by unicode block, hint sample)
LANGS = {
    "ar":   ("Arabic",      [(0x0600,0x06FF),(0x0750,0x077F),(0x08A0,0x08FF),(0xFB50,0xFDFF),(0xFE70,0xFEFF)]),
    "bn":   ("Bengali",     [(0x0980,0x09FF)]),
    "en":   ("Latin",       [(0x0000,0x007F)]),  # ascii; also allow latin-1 supplement
    "fr":   ("Latin",       [(0x0000,0x007F),(0x00C0,0x024F)]),
    "hi":   ("Devanagari",  [(0x0900,0x097F)]),
    "id":   ("Latin",       [(0x0000,0x007F)]),
    "ru":   ("Cyrillic",    [(0x0400,0x04FF)]),
    "ta":   ("Tamil",       [(0x0B80,0x0BFF)]),
    "tr":   ("Latin",       [(0x0000,0x007F),(0x00C0,0x024F)]),
    "ur":   ("Arabic",      [(0x0600,0x06FF),(0x0750,0x077F),(0xFB50,0xFDFF)]),
    "roman-ur": ("Latin",   [(0x0000,0x007F)]),
}

AI_LEAKAGE = re.compile(r'(?i)\b(here is the translation|sure[,!]|i apologize|as an ai|i am an ai|note:|translation:|translate the following|certainly[,!]|of course[,!]|let me know|is there anything else|in summary|to summarize|hope this helps|please note|kindly note|below is|the following is|original arabic|source:|rahimahullah translation|this hadith|chapter \d+\b|\[translation\]|\[placeholder\]|\[?\bTODO\b\]?|\bN/A\b|\bTBD\b)\b')

MARKDOWN = re.compile(r'(\*\*|`|\[([^\]]+)\]\([^)]+\)|^#{1,6}\s|^\s*[-*]\s+|\b__[^_]+__\b)')

# Leading ordinal pollution: a number/digit prefix at start of text that duplicates hadithnumber.
# e.g. text starts with "6." or "৬." or "(6)" then real text.
LEADING_ORDINAL = re.compile(r'^\s*(\d{1,4})\s*[.\-):]\s+')  # ascii digits leading

PLACEHOLDER = re.compile(r'(?i)(^|\s)(\?{2,}|—{2,}|\.{5,}|\bN/?A\b|\bTBD\b|\bTODO\b|\bPLACEHOLDER\b|lorem ipsum)(\s|$)')

def in_block(ch, blocks):
    o = ord(ch)
    for lo,hi in blocks:
        if lo <= o <= hi:
            return True
    return False

def detect_script(text):
    """Return dominant script name among known ones, ignoring ASCII punctuation/digits/spaces."""
    counts = collections.Counter()
    for ch in text:
        if ch.isspace() or ch in '.,!?;:\'"-()[]{}/\\0123456789…—–-':
            continue
        for name, blocks in [("Arabic",[(0x0600,0x06FF),(0x0750,0x077F),(0x08A0,0x08FF),(0xFB50,0xFDFF),(0xFE70,0xFEFF)]),
                             ("Bengali",[(0x0980,0x09FF)]),
                             ("Devanagari",[(0x0900,0x097F)]),
                             ("Cyrillic",[(0x0400,0x04FF)]),
                             ("Tamil",[(0x0B80,0x0BFF)]),
                             ("Latin",[(0x00C0,0x024F)]),
                             ("ArabicPresentation",[(0xFB50,0xFDFF)])]:
            if in_block(ch, blocks):
                counts[name]+=1
                break
    if not counts:
        return None
    return counts.most_common(1)[0][0]

HEADER_RE = re.compile(r'^(\w+)\[([^\]]+)\]\{([^}]*)\}:?\s*$')
HEADER_COUNT_FIELD_RE = re.compile(r'^hadiths\[(\d+|count)\]\{([^}]*)\}:?\s*$')

def parse_row(line):
    """Parse a CSV-ish quoted row: 'a","b","c'. Return list of field strings (without surrounding quotes) or None on failure.
    Rows are like: "1","text..."","Sahih","ref","intl","chain","intro"
    Note inner escaped quotes appear as ""."""
    s = line.strip()
    if not s.startswith('"'):
        return None
    # Strip leading and trailing quote
    if not (s.endswith('"') or s.endswith('",')):
        # tolerate trailing junk
        pass
    fields = []
    # Walk: state machine. fields separated by ",". quotes doubled inside.
    i = 0
    n = len(s)
    cur = []
    in_field = False
    expect_sep = False
    while i < n:
        ch = s[i]
        if not in_field:
            if ch == '"':
                in_field = True
                i += 1
                continue
            elif ch == ',':
                fields.append(''.join(cur)); cur=[]; i+=1; continue
            elif ch in ' \t':
                i += 1; continue
            else:
                # unexpected char outside field
                return None
        else:
            if ch == '"':
                # check for escaped quote
                if i+1 < n and s[i+1] == '"':
                    cur.append('"'); i += 2; continue
                # end of field
                in_field = False
                fields.append(''.join(cur)); cur=[]
                i += 1
                expect_sep = True
                continue
            else:
                cur.append(ch); i += 1; continue
    if in_field:
        fields.append(''.join(cur))
    return fields

def is_ar_source(path):
    parts = path.split(os.sep)
    return parts and parts[-1] != 'info.toon' and 'translations' not in parts

def extract_edition_lang(path):
    rel = os.path.relpath(path, EDITIONS_DIR)
    parts = rel.split(os.sep)
    edition = parts[0]
    lang = None
    if len(parts) >= 4 and parts[1] == 'translations' and parts[3] == 'sections':
        lang = parts[2]
    return edition, lang

issues = []
stats = collections.Counter()

def add(kind, path, line, detail, severity="M"):
    issues.append({"kind": kind, "file": path, "line": int(line) if line else 0,
                    "detail": (detail[:240] if isinstance(detail,str) else detail), "sev": severity})
    stats[kind] += 1

all_toon = []
for root, dirs, files in os.walk(EDITIONS_DIR):
    for f in files:
        if f.endswith('.toon'):
            all_toon.append(os.path.join(root, f))

print(f"scanning {len(all_toon)} files", file=sys.stderr)

# Track per-section expected for cross-file checks
section_files = collections.defaultdict(list)  # (edition, lang) -> [filepath]
info_files = {}

for path in sorted(all_toon):
    rel = os.path.relpath(path, EDITIONS_DIR)
    edition, lang = extract_edition_lang(path)
    try:
        with open(path, 'rb') as bf:
            raw = bf.read()
    except Exception as e:
        add("READ_ERROR", rel, 0, str(e), "H"); continue
    # BOM / mojibake
    if raw.startswith(b'\xef\xbb\xbf'):
        add("BOM", rel, 1, "UTF-8 BOM at file start", "L")
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        add("ENCODING_NON_UTF8", rel, 0, "file not valid UTF-8", "H")
        text = raw.decode('utf-8', errors='replace')
    if '�' in text:
        add("MOJIBAKE", rel, 0, f"replacement char U+FFFD count={text.count(chr(0xfffd))}", "M")
    lines = text.split('\n')
    # normalize CRLF check
    if b'\r\n' in raw:
        add("CRLF", rel, 0, "CRLF line endings", "L")
    # find header
    header_idx = None
    header = None
    for idx, ln in enumerate(lines):
        if ln.startswith('hadiths[') or ln.startswith('hadiths{'):
            header_idx = idx
            header = ln.strip()
            break
        m = HEADER_RE.match(ln.strip())
        if m:
            header_idx = idx; header = ln.strip(); break
    if header is None:
        add("NO_HEADER", rel, 0, "no hadiths[...] header found", "H"); continue
    # parse header
    mh = HEADER_COUNT_FIELD_RE.match(header)
    if not mh:
        add("HEADER_MALFORMED", rel, header_idx+1, f"header does not match schema: {header[:120]}", "H")
        header_count = None; fields = []
    else:
        hc = mh.group(1); fields = [x.strip() for x in mh.group(2).split(',')]
        if hc == 'count':
            add("HEADER_COUNT_LITERAL", rel, header_idx+1, "header uses [count] not numeric", "L")
            header_count = None
        else:
            header_count = int(hc)
    nfields = len(fields)
    is_full = nfields == 7
    is_min = nfields == 2
    # data rows = lines after header that start with quote
    data_lines = []
    for j in range(header_idx+1, len(lines)):
        ln = lines[j]
        if ln.strip() == '':
            continue
        if ln.lstrip().startswith('"'):
            data_lines.append((j+1, ln))
        elif ln.strip().startswith('#') or ln.strip().startswith('metadata'):
            continue
        else:
            # orphan non-data non-empty line after header
            add("ORPHAN_LINE", rel, j+1, f"non-data line after header: {ln[:120]}", "M")
    # count check
    if header_count is not None and header_count != len(data_lines):
        add("HEADER_COUNT_MISMATCH", rel, header_idx+1,
            f"header says {header_count}, actual rows {len(data_lines)}", "H")
    # per-row checks
    seen_numbers = []
    row_texts = []
    for lineno, ln in data_lines:
        # odd quote count
        qc = ln.count('"')
        if qc % 2 == 1:
            add("ODD_QUOTE", rel, lineno, f"odd quote count {qc}", "M")
        fields_row = parse_row(ln)
        if fields_row is None:
            add("ROW_PARSE_FAIL", rel, lineno, f"could not parse row: {ln[:120]}", "H")
            continue
        if len(fields_row) != nfields:
            add("FIELD_COUNT_MISMATCH", rel, lineno,
                f"expected {nfields} fields, got {len(fields_row)}: {ln[:100]}", "H")
            continue
        hadno = fields_row[0]
        seen_numbers.append(hadno)
        if is_min:
            txt = fields_row[1] if len(fields_row)>1 else ''
            row_texts.append(txt)
        elif is_full:
            arabic = fields_row[1] if len(fields_row)>1 else ''
            grades = fields_row[2] if len(fields_row)>2 else ''
            reference = fields_row[3] if len(fields_row)>3 else ''
            intl = fields_row[4] if len(fields_row)>4 else ''
            chain = fields_row[5] if len(fields_row)>5 else ''
            intro = fields_row[6] if len(fields_row)>6 else ''
            row_texts.append(arabic)
            if arabic.strip() == '':
                add("EMPTY_ARABIC", rel, lineno, f"empty arabic field (hadith {hadno})", "H")
            # grades empty
            if grades.strip() == '':
                add("EMPTY_GRADES", rel, lineno, f"empty grades (hadith {hadno})", "L")
            # reference empty
            if reference.strip() == '':
                add("EMPTY_REFERENCE", rel, lineno, f"empty reference (hadith {hadno})", "L")
            # international_number empty
            if intl.strip() == '':
                add("EMPTY_INTL_NUMBER", rel, lineno, f"empty international_number (hadith {hadno})", "L")
            # arabic field should be arabic script dominant; flag if latin-only
            sc = detect_script(arabic)
            if sc is not None and sc not in ('Arabic','ArabicPresentation') and len(arabic) > 20:
                add("ARABIC_NOT_AR_SCRIPT", rel, lineno, f"arabic field script={sc}: {arabic[:80]}", "M")
            # chapter intro empty
            if intro.strip() == '':
                add("EMPTY_CHAPTER_INTRO", rel, lineno, f"empty chapter_intro (hadith {hadno})", "L")
        # hadith number numeric?
        if not re.fullmatch(r'\d+', hadno.strip()):
            add("BAD_HADITH_NUMBER", rel, lineno, f"hadith number not numeric: {hadno[:40]}", "M")
        # now text checks (the 'text' for min, 'arabic' for full)
        body = row_texts[-1] if row_texts else ''
        if body.strip() == '':
            add("EMPTY_TEXT", rel, lineno, f"empty text field (hadith {hadno})", "H")
        elif len(body.strip()) < 15 and is_min:
            add("VERY_SHORT_TEXT", rel, lineno, f"text len={len(body.strip())}: {body!r}", "M")
        # AI leakage
        m = AI_LEAKAGE.search(body)
        if m:
            add("AI_LEAKAGE", rel, lineno, f"AI-markers: '{m.group(0)}' in: {body[:80]}", "M")
        # markdown
        mm = MARKDOWN.search(body)
        if mm:
            add("MARKDOWN_RESIDUE", rel, lineno, f"markdown: {mm.group(0)} in: {body[:80]}", "L")
        # leading ordinal pollution
        lo = LEADING_ORDINAL.match(body)
        if lo and is_min:
            add("LEADING_ORDINAL", rel, lineno, f"text starts with ordinal '{lo.group(0).strip()}': {body[:80]}", "M")
        # placeholder
        pm = PLACEHOLDER.search(body)
        if pm:
            add("PLACEHOLDER", rel, lineno, f"placeholder: {pm.group(0)} in: {body[:80]}", "M")
        # script mismatch for translations
        if lang and lang in LANGS and is_min and len(body) > 30:
            expected_name, _ = LANGS[lang]
            sc = detect_script(body)
            if sc is not None and sc != expected_name and sc not in ('ArabicPresentation',):
                # allow arabic snippets in translations (quran etc.) only if dominant wrong
                add("SCRIPT_MISMATCH", rel, lineno, f"lang={lang} expected {expected_name} got {sc}: {body[:80]}", "M")
        # leading/trailing whitespace inside field
        if body != body.strip() and (body != body.lstrip() or len(body)-len(body.rstrip())>0):
            pass  # too noisy, skip
    # duplicate hadith numbers
    dup = [k for k,v in collections.Counter(seen_numbers).items() if v>1]
    if dup:
        add("DUP_HADITH_NUMBER", rel, 0, f"duplicate hadith numbers: {dup[:10]}", "H")
    # non-sequential numbering (gaps) for min schema translations
    nums = []
    bad_seq = False
    for n in seen_numbers:
        try: nums.append(int(n))
        except: bad_seq = True
    if nums and not bad_seq:
        # check strictly increasing by 1
        gaps = []
        for a,b in zip(nums, nums[1:]):
            if b != a+1 and b != a:
                gaps.append((a,b))
        if gaps:
            add("NUMBERING_GAP", rel, 0, f"non-sequential numbering gaps: {gaps[:6]}", "M")
    # exact duplicate rows in a section
    dups = [t for t,c in collections.Counter(row_texts).items() if c>1 and len(t)>30]
    if dups:
        add("DUP_TEXT_IN_SECTION", rel, 0, f"{len(dups)} duplicated hadith text(s): {dups[0][:60]}", "M")
    # record for cross-file
    section_files[(edition, lang)].append((path, len(data_lines)))
    if os.path.basename(path) == 'info.toon':
        info_files[edition] = path

# info.toon cross checks
for edition, path in info_files.items():
    rel = os.path.relpath(path, EDITIONS_DIR)
    try:
        txt = open(path, encoding='utf-8', errors='replace').read()
    except: continue
    mh = re.search(r'total_hadiths:\s*"?(\d+)"?', txt)
    mh2 = re.search(r'available_languages:\s*"?([a-z,\-]+)"?', txt)
    mh3 = re.search(r'book_id:\s*"?([a-z0-9\-]+)"?', txt)
    # count actual sections in source
    src_dir = os.path.join(EDITIONS_DIR, edition, 'sections')
    actual_files = 0
    if os.path.isdir(src_dir):
        actual_files = len([f for f in os.listdir(src_dir) if f.endswith('.toon')])
    if mh:
        declared = int(mh.group(1))
        # rough: sum rows across source sections
        total_rows = sum(c for (e,lang),lst in section_files.items() if e==edition and lang is None for (_,c) in lst)
        if total_rows and abs(declared - total_rows) > declared*0.05 and declared != 0:
            if abs(declared-total_rows) > 5:
                add("INFO_TOTAL_MISMATCH", rel, 0, f"total_hadiths={declared} actual source rows={total_rows}", "M")
    # languages vs actual dirs
    trans_dir = os.path.join(EDITIONS_DIR, edition, 'translations')
    actual_langs = set()
    if os.path.isdir(trans_dir):
        for d in os.listdir(trans_dir):
            if os.path.isdir(os.path.join(trans_dir, d)):
                actual_langs.add(d)
    if mh2:
        declared_langs = set(mh2.group(1).split(','))
        missing = declared_langs - actual_langs
        extra = actual_langs - declared_langs
        if missing:
            add("INFO_LANG_DECLARED_MISSING", rel, 0, f"declared langs not present: {missing}", "M")
        if extra:
            add("INFO_LANG_PRESENT_UNDECLARED", rel, 0, f"present langs not declared: {extra}", "L")

# section numbering completeness per (edition,lang)
for (edition, lang), lst in section_files.items():
    nums = []
    for p,c in lst:
        b = os.path.basename(p)
        m = re.match(r'(\d+)\.toon$', b)
        if m: nums.append(int(m.group(1)))
    if nums and len(nums) > 1:
        nums.sort()
        gaps = []
        for a,b in zip(nums, nums[1:]):
            if b != a+1:
                gaps.append((a,b))
        if gaps and len(gaps) < 20:
            add("SECTION_GAP", "", 0, f"{edition}/{lang}: section files missing: {gaps[:10]}", "L")

# output
out = {
    "stats": dict(stats),
    "total_files": len(all_toon),
    "total_issues": len(issues),
    "issues": issues,
}
json.dump(out, sys.stdout, ensure_ascii=False)
print("", file=sys.stderr)
for k,v in sorted(stats.items(), key=lambda x:-x[1]):
    print(f"  {k:28s} {v}", file=sys.stderr)
print(f"TOTAL issues: {len(issues)}", file=sys.stderr)
