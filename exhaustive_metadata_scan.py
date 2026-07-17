#!/usr/bin/env python3
"""Exhaustive metadata consistency scan of ALL editions in editions/.

Excludes skeleton editions:
  abdurrazzaq/translations/en, abdurrazzaq/translations/ur,
  muajam-tabarani-saghir/translations/en, mustadrak/translations/en

Checks:
  1. info.toon total_hadiths vs actual AR unique hadith count (mismatch > 5)
  2. metadata.toon total_hadiths vs info.toon total_hadiths
  3. Section file count vs info.toon sections[N], cross-translation consistency
  4. available_languages vs actual translation directories
  5. Root info.toon lists all editions with correct total_hadiths
  6. Header count vs actual data rows for EVERY .toon file
  7. Section ranges (hadith_first/hadith_last/arabic_first/arabic_last vs actual data)
"""
import os, re, glob, sys
from collections import defaultdict

EDITIONS_DIR = '/home/saboor/code/hadith-api-toon/editions'
ROOT_INFO = '/home/saboor/code/hadith-api-toon/info.toon'

EXCLUDE_TRANSLATIONS = {
    ('abdurrazzaq', 'en'),
    ('abdurrazzaq', 'ur'),
    ('muajam-tabarani-saghir', 'en'),
    ('mustadrak', 'en'),
}

issues = []


def add_issue(check, edition, path, msg):
    issues.append((check, edition, path, msg))


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def normalize_hadith_number(raw):
    """Parse a raw hadith number string to a set of int values.
    Handles comma-separated, decimal, and simple ints.
    Compound numbers (e.g. 14601) are kept AS-IS (NOT split to base).
    Used for counting unique hadiths (Check 1).
    """
    results = set()
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            results.add(int(part))
        except ValueError:
            try:
                results.add(int(float(part)))
            except ValueError:
                pass
    return results


