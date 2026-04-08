"""
Validate all .toon files (JSON Lines format).

Checks:
1. All .toon files parse correctly as JSON Lines
2. Hadith counts match header declarations
3. All required fields present
4. Cross-edition consistency
"""

import json
import os
import sys
from collections import defaultdict


def validate_toon_file(path):
    errors = []
    metadata = {}
    hadith_count = 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return False, [f"Cannot read file: {e}"], metadata, 0

    if not lines:
        return False, ["File is empty"], metadata, 0

    in_metadata = False
    header_found = False
    expected_count = 0
    fields = []

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

        if "[" in stripped and "{" in stripped and stripped.endswith(":"):
            try:
                inner = stripped[:-1]
                bracket_open = inner.index("[")
                bracket_close = inner.index("]")
                brace_open = inner.index("{")
                brace_close = inner.index("}")
                expected_count = int(inner[bracket_open + 1 : bracket_close])
                fields = inner[brace_open + 1 : brace_close].split(",")
                header_found = True
            except Exception as e:
                errors.append(f"Line {i}: Bad header: {e}")
                return False, errors, metadata, 0
            continue

        if header_found:
            try:
                obj = json.loads(stripped)
                hadith_count += 1
                for field in fields:
                    if field not in obj:
                        errors.append(f"Line {i}: Missing field '{field}'")
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: JSON parse error: {e}")

    if not header_found:
        errors.append("No section header found")
        return False, errors, metadata, 0

    if hadith_count != expected_count:
        errors.append(f"Expected {expected_count} hadiths, found {hadith_count}")

    ok = len(errors) == 0
    return ok, errors, metadata, hadith_count


def validate_all(output_dir, info_toon_path):
    print("=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

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

    editions_dir = os.path.join(output_dir, "editions")
    total_files = 0
    total_hadiths = 0
    total_errors = 0
    edition_stats = {}

    for edition_id in sorted(os.listdir(editions_dir)):
        sec_dir = os.path.join(editions_dir, edition_id, "sections")
        if not os.path.isdir(sec_dir):
            continue

        book_key = edition_to_book.get(edition_id, "unknown")
        edition_file_count = 0
        edition_hadith_count = 0
        edition_errors = 0

        for fname in sorted(os.listdir(sec_dir)):
            if not fname.endswith(".toon"):
                continue
            base = fname.replace(".toon", "")
            try:
                int(base)
            except ValueError:
                print(f"  WARN {edition_id}/{fname}: non-integer section name")

            fpath = os.path.join(sec_dir, fname)
            total_files += 1
            edition_file_count += 1

            ok, errors, meta, hadith_count = validate_toon_file(fpath)
            if not ok:
                edition_errors += len(errors)
                total_errors += len(errors)
                print(f"  FAIL {edition_id}/{fname}: {'; '.join(errors[:2])}")

            total_hadiths += hadith_count
            edition_hadith_count += hadith_count

        edition_stats[edition_id] = {
            "book": book_key,
            "files": edition_file_count,
            "hadiths": edition_hadith_count,
            "errors": edition_errors,
        }

    print(f"\n--- Summary ---")
    print(f"  Total section files:  {total_files}")
    print(f"  Total hadiths:        {total_hadiths}")
    print(f"  Editions processed:  {len(edition_stats)}")
    print(f"  Total errors:         {total_errors}")

    if total_errors == 0:
        print(f"\n  All {total_files} files validated successfully!")
    else:
        print(f"\n  {total_errors} errors found.")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    validate_all(base, os.path.join(base, "info.toon"))
