#!/usr/bin/env python3
"""Exhaustive metadata consistency scan of all editions."""
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
    """Parse a raw hadith number string to a list of int values.
    Handles:
      - comma-separated: "272, 273" -> [272, 273]
      - decimal: "146.1" -> [146]
      - simple: "147" -> [147]
      - compound: "14601" -> [14601] (kept as-is, NOT divided)
    Returns empty list if unparseable.
    """
    results = []
    # Split on commas
    parts = [p.strip() for p in raw.split(',')]
    for part in parts:
        if not part:
            continue
        # Try direct int
        try:
            v = int(part)
            results.append(v)
        except ValueError:
            # Try float (e.g., "146.1")
            try:
                fv = float(part)
                results.append(int(fv))
            except ValueError:
                pass
    return results


def parse_section_file(filepath):
    """Parse a .toon section file.
    Returns dict: header_count (int or None), num_rows (int), hadith_numbers (set of str),
    hadith_numbers_normalized (set of int), fields (list), header_corrupt (bool).
    Returns None if file can't be parsed at all.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return None
    if not content.strip():
        return {'header_count': 0, 'num_rows': 0, 'hadith_numbers': set(),
                'hadith_numbers_normalized': set(), 'fields': None, 'header_corrupt': False}
    lines = content.split('\n')
    header = lines[0]
    header_corrupt = False

    # Try standard header
    m = re.match(r'hadiths\[(\d+|count)\]\{([^}]*)\}:', header)
    if not m:
        # Try corrupted header: starts with " and has misplaced quotes
        # e.g., "hadiths[1148]{hadithnumber","text}:"
        stripped = header.strip().strip('"')
        m2 = re.match(r'hadiths\[(\d+|count)\]\{([^}]*)\}:?', stripped)
        if m2:
            m = m2
            header_corrupt = True
        else:
            return None

    count_str = m.group(1)
    header_count = int(count_str) if count_str.isdigit() else None
    # Fix fields: may have misplaced quotes like hadithnumber","text
    raw_fields = m.group(2)
    fields = [f.strip().strip('"') for f in raw_fields.split(',')]
    # data rows = non-empty lines after header
    data_lines = [l for l in lines[1:] if l.strip()]
    num_rows = len(data_lines)
    # extract hadith number (first quoted field)
    hadith_numbers = set()
    hadith_numbers_normalized = set()
    for line in data_lines:
        m2 = re.match(r'"([^"]*)"', line)
        if m2:
            raw_num = m2.group(1)
            hadith_numbers.add(raw_num)
            hadith_numbers_normalized.update(normalize_hadith_number(raw_num))
    return {'header_count': header_count, 'num_rows': num_rows,
            'hadith_numbers': hadith_numbers,
            'hadith_numbers_normalized': hadith_numbers_normalized,
            'fields': fields, 'header_corrupt': header_corrupt}


def parse_info_toon(filepath):
    """Parse an edition's info.toon.
    Returns dict with: total_hadiths, available_languages, translations (list of dicts),
    sections (list of dicts), translations_count, sections_count.
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

    # total_hadiths - find in metadata block
    m = re.search(r'^\s*total_hadiths:\s*"?(\d+)"?\s*$', content, re.MULTILINE)
    if m:
        result['total_hadiths'] = int(m.group(1))

    # available_languages
    m = re.search(r'^\s*available_languages:\s*"([^"]*)"\s*$', content, re.MULTILINE)
    if m:
        result['available_languages'] = [x.strip() for x in m.group(1).split(',') if x.strip()]
    else:
        m2 = re.search(r'^\s*available_languages:\s*(\S+)\s*$', content, re.MULTILINE)
        if m2:
            result['available_languages'] = [x.strip() for x in m2.group(1).split(',') if x.strip()]

    # translations block: translations[N]{fields}:\n rows
    m = re.search(r'translations\[(\d+)\]\{([^}]*)\}:\s*\n', content)
    if m:
        result['translations_count'] = int(m.group(1))
        tfields = m.group(2).split(',')
        # find start of rows
        start = m.end()
        # find end - next blank line or sections[ or end of file
        rest = content[start:]
        # rows are lines that start with a quote
        for line in rest.split('\n'):
            if line.strip() == '' or line.startswith('sections[') or line.startswith('metadata:') or (not line.startswith('"')):
                break
            # parse CSV row
            parts = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
            if parts and len(parts) >= len(tfields):
                row = dict(zip(tfields, parts))
                result['translations'].append(row)

    # sections block: sections[N]{fields}:\n rows
    m = re.search(r'sections\[(\d+)\]\{([^}]*)\}:\s*\n', content)
    if m:
        result['sections_count'] = int(m.group(1))
        sfields = m.group(2).split(',')
        start = m.end()
        rest = content[start:]
        for line in rest.split('\n'):
            if line.strip() == '' or (not line.startswith('"')):
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

