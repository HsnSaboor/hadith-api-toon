#!/usr/bin/env python3
"""
Extract references (Takhreej) and grades from ALL Takhreej JSONL files
and merge them into grades.toon and references.toon.

For each book:
  - Reads Takhreej field from Urdu translation (language_id=1)
  - Adds reference entry to references.toon
  - Parses grade from the last parenthetical of Takhreej
  - Adds grade entries (as "Takhreej-Takhreej" grader) to grades.toon

Usage:
    python3 scripts/extract_refs_grades_all.py [--dry-run] [--book <book_id>]

Mode:
    --dry-run   : Show what would be written, no file changes
    --book ID   : Only process one book (e.g. --book bukhari)
    --refs-only : Only update references.toon
    --grades-only: Only update grades.toon
"""

import json
import os
import re
import sys
from collections import defaultdict

REPO_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_SOURCE_DIR = "/home/saboor/takhreej-source/hadith"
GRADES_TOON   = os.path.join(REPO_ROOT, "grades.toon")
REFS_TOON     = os.path.join(REPO_ROOT, "references.toon")

# Map: edition_id → Takhreej JSONL key
BOOK_MAP = {
    "abudawud":                "abu_dawood",
    "bukhari":                 "bukhari",
    "ibnmajah":                "maja",
    "malik":                   "muwatta",
    "muslim":                  "muslim",
    "nasai":                   "nasai",
    "tirmidhi":                "tirmazi",
    "mishkat":                 "mishkat",
    "bayhaqi":                 "beyhaqi",
    "sunan-darmi":             "darmi",
    "sahih-ibn-khuzaymah":     "khuzaymah",
    "musnad-ahmed":            "musnad",     # note: these have 0 takhreej
    "mustadrak":               "mustadrak",  # 0 takhreej
    "musannaf-ibn-abi-shaybah":"Shaybah",    # 0 takhreej
    "silsila-sahih":           "silsila",
    # alzawaid: no matching edition — skip for now
}

# Urdu grade keywords → English translation
URDU_GRADE_MAP = {
    "صحیح":         "Sahih",
    "حسن":          "Hasan",
    "حسن صحیح":     "Hasan Sahih",
    "ضعیف":         "Daif",
    "ضعيف":         "Daif",
    "موضوع":        "Maudu",
    "شاذ":          "Shadh",
    "منکر":         "Munkar",
    "صحیح لغیرہ":   "Sahih Lighairihi",
    "حسن لغیرہ":    "Hasan Lighairihi",
    "مقطوع":        "Maqtu",
    "مرسل":         "Mursal",
    "معضل":         "Mu'dal",
    "ضعیف جدا":     "Very Daif",
    "موقوف":        "Mawquf",
    "صحیح موقوف":   "Sahih Mawquf",
    "ضعیف جداً":    "Very Daif",
    "إسناده صحيح":  "Isnaad Sahih",
    "إسناده حسن":   "Isnaad Hasan",
    "إسناده ضعيف":  "Isnaad Daif",
}

GRADER_NAME = "Takhreej-Takhreej"


def extract_grade_from_takhreej(takhreej: str) -> tuple:
    """
    Parse the last parenthetical from a Takhreej string.
    Returns (urdu_grade, english_grade) or ('', '') if not parseable.
    """
    if not takhreej:
        return ("", "")
    # Grab ALL parentheticals
    matches = re.findall(r'\(([^)]+)\)', takhreej.strip())
    if not matches:
        return ("", "")
    # Try last few parentheticals for grade keyword
    for candidate in reversed(matches):
        candidate = candidate.strip()
        if candidate in URDU_GRADE_MAP:
            return (candidate, URDU_GRADE_MAP[candidate])
        # Check partial match (e.g. "حسن صحیح" within longer candidate)
        for urdu, eng in URDU_GRADE_MAP.items():
            if candidate == urdu:
                return (candidate, eng)
    return ("", "")


