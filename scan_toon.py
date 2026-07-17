#!/usr/bin/env python3
"""
Exhaustive CSV structural integrity scanner for ALL .toon section files.
Checks 6 categories: orphan lines, bad start lines, odd quote count,
empty lines, header mismatch, duplicate hadith numbers.
"""

import os
import re
import sys
from collections import defaultdict

EDITIONS_DIR = "/home/saboor/code/hadith-api-toon/editions"

EXCLUDE_PREFIXES = [
    os.path.join(EDITIONS_DIR, "abdurrazzaq", "translations", "en"),
    os.path.join(EDITIONS_DIR, "abdurrazzaq", "translations", "ur"),
    os.path.join(EDITIONS_DIR, "muajam-tabarani-saghir", "translations", "en"),
    os.path.join(EDITIONS_DIR, "mustadrak", "translations", "en"),
]

HEADER_COUNT_RE = re.compile(r'^hadiths\[(\d+|count)\]')
FIRST_FIELD_RE = re.compile(r'^"([^"]*)"')


def is_excluded(filepath):
    norm = os.path.normpath(filepath)
    for prefix in EXCLUDE_PREFIXES:
        p = os.path.normpath(prefix)
        if norm == p or norm.startswith(p + os.sep):
            return True
    return False


def extract_edition(filepath):
    rel = os.path.relpath(filepath, EDITIONS_DIR)
    parts = rel.split(os.sep)
    if len(parts) >= 4 and parts[1] == "translations" and parts[3] == "sections":
        return f"{parts[0]}/{parts[2]}"
    return parts[0]


def scan_file(filepath):
    issues = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        issues.append(("READ_ERROR", 0, f"Cannot read: {e}"))
        return issues

    header_count = None
    header_is_count = False
    header_line_num = None
    state = "BEFORE_HEADER"
    data_row_count = 0
    hadith_numbers = []

    total_lines = len(lines)

    for i, raw in enumerate(lines, 1):
        line = raw.rstrip("\n").rstrip("\r")
        stripped = line.strip()

        qc = line.count('"')
        if qc % 2 == 1:
            issues.append(("ODD_QUOTE", i, f"Odd quote count ({qc})"))

        if state == "BEFORE_HEADER":
            if stripped == "":
                continue
            m = HEADER_COUNT_RE.match(line)
            if m:
                header_line_num = i
                val = m.group(1)
                if val == "count":
                    header_is_count = True
                else:
                    header_count = int(val)
                state = "IN_DATA"
                continue
            state = "IN_DATA"

        if state == "IN_DATA":
            if stripped == "":
                if i == total_lines:
                    pass
                else:
                    issues.append(("EMPTY_LINE", i, "Blank line in data"))
                continue

            first_char = line[0]

            if first_char == '"':
                data_row_count += 1
                m2 = FIRST_FIELD_RE.match(line)
                if m2:
                    hadith_numbers.append((m2.group(1), i))
            elif first_char.isdigit():
                issues.append(("ORPHAN_LINE", i, f"Starts with digit, no opening quote: {line[:80]}"))
            elif line.startswith("hadiths"):
                issues.append(("BAD_START", i, f"Unexpected header-like line in data: {line[:80]}"))
            else:
                issues.append(("BAD_START", i, f"Bad start (not quote/digit/hadiths): {line[:80]}"))

    if header_count is not None and not header_is_count:
        if header_count != data_row_count:
            issues.append(("HEADER_MISMATCH", header_line_num or 0,
                           f"Header declares {header_count} hadiths but found {data_row_count} data rows"))

    seen = defaultdict(list)
    for hnum, lnum in hadith_numbers:
        seen[hnum].append(lnum)
    for hnum, lnums in seen.items():
        if len(lnums) > 1:
            for lnum in lnums[1:]:
                issues.append(("DUPLICATE_HADITH", lnum,
                               f"Duplicate hadith number '{hnum}' (first at line {lnums[0]})"))

    return issues


def main():
    all_files = []
    for root, dirs, files in os.walk(EDITIONS_DIR):
        if os.sep + "sections" + os.sep not in root + os.sep:
            continue
        for fn in files:
            if fn.endswith(".toon"):
                fp = os.path.join(root, fn)
                if not is_excluded(fp):
                    all_files.append(fp)

    all_files.sort()

    cat_totals = defaultdict(int)
    edition_stats = defaultdict(lambda: defaultdict(int))
    files_with_issues = 0
    all_issues_detail = []

    for fp in all_files:
        issues = scan_file(fp)
        edition = extract_edition(fp)
        if issues:
            files_with_issues += 1
        for cat, lnum, desc in issues:
            cat_totals[cat] += 1
            edition_stats[edition][cat] += 1
            all_issues_detail.append((fp, cat, lnum, desc))

    print("=" * 80)
    print("EXHAUSTIVE .toon STRUCTURAL INTEGRITY SCAN")
    print("=" * 80)
    print(f"Files scanned:  {len(all_files)}")
    print(f"Files excluded: 4 skeleton editions (abdurrazzaq/en, abdurrazzaq/ur,")
    print(f"                 muajam-tabarani-saghir/en, mustadrak/en)")
    print(f"Files with issues: {files_with_issues}")
    print(f"Total issues found: {len(all_issues_detail)}")
    print()

    print("=" * 80)
    print("TOTAL COUNTS PER CATEGORY")
    print("=" * 80)
    cat_labels = {
        "ORPHAN_LINE": "1. Orphan lines (digit start, no quote)",
        "BAD_START": "2. Bad start lines (broken continuation)",
        "ODD_QUOTE": "3. Odd quote count",
        "EMPTY_LINE": "4. Empty lines between data",
        "HEADER_MISMATCH": "5. Header vs actual row count mismatch",
        "DUPLICATE_HADITH": "6. Duplicate hadith numbers",
        "READ_ERROR": "READ ERROR",
    }
    for cat, label in cat_labels.items():
        print(f"  {label}: {cat_totals[cat]}")
    print()

    print("=" * 80)
    print("COUNTS PER EDITION")
    print("=" * 80)
    for edition in sorted(edition_stats.keys()):
        stats = edition_stats[edition]
        total = sum(stats.values())
        if total == 0:
            continue
        print(f"\n  [{edition}] — {total} total issues:")
        for cat, label in cat_labels.items():
            if stats[cat] > 0:
                print(f"    {label}: {stats[cat]}")

    print()
    print("=" * 80)
    print("ALL ISSUES (file : line : category : description)")
    print("=" * 80)
    for fp, cat, lnum, desc in all_issues_detail:
        print(f"  {fp}:{lnum} [{cat_labels.get(cat, cat)}] {desc}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Files scanned:     {len(all_files)}")
    print(f"  Files with issues:  {files_with_issues}")
    print(f"  Files clean:        {len(all_files) - files_with_issues}")
    print(f"  Total issues:       {len(all_issues_detail)}")
    for cat, label in cat_labels.items():
        print(f"  {label}: {cat_totals[cat]}")
    print("=" * 80)


if __name__ == "__main__":
    main()