print(f"Found {len(editions)} editions: {editions}")
print()

# ---------------------------------------------------------------------------
# CHECK 1: info.toon total_hadiths vs actual AR unique hadith count
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 1: info.toon total_hadiths vs actual AR unique hadith count (mismatch >5)")
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
        if parsed and parsed['hadith_numbers_normalized']:
            ar_hadith_numbers.update(parsed['hadith_numbers_normalized'])

    actual_count = len(ar_hadith_numbers)
    if info_total is not None and abs(info_total - actual_count) > 5:
        add_issue(1, ed, info_path,
                  f"info.toon total_hadiths={info_total} vs AR unique count={actual_count} (diff={info_total - actual_count})")

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
# CHECK 3: Section file count vs info.toon sections[N], and translation dirs match
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 3: Section file count vs info.toon sections[N], and cross-translation consistency")
print("=" * 80)

for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    info = parse_info_toon(info_path) if os.path.exists(info_path) else None

    sections_dir = os.path.join(ed_path, 'sections')
    ar_section_files = sorted(glob.glob(os.path.join(sections_dir, '*.toon'))) if os.path.isdir(sections_dir) else []
    ar_section_count = len(ar_section_files)

    if info:
        # Check AR section count vs info.toon sections_count
        if info['sections_count'] is not None and info['sections_count'] != ar_section_count:
            add_issue(3, ed, info_path,
                      f"info.toon sections[{info['sections_count']}] vs actual AR .toon files={ar_section_count}")

        # Check each translation directory has same section count as AR
        translations_dir = os.path.join(ed_path, 'translations')
        if os.path.isdir(translations_dir):
            for lang_dir in sorted(os.listdir(translations_dir)):
                if (ed, lang_dir) in EXCLUDE_TRANSLATIONS:
                    continue
                lang_sections_dir = os.path.join(translations_dir, lang_dir, 'sections')
                if not os.path.isdir(lang_sections_dir):
                    add_issue(3, ed, lang_sections_dir, f"MISSING sections/ dir for translation {lang_dir}")
                    continue
                lang_section_files = sorted(glob.glob(os.path.join(lang_sections_dir, '*.toon')))
                lang_count = len(lang_section_files)
                if lang_count != ar_section_count:
                    add_issue(3, ed, lang_sections_dir,
                              f"translation {lang_dir} section count={lang_count} vs AR section count={ar_section_count}")

                # Also check against info.toon translations block section count
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
# CHECK 4: Section ranges - hadith_first/hadith_last consistent with actual data
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 4: Section ranges (hadith_first/hadith_last vs actual data in section files)")
print("=" * 80)