def load_jsonl(path: str) -> list:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_existing_refs(refs_path: str) -> dict:
    """Load existing references.toon → {book: {hn: takhreej}}"""
    existing = defaultdict(dict)
    if not os.path.exists(refs_path):
        return existing
    with open(refs_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("references["):
                continue
            parts = line.split(",", 3)
            if len(parts) == 4:
                book, hn, source, takhreej = parts
                existing[book][hn] = takhreej
    return existing


def load_existing_grades(grades_path: str) -> dict:
    """Load existing grades.toon → {book: {hn: {grader: grade}}}"""
    existing = defaultdict(lambda: defaultdict(dict))
    if not os.path.exists(grades_path):
        return existing
    with open(grades_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("grades["):
                continue
            parts = line.split(",", 3)
            if len(parts) == 4:
                book, hn, grader, grade = parts
                existing[book][hn][grader] = grade
    return existing


def write_refs_toon(all_refs: dict, path: str) -> int:
    """Write all_refs {book: {hn: takhreej}} to references.toon"""
    lines = []
    total = 0
    for book in sorted(all_refs.keys()):
        hn_map = all_refs[book]
        for hn in sorted(hn_map.keys(), key=lambda x: float(x) if x.replace('.','',1).isdigit() else 0):
            takhreej = hn_map[hn].strip().replace("\n", " ")
            if takhreej:
                lines.append(f"{book},{hn},takhreej,{takhreej}")
                total += 1

    header = f"references[{total}]{{book,hadithnumber,source,takhreej}}:\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(lines) + "\n")
    return total


def write_grades_toon(all_grades: dict, path: str) -> int:
    """Write all_grades {book: {hn: {grader: grade}}} to grades.toon"""
    lines = []
    total = 0
    for book in sorted(all_grades.keys()):
        for hn in sorted(all_grades[book].keys(),
                         key=lambda x: float(x) if x.replace('.','',1).isdigit() else 0):
            for grader, grade in sorted(all_grades[book][hn].items()):
                lines.append(f"{book},{hn},{grader},{grade}")
                total += 1

    header = f"grades[{total}]{{book,hadithnumber,grader,grade}}:\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(lines) + "\n")
    return total


def load_edition_hadithnumbers(edition_id: str) -> set:
    """
    Load all hadithnumbers present in an edition's Arabic sections + all translation sections.
    Returns a set of string hadith numbers. Empty set = no filtering (accept all).
    """
    nums = set()
    ed_dir = os.path.join(REPO_ROOT, "editions", edition_id)

    # Arabic sections (custom toon format with header line)
    ar_sec = os.path.join(ed_dir, "sections")
    if os.path.isdir(ar_sec):
        for fname in os.listdir(ar_sec):
            if not fname.endswith(".toon"):
                continue
            with open(os.path.join(ar_sec, fname), encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[1:]:  # skip header
                line = line.strip()
                if line:
                    hn = line.split(",")[0].strip().strip('"')
                    if hn:
                        nums.add(hn)

    # Translation sections (JSONL format) — union of all languages
    trans_dir = os.path.join(ed_dir, "translations")
    if os.path.isdir(trans_dir):
        for lang in os.listdir(trans_dir):
            sec_dir = os.path.join(trans_dir, lang, "sections")
            if not os.path.isdir(sec_dir):
                continue
            for fname in os.listdir(sec_dir):
                if not fname.endswith(".toon") or fname.startswith("_"):
                    continue
                with open(os.path.join(sec_dir, fname), encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                rec = json.loads(line)
                                hn = str(rec.get("hadithnumber", "")).strip()
                                if hn:
                                    nums.add(hn)
                            except json.JSONDecodeError:
                                pass

    return nums


def process_book(edition_id: str, takhreej_key: str, records: list,
                 existing_refs: dict, existing_grades: dict,
                 valid_nums: set, dry_run: bool) -> dict:
    """Process one book's records and update existing dicts in-place."""
    new_refs = 0
    updated_refs = 0
    new_grades = 0
    skipped_nums = 0

    book_refs   = existing_refs.get(edition_id, {})
    book_grades = existing_grades.get(edition_id, defaultdict(dict))

    for rec in records:
        hn = str(rec.get("hadees_number", "")).strip()
        if not hn:
            continue

        # Filter: only process if hn is in our edition's hadith numbers
        # If valid_nums is empty, it means we don't have an edition dir yet or it's empty, 
        # but usually we want to preserve what we have or only add what we need.
        if valid_nums and hn not in valid_nums:
            skipped_nums += 1
            continue

        # Get Urdu Takhreej (primary source for references + grade extraction)
        takhreej = ""
        for t in rec.get("translations", []):
            if t.get("language_id") == 1:  # Urdu
                takhreej = (t.get("Takhreej") or "").strip()
                break
        # Fall back to English Takhreej if Urdu is empty
        if not takhreej:
            for t in rec.get("translations", []):
                if t.get("language_id") == 2:  # English
                    takhreej = (t.get("Takhreej") or "").strip()
                    break

        if takhreej:
            # References
            if hn not in book_refs:
                new_refs += 1
            else:
                updated_refs += 1
            book_refs[hn] = takhreej

            # Grades — parse from Takhreej
            urdu_grade, eng_grade = extract_grade_from_takhreej(takhreej)
            if eng_grade:
                if GRADER_NAME not in book_grades[hn]:
                    new_grades += 1
                book_grades[hn][GRADER_NAME] = eng_grade

    # Update the existing dicts
    existing_refs[edition_id] = book_refs
    existing_grades[edition_id] = book_grades

    return {
        "edition": edition_id,
        "records": len(records),
        "takhreej_found": sum(1 for r in records
                              for t in r.get("translations", [])
                              if t.get("language_id") == 1 and (t.get("Takhreej") or "").strip()),
        "new_refs": new_refs,
        "updated_refs": updated_refs,
        "new_grades": new_grades,
        "skipped": skipped_nums,
    }


def main():
    dry_run     = "--dry-run" in sys.argv
    refs_only   = "--refs-only" in sys.argv
    grades_only = "--grades-only" in sys.argv
    only_book   = None
    if "--book" in sys.argv:
        idx = sys.argv.index("--book")
        only_book = sys.argv[idx + 1]

    print("=" * 65)
    print("Takhreej References & Grades Extractor — All Books")
    print("=" * 65)
    if dry_run:
        print("  [DRY RUN — no files will be written]")

    # Load existing data
    print("\n[1] Loading existing references.toon ...")
    existing_refs = load_existing_refs(REFS_TOON)
    print(f"    → {sum(len(v) for v in existing_refs.values())} existing reference entries")

    print("\n[2] Loading existing grades.toon ...")
    existing_grades = load_existing_grades(GRADES_TOON)
    print(f"    → {sum(len(v) for v in existing_grades.values())} existing grade hadiths")

    # Process each book
    print("\n[3] Processing books ...")
    results = []

    books_to_process = {k: v for k, v in BOOK_MAP.items()
                        if only_book is None or k == only_book}

    for edition_id, takhreej_key in sorted(books_to_process.items()):
        jsonl_path = os.path.join(RAW_SOURCE_DIR, f"{takhreej_key}.jsonl")
        if not os.path.exists(jsonl_path):
            print(f"  ⚠️  {edition_id}: JSONL not found ({jsonl_path})")
            continue

        print(f"  Loading {edition_id} ({takhreej_key}.jsonl) ...", end="", flush=True)
        records = load_jsonl(jsonl_path)
        valid_nums = load_edition_hadithnumbers(edition_id)
        result = process_book(edition_id, takhreej_key, records,
                              existing_refs, existing_grades, valid_nums, dry_run)
        results.append(result)
        print(f" {result['records']} records | "
              f"{result['takhreej_found']} with Takhreej | "
              f"+{result['new_refs']} new refs | "
              f"+{result['new_grades']} new grades | "
              f"({result['skipped']} skipped)")

    # Write output
    if not dry_run:
        if not grades_only:
            print(f"\n[4] Writing references.toon ...")
            total_refs = write_refs_toon(existing_refs, REFS_TOON)
            print(f"    → {total_refs} total reference entries")

        if not refs_only:
            print(f"\n[5] Writing grades.toon ...")
            total_grades = write_grades_toon(existing_grades, GRADES_TOON)
            print(f"    → {total_grades} total grade entries")
    else:
        total_refs = sum(len(v) for v in existing_refs.values())
        total_grades = sum(len(v) for v in existing_grades.values())
        print(f"\n[DRY RUN] Would write {total_refs} refs, {total_grades} grade hadiths")

    # Summary table
    print("\n\n" + "=" * 65)
    print("SUMMARY")
    print("=" * 65)
    print(f"  {'Book':<30} {'Records':>8} {'Takhreej':>9} {'NewRefs':>8} {'NewGrades':>10}")
    print("  " + "-" * 60)
    for r in results:
        print(f"  {r['edition']:<30} {r['records']:>8} {r['takhreej_found']:>9} "
              f"{r['new_refs']:>8} {r['new_grades']:>10}")

    total_new_refs   = sum(r["new_refs"]   for r in results)
    total_new_grades = sum(r["new_grades"] for r in results)
    print(f"\n  Total new/updated: {total_new_refs} refs, {total_new_grades} grade entries")
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
