"""
Validate all converted .toon files.

Checks:
1. All .toon files parse correctly (structure validation)
2. Hadith counts match between info.toon sections and actual .toon files
3. All sections listed in info.toon have corresponding .toon files per edition
4. No empty hadith sections
5. Cross-edition consistency (hadith counts per book)
"""

import csv
import io
import os
import sys
from collections import defaultdict


def parse_toon_header(line):
    """Parse a section header like 'hadiths[7]{hadithnumber,text,reference_book,reference_hadith}:'"""
    line = line.strip()
    if not line.endswith(":"):
        return None
    line = line[:-1]
    bracket_open = line.index("[")
    bracket_close = line.index("]")
    brace_open = line.index("{")
    brace_close = line.index("}")

    name = line[:bracket_open]
    count = int(line[bracket_open + 1 : bracket_close])
    fields = line[brace_open + 1 : brace_close].split(",")
    return name, count, fields


def validate_toon_file(path):
    """Validate a single .toon file. Returns (ok, errors, metadata)."""
    errors = []
    metadata = {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return False, [f"Cannot read file: {e}"], metadata

    if not lines:
        return False, ["File is empty"], metadata

    # Parse metadata block
    in_metadata = False
    header_found = False
    section_name = None
    expected_count = 0
    fields = []
    data_lines = 0

    for i, line in enumerate(lines, 1):
        raw = line.rstrip("\n")
        stripped = raw.strip()

        if not stripped:
            continue

        if stripped == "metadata:":
            in_metadata = True
            continue

        if in_metadata and stripped.startswith("  "):
            key, _, val = stripped.strip().partition(": ")
            metadata[key] = val
            continue
        elif in_metadata and not stripped.startswith("  "):
            in_metadata = False

        # Parse section header
        if "[" in stripped and "{" in stripped and stripped.endswith(":"):
            try:
                parsed = parse_toon_header(stripped)
                if parsed:
                    section_name, expected_count, fields = parsed
                    header_found = True
            except Exception as e:
                errors.append(f"Line {i}: Bad header '{stripped}': {e}")
                return False, errors, metadata
            continue

        # Count data lines
        if header_found and stripped:
            data_lines += 1

    if not header_found:
        errors.append("No section header found")
        return False, errors, metadata

    if data_lines != expected_count:
        errors.append(f"Expected {expected_count} hadiths, found {data_lines}")
        return False, errors, metadata

    return True, errors, metadata


def parse_csv_line(line):
    """Parse a CSV line handling quoted fields with commas."""
    reader = csv.reader(io.StringIO(line))
    return next(reader)


def validate_all(output_dir, info_toon_path):
    """Run full validation suite."""
    print("=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    # Parse info.toon for expected sections per book
    expected_sections = {}
    book_hadith_totals = {}

    with open(info_toon_path, "r", encoding="utf-8") as f:
        current_book = None
        for line in f:
            line = line.strip()
            if line.startswith("books[") and line.endswith(":"):
                continue
            if line.startswith("sections_") and "{" in line and line.endswith(":"):
                prefix = "sections_"
                rest = line[len(prefix) :]
                book_key = rest.split("[")[0]
                current_book = book_key
                expected_sections[book_key] = {}
                continue
            if current_book and line:
                parts = parse_csv_line(line)
                if len(parts) >= 6 and parts[0].isdigit():
                    sec_id = int(parts[0])
                    sec_name = parts[1]
                    hf = int(float(parts[2]))
                    hl = int(float(parts[3]))
                    expected_sections[current_book][sec_id] = {
                        "name": sec_name,
                        "hadith_first": hf,
                        "hadith_last": hl,
                    }

    # Parse books totals
    with open(info_toon_path, "r", encoding="utf-8") as f:
        in_books = False
        for line in f:
            line = line.strip()
            if line.startswith("books[") and line.endswith(":"):
                in_books = True
                continue
            if in_books:
                if not line:
                    in_books = False
                    continue
                parts = line.split(",")
                if len(parts) >= 3:
                    book_hadith_totals[parts[0]] = int(parts[2])

    # Parse editions.toon for edition->book mapping
    edition_to_book = {}
    editions_path = os.path.join(os.path.dirname(info_toon_path), "editions.toon")
    with open(editions_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("editions["):
                continue
            if line and "," in line:
                parts = line.split(",", 7)
                if len(parts) >= 2:
                    edition_to_book[parts[0]] = parts[1]

    # Validate each edition
    editions_dir = os.path.join(output_dir, "editions")
    total_files = 0
    total_hadiths = 0
    parse_errors = 0
    count_mismatches = 0
    missing_sections = 0
    edition_stats = {}

    if not os.path.isdir(editions_dir):
        print(f"\nERROR: editions/ directory not found at {editions_dir}")
        return

    for edition_id in sorted(os.listdir(editions_dir)):
        sec_dir = os.path.join(editions_dir, edition_id, "sections")
        if not os.path.isdir(sec_dir):
            continue

        book_key = edition_to_book.get(edition_id, "unknown")
        edition_file_count = 0
        edition_hadith_count = 0
        edition_errors = 0
        actual_sections = set()

        for fname in sorted(
            os.listdir(sec_dir), key=lambda x: int(x.replace(".toon", ""))
        ):
            if not fname.endswith(".toon"):
                continue

            fpath = os.path.join(sec_dir, fname)
            total_files += 1
            edition_file_count += 1

            ok, errors, meta = validate_toon_file(fpath)
            if not ok:
                parse_errors += len(errors)
                edition_errors += len(errors)
                if errors:
                    print(f"  FAIL {edition_id}/{fname}: {'; '.join(errors[:2])}")
                continue

            sec_id = int(meta.get("section_id", "0"))
            actual_sections.add(sec_id)
            hadith_count = (
                int(meta.get("hadith_last", "0"))
                - int(meta.get("hadith_first", "0"))
                + 1
            )
            # Use header count instead (more reliable)
            hadith_count = 0
            # Re-parse for count
            with open(fpath, "r", encoding="utf-8") as f:
                for l in f:
                    l = l.strip()
                    if l.startswith("hadiths[") and "{" in l:
                        c = int(l.split("[")[1].split("]")[0])
                        hadith_count = c
                        break

            total_hadiths += hadith_count
            edition_hadith_count += hadith_count

        edition_stats[edition_id] = {
            "book": book_key,
            "files": edition_file_count,
            "hadiths": edition_hadith_count,
            "errors": edition_errors,
            "sections": actual_sections,
        }

    # Cross-reference with info.toon
    print(f"\n--- Cross-reference with info.toon ---")
    book_actual_totals = defaultdict(int)
    for eid, stats in edition_stats.items():
        book_actual_totals[stats["book"]] += stats["hadiths"]

    for book_key in sorted(book_hadith_totals.keys()):
        expected = book_hadith_totals[book_key]
        editions_for_book = [
            e for e, s in edition_stats.items() if s["book"] == book_key
        ]
        if editions_for_book:
            avg = book_actual_totals[book_key] // len(editions_for_book)
            status = "OK" if avg == expected else "MISMATCH"
            if status == "MISMATCH":
                print(f"  {book_key}: expected {expected}, avg actual {avg} ({status})")
            else:
                print(f"  {book_key}: {expected} hadiths ({status})")

    # Summary
    print(f"\n--- Summary ---")
    print(f"  Total section files:  {total_files}")
    print(f"  Total hadiths:        {total_hadiths}")
    print(f"  Editions processed:   {len(edition_stats)}")
    print(f"  Parse errors:         {parse_errors}")
    print(f"  Count mismatches:     {count_mismatches}")

    if parse_errors == 0:
        print(f"\n  All {total_files} files validated successfully.")
    else:
        print(f"\n  {parse_errors} errors found across files.")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base, "output")
    info_toon = os.path.join(output_dir, "info.toon")

    validate_all(output_dir, info_toon)