for ed in editions:
    ed_path = os.path.join(EDITIONS_DIR, ed)
    info_path = os.path.join(ed_path, 'info.toon')
    info = parse_info_toon(info_path) if os.path.exists(info_path) else None
    if not info or not info['sections']:
        continue

    sections_dir = os.path.join(ed_path, 'sections')
    if not os.path.isdir(sections_dir):
        continue

    # Build map of section id -> actual hadith numbers (normalized)
    section_data = {}
    for sf in sorted(glob.glob(os.path.join(sections_dir, '*.toon'))):
        sec_id = os.path.splitext(os.path.basename(sf))[0]
        parsed = parse_section_file(sf)
        if parsed:
            section_data[sec_id] = parsed['hadith_numbers_normalized']

    for sec in info['sections']:
        sec_id = sec.get('id', '')
        hadith_first = sec.get('hadith_first', '')
        hadith_last = sec.get('hadith_last', '')
        arabic_first = sec.get('arabic_first', '')
        arabic_last = sec.get('arabic_last', '')

        actual_nums = section_data.get(sec_id)
        if actual_nums is None:
            add_issue(4, ed, os.path.join(sections_dir, f'{sec_id}.toon'),
                      f"Section {sec_id} listed in info.toon but no section file found")
            continue

        if not actual_nums:
            # empty section - skip range check but note if hadith_first/hadith_last are non-empty
            continue

        actual_min = min(actual_nums)
        actual_max = max(actual_nums)

        # Check hadith_first (use normalize_hadith_number for comma-separated handling)
        hf_vals = normalize_hadith_number(hadith_first)
        if hf_vals:
            hf = min(hf_vals)
            if hf != actual_min:
                add_issue(4, ed, info_path,
                          f"Section {sec_id}: hadith_first={hf} vs actual min={actual_min}")

        # Check hadith_last
        hl_vals = normalize_hadith_number(hadith_last)
        if hl_vals:
            hl = max(hl_vals)
            if hl != actual_max:
                add_issue(4, ed, info_path,
                          f"Section {sec_id}: hadith_last={hl} vs actual max={actual_max}")

        # Check arabic_first / arabic_last
        af_vals = normalize_hadith_number(arabic_first)
        if af_vals:
            af = min(af_vals)
            if af != actual_min:
                add_issue(4, ed, info_path,
                          f"Section {sec_id}: arabic_first={af} vs actual min={actual_min}")

        al_vals = normalize_hadith_number(arabic_last)
        if al_vals:
            al = max(al_vals)
            if al != actual_max:
                add_issue(4, ed, info_path,
                          f"Section {sec_id}: arabic_last={al} vs actual max={actual_max}")

check4_issues = [i for i in issues if i[0] == 4]
if check4_issues:
    for _, ed, path, msg in check4_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 5: available_languages vs actual translation directories
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 5: available_languages vs actual translation directories")
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

    # 'ar' in available_languages typically refers to the AR sections/ dir, not a translation dir
    # So remove 'ar' from declared when comparing to translation dirs
    declared_translations = declared_langs - {'ar'}

    missing_dirs = declared_translations - actual_langs
    extra_dirs = actual_langs - declared_translations

    # Also: 'ar' should be in available_languages (since AR sections always exist)
    if 'ar' not in declared_langs:
        add_issue(5, ed, info_path, "'ar' not in available_languages but AR sections/ exists")

    for lang in sorted(missing_dirs):
        add_issue(5, ed, info_path,
                  f"available_languages lists '{lang}' but translations/{lang}/ directory does not exist")
    for lang in sorted(extra_dirs):
        if (ed, lang) in EXCLUDE_TRANSLATIONS:
            continue
        add_issue(5, ed, os.path.join(translations_dir, lang),
                  f"translations/{lang}/ exists but not in available_languages (declared: {','.join(sorted(declared_langs))})")

check5_issues = [i for i in issues if i[0] == 5]
if check5_issues:
    for _, ed, path, msg in check5_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 6: Root info.toon - lists all 31 editions with correct paths and totals
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 6: Root info.toon - all 31 editions, correct paths and total_hadiths")
print("=" * 80)

with open(ROOT_INFO, 'r', encoding='utf-8') as f:
    root_content = f.read()

# Parse root info.toon
root_books = []
m = re.search(r'books\[(\d+)\]\{([^}]*)\}:\s*\n', root_content)
if m:
    root_count = int(m.group(1))
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
    add_issue(6, 'ROOT', ROOT_INFO, "Could not parse books[] block in root info.toon")
    root_count = 0

# Check count
if m and root_count != len(root_books):
    add_issue(6, 'ROOT', ROOT_INFO,
              f"Root books[{root_count}] vs actual rows={len(root_books)}")

# Check we have 31 editions
if len(root_books) != 31:
    add_issue(6, 'ROOT', ROOT_INFO,
              f"Root lists {len(root_books)} editions, expected 31")