def normalize_for_range(raw, is_compound_edition):
    """Parse a raw hadith number string for RANGE comparison.
    For compound editions (e.g. malik), 5-digit numbers with suffix 01/02
    are split to their base (14601 -> 146).
    For non-compound editions, numbers are kept as-is.
    Returns a set of int values.
    """
    results = set()
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
        except ValueError:
            try:
                n = int(float(part))
            except ValueError:
                continue
        if is_compound_edition and n >= 10000 and n % 100 in (1, 2):
            results.add(n // 100)
        else:
            results.add(n)
    return results


def detect_compound_edition(edition_dir, info_total):
    """Detect if an edition uses compound hadith numbering (e.g. malik).
    Heuristic: max hadith number in sections >> info.toon total_hadiths.
    Also verify compound numbers follow base*100+01/02 pattern.
    """
    if not info_total or info_total <= 0:
        return False
    sections_dir = os.path.join(edition_dir, 'sections')
    if not os.path.isdir(sections_dir):
        return False
    max_num = 0
    compound_count = 0
    total_count = 0
    for sf in glob.glob(os.path.join(sections_dir, '*.toon')):
        parsed = parse_section_file(sf)
        if not parsed:
            continue
        for n in parsed['hadith_numbers_int']:
            total_count += 1
            if n > max_num:
                max_num = n
            if n >= 10000 and n % 100 in (1, 2):
                compound_count += 1
    # If max number is far larger than total_hadiths, and we have compound numbers,
    # it's a compound edition.
    if max_num > info_total * 2 and compound_count > 0:
        return True
    return False


def parse_section_file(filepath):
    """Parse a .toon section file.
    Returns dict with:
      header_count (int or None), num_rows (int),
      hadith_numbers (set of str), hadith_numbers_int (set of int),
      fields (list), header_corrupt (bool)
    Returns None if unparseable.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None
    if not content.strip():
        return {'header_count': 0, 'num_rows': 0, 'num_lines': 0,
                'hadith_numbers': set(),
                'hadith_numbers_int': set(), 'fields': None, 'header_corrupt': False}
    lines = content.split('\n')
    header = lines[0]
    header_corrupt = False

    m = re.match(r'hadiths\[(\d+|count)\]\{([^}]*)\}:', header)
    if not m:
        stripped = header.strip().strip('"')
        m2 = re.match(r'hadiths\[(\d+|count)\]\{([^}]*)\}:?', stripped)
        if m2:
            m = m2
            header_corrupt = True
        else:
            return None

    count_str = m.group(1)
    header_count = int(count_str) if count_str.isdigit() else None
    raw_fields = m.group(2)
    fields = [f.strip().strip('"') for f in raw_fields.split(',')]
    data_lines = [l for l in lines[1:] if l.strip()]
    # Count actual hadith records (lines starting with ") — some files have
    # multi-line records where arabic text contains literal newlines, causing
    # continuation lines that don't start with a quote.
    record_lines = [l for l in data_lines if l.startswith('"')]
    num_rows = len(record_lines)
    num_lines = len(data_lines)
    hadith_numbers = set()
    hadith_numbers_int = set()
    for line in record_lines:
        m2 = re.match(r'"([^"]*)"', line)
        if m2:
            raw_num = m2.group(1)
            hadith_numbers.add(raw_num)
            hadith_numbers_int.update(normalize_hadith_number(raw_num))
    return {'header_count': header_count, 'num_rows': num_rows,
            'num_lines': num_lines,
            'hadith_numbers': hadith_numbers,
            'hadith_numbers_int': hadith_numbers_int,
            'fields': fields, 'header_corrupt': header_corrupt}


def parse_info_toon(filepath):
    """Parse an edition's info.toon.
    Returns dict with: total_hadiths, available_languages, translations,
    sections, translations_count, sections_count.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {
        'total_hadiths': None,
        'available_languages': None,
        'translations': [],
        'sections': [],
        'translations_count': None,
        'sections_count': None,
    }

    m = re.search(r'^\s*total_hadiths:\s*"?(\d+)"?\s*$', content, re.MULTILINE)
    if m:
        result['total_hadiths'] = int(m.group(1))

    m = re.search(r'^\s*available_languages:\s*"([^"]*)"\s*$', content, re.MULTILINE)
    if m:
        result['available_languages'] = [x.strip() for x in m.group(1).split(',') if x.strip()]
    else:
        m = re.search(r'^\s*available_languages:\s*(\S+)\s*$', content, re.MULTILINE)
        if m:
            result['available_languages'] = [x.strip() for x in m.group(1).split(',') if x.strip()]

    m = re.search(r'translations\[(\d+)\]\{([^}]*)\}:\s*\n', content)
    if m:
        result['translations_count'] = int(m.group(1))
        tfields = m.group(2).split(',')
        start = m.end()
        rest = content[start:]
        for line in rest.split('\n'):
            if line.strip() == '' or line.startswith('sections[') or \
               line.startswith('metadata:') or not line.startswith('"'):
                break
            parts = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
            if parts and len(parts) >= len(tfields):
                row = dict(zip(tfields, parts))
                result['translations'].append(row)

    m = re.search(r'sections\[(\d+)\]\{([^}]*)\}:\s*\n', content)
    if m:
        result['sections_count'] = int(m.group(1))
        sfields = m.group(2).split(',')
        start = m.end()
        rest = content[start:]
        for line in rest.split('\n'):
            if line.strip() == '' or not line.startswith('"'):
                break
            parts = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
            if parts and len(parts) >= len(sfields):
                row = dict(zip(sfields, parts))
                result['sections'].append(row)

    return result


def parse_metadata_toon(filepath):
    """Parse a translation's metadata.toon. Returns total_hadiths (int or None)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'^\s*total_hadiths:\s*(\d+)\s*$', content, re.MULTILINE)
    if m:
        return int(m.group(1))
    m = re.search(r'^\s*total_hadiths:\s*"(\d+)"\s*$', content, re.MULTILINE)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Get all editions
# ---------------------------------------------------------------------------
editions = sorted([d for d in os.listdir(EDITIONS_DIR)
                   if os.path.isdir(os.path.join(EDITIONS_DIR, d))])

print(f"Found {len(editions)} editions")
print()

# Pre-compute compound edition detection for all editions
compound_editions = {}
for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    if os.path.exists(info_path):
        info = parse_info_toon(info_path)
        compound_editions[ed] = detect_compound_edition(ed_path, info['total_hadiths'])
    else:
        compound_editions[ed] = False

compound_list = [ed for ed, v in compound_editions.items() if v]
if compound_list:
    print(f"Compound numbering detected in: {compound_list}")
    print()

# ---------------------------------------------------------------------------
# CHECK 1: info.toon total_hadiths vs actual AR unique hadith count
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 1: info.toon total_hadiths vs actual AR unique hadith count (mismatch > 5)")
print("=" * 80)

for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    if not os.path.exists(info_path):
        add_issue(1, ed, info_path, "MISSING info.toon")
        continue
    info = parse_info_toon(info_path)
    info_total = info['total_hadiths']

    sections_dir = os.path.join(ed_path, 'sections')
    if not os.path.isdir(sections_dir):
        add_issue(1, ed, sections_dir, "MISSING sections/ directory")
        continue

    ar_hadith_numbers = set()
    for sf in sorted(glob.glob(os.path.join(sections_dir, '*.toon'))):
        parsed = parse_section_file(sf)
        if parsed and parsed['hadith_numbers_int']:
            ar_hadith_numbers.update(parsed['hadith_numbers_int'])

    actual_count = len(ar_hadith_numbers)
    if info_total is not None and abs(info_total - actual_count) > 5:
        add_issue(1, ed, info_path,
                  f"info.toon total_hadiths={info_total} vs AR unique count={actual_count} "
                  f"(diff={info_total - actual_count})")

check1_issues = [i for i in issues if i[0] == 1]
if check1_issues:
    for _, ed, path, msg in check1_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 2: metadata.toon total_hadiths vs info.toon total_hadiths
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 2: metadata.toon total_hadiths vs info.toon total_hadiths")
print("=" * 80)

for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    info = parse_info_toon(info_path) if os.path.exists(info_path) else None
    info_total = info['total_hadiths'] if info else None

    translations_dir = os.path.join(ed_path, 'translations')
    if not os.path.isdir(translations_dir):
        continue
    for lang_dir in sorted(os.listdir(translations_dir)):
        if (ed, lang_dir) in EXCLUDE_TRANSLATIONS:
            continue
        lang_path = os.path.join(translations_dir, lang_dir)
        if not os.path.isdir(lang_path):
            continue
        meta_path = os.path.join(lang_path, 'metadata.toon')
        if not os.path.exists(meta_path):
            add_issue(2, ed, meta_path, "MISSING metadata.toon")
            continue
        meta_total = parse_metadata_toon(meta_path)
        if meta_total is None:
            add_issue(2, ed, meta_path, "metadata.toon has no parseable total_hadiths")
            continue
        if info_total is not None and meta_total != info_total:
            add_issue(2, ed, meta_path,
                      f"metadata.toon total_hadiths={meta_total} != info.toon total_hadiths={info_total}")

check2_issues = [i for i in issues if i[0] == 2]
if check2_issues:
    for _, ed, path, msg in check2_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 3: Section file count vs info.toon sections[N], and cross-translation
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 3: Section file count vs info.toon sections[N], cross-translation consistency")
print("=" * 80)

for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    info = parse_info_toon(info_path) if os.path.exists(info_path) else None

    sections_dir = os.path.join(ed_path, 'sections')
    ar_section_files = sorted(glob.glob(os.path.join(sections_dir, '*.toon'))) \
        if os.path.isdir(sections_dir) else []
    ar_section_count = len(ar_section_files)

    if info:
        if info['sections_count'] is not None and info['sections_count'] != ar_section_count:
            add_issue(3, ed, info_path,
                      f"info.toon sections[{info['sections_count']}] vs actual AR .toon files={ar_section_count}")

        translations_dir = os.path.join(ed_path, 'translations')
        if os.path.isdir(translations_dir):
            for lang_dir in sorted(os.listdir(translations_dir)):
                if (ed, lang_dir) in EXCLUDE_TRANSLATIONS:
                    continue
                lang_sections_dir = os.path.join(translations_dir, lang_dir, 'sections')
                if not os.path.isdir(lang_sections_dir):
                    add_issue(3, ed, lang_sections_dir,
                              f"MISSING sections/ dir for translation {lang_dir}")
                    continue
                lang_section_files = sorted(glob.glob(os.path.join(lang_sections_dir, '*.toon')))
                lang_count = len(lang_section_files)
                if lang_count != ar_section_count:
                    add_issue(3, ed, lang_sections_dir,
                              f"translation {lang_dir} section count={lang_count} vs AR section count={ar_section_count}")

                for t in info['translations']:
                    if t.get('language') == lang_dir:
                        t_sections = int(t.get('sections', 0)) if t.get('sections') else None
                        if t_sections is not None and t_sections != lang_count:
                            add_issue(3, ed, info_path,
                                      f"info.toon translations[{lang_dir}] sections={t_sections} vs actual={lang_count}")

check3_issues = [i for i in issues if i[0] == 3]
if check3_issues:
    for _, ed, path, msg in check3_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 4: available_languages vs actual translation directories
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 4: available_languages vs actual translation directories")
print("=" * 80)

for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    info = parse_info_toon(info_path) if os.path.exists(info_path) else None
    if not info:
        continue

    translations_dir = os.path.join(ed_path, 'translations')
    actual_langs = set()
    if os.path.isdir(translations_dir):
        for d in os.listdir(translations_dir):
            if os.path.isdir(os.path.join(translations_dir, d)):
                actual_langs.add(d)

    declared_langs = set(info['available_languages']) if info['available_languages'] else set()
    declared_translations = declared_langs - {'ar'}

    missing_dirs = declared_translations - actual_langs
    extra_dirs = actual_langs - declared_translations

    if 'ar' not in declared_langs:
        add_issue(4, ed, info_path, "'ar' not in available_languages but AR sections/ exists")

    for lang in sorted(missing_dirs):
        add_issue(4, ed, info_path,
                  f"available_languages lists '{lang}' but translations/{lang}/ directory does not exist")
    for lang in sorted(extra_dirs):
        if (ed, lang) in EXCLUDE_TRANSLATIONS:
            continue
        add_issue(4, ed, os.path.join(translations_dir, lang),
                  f"translations/{lang}/ exists but not in available_languages "
                  f"(declared: {','.join(sorted(declared_langs))})")

check4_issues = [i for i in issues if i[0] == 4]
if check4_issues:
    for _, ed, path, msg in check4_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 5: Root info.toon - all editions, correct paths and total_hadiths
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 5: Root info.toon - all editions, correct paths and total_hadiths")
print("=" * 80)

with open(ROOT_INFO, 'r', encoding='utf-8') as f:
    root_content = f.read()

root_books = []
root_count_declared = None
m = re.search(r'books\[(\d+)\]\{([^}]*)\}:\s*\n', root_content)
if m:
    root_count_declared = int(m.group(1))
    rfields = m.group(2).split(',')
    start = m.end()
    rest = root_content[start:]
    for line in rest.split('\n'):
        if line.strip() == '' or not line.startswith('"'):
            break
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        if parts and len(parts) >= len(rfields):
            row = dict(zip(rfields, parts))
            root_books.append(row)
else:
    add_issue(5, 'ROOT', ROOT_INFO, "Could not parse books[] block in root info.toon")

if m and root_count_declared != len(root_books):
    add_issue(5, 'ROOT', ROOT_INFO,
              f"Root books[{root_count_declared}] vs actual rows={len(root_books)}")

if len(root_books) != len(editions):
    add_issue(5, 'ROOT', ROOT_INFO,
              f"Root lists {len(root_books)} editions, found {len(editions)} edition directories")

root_book_ids = set()
for rb in root_books:
    bid = rb.get('id', '')
    root_book_ids.add(bid)
    ed_path_check = os.path.join(EDITIONS_DIR, bid)
    if not os.path.isdir(ed_path_check):
        add_issue(5, bid, ROOT_INFO,
                  f"Root lists edition '{bid}' but directory {ed_path_check} does not exist")
        continue

    info_path = os.path.join(ed_path_check, 'info.toon')
    if not os.path.exists(info_path):
        add_issue(5, bid, info_path, f"Edition '{bid}' has no info.toon")
        continue

    info = parse_info_toon(info_path)
    root_total = int(rb.get('total_hadiths', 0)) if rb.get('total_hadiths') else None
    ed_total = info['total_hadiths']

    if root_total is not None and ed_total is not None and root_total != ed_total:
        add_issue(5, bid, ROOT_INFO,
                  f"Root total_hadiths={root_total} vs edition info.toon total_hadiths={ed_total}")

    root_path = rb.get('path', '')
    expected_path = f"editions/{bid}"
    if root_path != expected_path:
        add_issue(5, bid, ROOT_INFO,
                  f"Root path='{root_path}' vs expected='{expected_path}'")

    root_langs = rb.get('available_languages', '')
    if root_langs and ed_total is not None:
        ed_langs = ','.join(info['available_languages']) if info['available_languages'] else ''
        if root_langs != ed_langs:
            add_issue(5, bid, ROOT_INFO,
                      f"Root available_languages='{root_langs}' vs edition='{ed_langs}'")

for ed in editions:
    if ed not in root_book_ids:
        add_issue(5, ed, ROOT_INFO,
                  f"Edition directory '{ed}' exists but not listed in root info.toon")

check5_issues = [i for i in issues if i[0] == 5]
if check5_issues:
    for _, ed, path, msg in check5_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 6: Header count vs actual data rows for EVERY .toon file
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 6: Header count vs actual data rows for EVERY .toon section file")
print("=" * 80)

all_section_files = []
all_section_files += glob.glob(os.path.join(EDITIONS_DIR, '*', 'sections', '*.toon'))
all_section_files += glob.glob(os.path.join(EDITIONS_DIR, '*', 'translations', '*', 'sections', '*.toon'))

# Exclude skeleton editions
filtered_files = []
for sf in all_section_files:
    rel = os.path.relpath(sf, EDITIONS_DIR)
    rel_parts = rel.split(os.sep)
    ed = rel_parts[0]
    if len(rel_parts) >= 4 and rel_parts[1] == 'translations':
        lang = rel_parts[2]
        if (ed, lang) in EXCLUDE_TRANSLATIONS:
            continue
    filtered_files.append(sf)
all_section_files = sorted(filtered_files)

count_placeholder_count = 0
numeric_checked = 0
unparseable = 0

for sf in all_section_files:
    parsed = parse_section_file(sf)
    if parsed is None:
        unparseable += 1
        add_issue(6, '', sf, "UNPARSEABLE: no hadiths[N] header found")
        continue
    if parsed.get('header_corrupt', False):
        with open(sf, 'r', encoding='utf-8', errors='replace') as f:
            first_line = f.readline().strip()
        add_issue(6, '', sf, f"CORRUPT HEADER: {first_line}")
    if parsed['header_count'] is None:
        count_placeholder_count += 1
        continue
    numeric_checked += 1
    if parsed['header_count'] != parsed['num_rows']:
        rel_path = sf.replace(EDITIONS_DIR + '/', '')
        add_issue(6, '', sf,
                  f"header hadiths[{parsed['header_count']}] vs actual rows={parsed['num_rows']} "
                  f"(diff={parsed['header_count'] - parsed['num_rows']}) [{rel_path}]")

print(f"  Total files scanned: {len(all_section_files)}")
print(f"  Files with numeric header checked: {numeric_checked}")
print(f"  Files with 'count' placeholder (skipped): {count_placeholder_count}")
print(f"  Unparseable files: {unparseable}")
print()

check6_issues = [i for i in issues if i[0] == 6]
if check6_issues:
    for _, ed, path, msg in check6_issues:
        print(f"  {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 7: Section ranges (hadith_first/hadith_last/arabic_first/arabic_last
#           vs actual data in section files)
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 7: Section ranges (hadith_first/hadith_last vs actual data, compound-aware)")
print("=" * 80)

for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    info = parse_info_toon(info_path) if os.path.exists(info_path) else None
    if not info or not info['sections']:
        continue

    is_compound = compound_editions.get(ed, False)
    sections_dir = os.path.join(ed_path, 'sections')
    if not os.path.isdir(sections_dir):
        continue

    section_data = {}
    for sf in sorted(glob.glob(os.path.join(sections_dir, '*.toon'))):
        sec_id = os.path.splitext(os.path.basename(sf))[0]
        parsed = parse_section_file(sf)
        if parsed:
            section_data[sec_id] = parsed['hadith_numbers_int']

    for sec in info['sections']:
        sec_id = sec.get('id', '')
        hadith_first = sec.get('hadith_first', '')
        hadith_last = sec.get('hadith_last', '')
        arabic_first = sec.get('arabic_first', '')
        arabic_last = sec.get('arabic_last', '')

        actual_nums = section_data.get(sec_id)
        if actual_nums is None:
            add_issue(7, ed, os.path.join(sections_dir, f'{sec_id}.toon'),
                      f"Section {sec_id} listed in info.toon but no section file found")
            continue

        if not actual_nums:
            continue

        if is_compound:
            actual_norm = set()
            for n in actual_nums:
                if n >= 10000 and n % 100 in (1, 2):
                    actual_norm.add(n // 100)
                else:
                    actual_norm.add(n)
        else:
            actual_norm = actual_nums

        actual_min = min(actual_norm)
        actual_max = max(actual_norm)

        for label, val_str in [('hadith_first', hadith_first), ('hadith_last', hadith_last),
                                ('arabic_first', arabic_first), ('arabic_last', arabic_last)]:
            vals = normalize_for_range(val_str, is_compound)
            if not vals:
                continue
            val = min(vals) if 'first' in label else max(vals)
            target = actual_min if 'first' in label else actual_max
            if val != target:
                add_issue(7, ed, info_path,
                          f"Section {sec_id}: {label}={val} vs actual {'min' if 'first' in label else 'max'}={target}")

check7_issues = [i for i in issues if i[0] == 7]
if check7_issues:
    for _, ed, path, msg in check7_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
print("=" * 80)
print("SUMMARY")
print("=" * 80)
check_labels = {
    1: "Check 1: info.toon total_hadiths vs AR unique count",
    2: "Check 2: metadata.toon vs info.toon total_hadiths",
    3: "Check 3: Section file count consistency",
    4: "Check 4: available_languages vs actual dirs",
    5: "Check 5: Root info.toon completeness",
    6: "Check 6: Header count vs actual data rows",
    7: "Check 7: Section ranges vs actual data",
}
for check_num in range(1, 8):
    check_issues = [i for i in issues if i[0] == check_num]
    print(f"  {check_labels[check_num]}: {len(check_issues)} issue(s)")
print(f"  TOTAL: {len(issues)} issue(s)")

# Write full report to file
report_path = '/home/saboor/code/hadith-api-toon/exhaustive_metadata_report.txt'
with open(report_path, 'w') as f:
    f.write("EXHAUSTIVE METADATA CONSISTENCY AUDIT REPORT\n")
    f.write("=" * 80 + "\n\n")
    if compound_list:
        f.write(f"Compound numbering detected in: {', '.join(compound_list)}\n")
        f.write("(5-digit hadith numbers base*100+01/02 are split to base for range checks)\n\n")
    for check_num in range(1, 8):
        check_issues = [i for i in issues if i[0] == check_num]
        f.write(f"CHECK {check_num}: {check_labels[check_num]}\n")
        f.write(f"  -> {len(check_issues)} issue(s)\n")
        f.write("-" * 80 + "\n")
        for _, ed, path, msg in check_issues:
            f.write(f"  [{ed}] {msg}\n")
            f.write(f"    -> {path}\n")
        f.write("\n")
    f.write(f"TOTAL: {len(issues)} issue(s)\n")
print(f"\nFull report written to: {report_path}")