root_book_ids = set()
for rb in root_books:
    bid = rb.get('id', '')
    root_book_ids.add(bid)
    ed_path_check = os.path.join(EDITIONS_DIR, bid)
    if not os.path.isdir(ed_path_check):
        add_issue(6, bid, ROOT_INFO, f"Root lists edition '{bid}' but directory {ed_path_check} does not exist")
        continue

    info_path = os.path.join(ed_path_check, 'info.toon')
    if not os.path.exists(info_path):
        add_issue(6, bid, info_path, f"Edition '{bid}' has no info.toon")
        continue

    info = parse_info_toon(info_path)
    root_total = int(rb.get('total_hadiths', 0)) if rb.get('total_hadiths') else None
    ed_total = info['total_hadiths']

    if root_total is not None and ed_total is not None and root_total != ed_total:
        add_issue(6, bid, ROOT_INFO,
                  f"Root total_hadiths={root_total} vs edition info.toon total_hadiths={ed_total}")

    # Check path
    root_path = rb.get('path', '')
    expected_path = f"editions/{bid}"
    if root_path != expected_path:
        add_issue(6, bid, ROOT_INFO,
                  f"Root path='{root_path}' vs expected='{expected_path}'")

# Check all edition dirs are listed in root
for ed in editions:
    if ed not in root_book_ids:
        add_issue(6, ed, ROOT_INFO, f"Edition directory '{ed}' exists but not listed in root info.toon")

check6_issues = [i for i in issues if i[0] == 6]
if check6_issues:
    for _, ed, path, msg in check6_issues:
        print(f"  [{ed}] {msg}")
        print(f"    -> {path}")
else:
    print("  No issues found.")
print()

# ---------------------------------------------------------------------------
# CHECK 7: Header count vs actual data rows for EVERY .toon file
# ---------------------------------------------------------------------------
print("=" * 80)
print("CHECK 7: Header count vs actual data rows for EVERY .toon section file")
print("=" * 80)

all_section_files = []
all_section_files += glob.glob(os.path.join(EDITIONS_DIR, '*', 'sections', '*.toon'))
all_section_files += glob.glob(os.path.join(EDITIONS_DIR, '*', 'translations', '*', 'sections', '*.toon'))

count_placeholder_count = 0
numeric_checked = 0
unparseable = 0

for sf in sorted(all_section_files):
    parsed = parse_section_file(sf)
    if parsed is None:
        unparseable += 1
        add_issue(7, '', sf, "UNPARSEABLE: no hadiths[N] header found")
        continue
    if parsed.get('header_corrupt', False):
        add_issue(7, '', sf, f"CORRUPT HEADER: {open(sf).readline().strip()}")
    if parsed['header_count'] is None:
        # uses 'count' placeholder - can't check
        count_placeholder_count += 1
        continue
    numeric_checked += 1
    if parsed['header_count'] != parsed['num_rows']:
        rel_path = sf.replace(EDITIONS_DIR + '/', '')
        add_issue(7, '', sf,
                  f"header hadiths[{parsed['header_count']}] vs actual rows={parsed['num_rows']} (diff={parsed['header_count'] - parsed['num_rows']})")

print(f"  Files with numeric header checked: {numeric_checked}")
print(f"  Files with 'count' placeholder (skipped): {count_placeholder_count}")
print(f"  Unparseable files: {unparseable}")
print()

check7_issues = [i for i in issues if i[0] == 7]
if check7_issues:
    for _, ed, path, msg in check7_issues:
        print(f"  {msg}")
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
for check_num in range(1, 8):
    check_issues = [i for i in issues if i[0] == check_num]
    print(f"  Check {check_num}: {len(check_issues)} issue(s)")
print(f"  TOTAL: {len(issues)} issue(s)")

# Write full report to file
report_path = '/home/saboor/code/hadith-api-toon/audit_metadata_report.txt'
with open(report_path, 'w') as f:
    f.write("METADATA CONSISTENCY AUDIT REPORT\n")
    f.write("=" * 80 + "\n\n")
    for check_num in range(1, 8):
        check_issues = [i for i in issues if i[0] == check_num]
        f.write(f"CHECK {check_num}: {len(check_issues)} issue(s)\n")
        f.write("-" * 40 + "\n")
        for _, ed, path, msg in check_issues:
            f.write(f"  [{ed}] {msg}\n")
            f.write(f"    -> {path}\n")
        f.write("\n")
    f.write(f"TOTAL: {len(issues)} issue(s)\n")
print(f"\nFull report written to: {report_path}")
