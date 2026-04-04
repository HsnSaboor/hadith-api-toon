"""
Merge HuggingFace sunnah.com dataset into existing .toon section files.

Adds new columns: grades, reference, international_number, narrator_chain, chapter_intro
- grades: from HuggingFace dataset (Grade field)
- reference: from HuggingFace dataset (In-book reference field)
- international_number: extracted from In-book reference
- narrator_chain: empty for now (to be scraped from sunnah.com later)
- chapter_intro: empty for now (to be scraped from sunnah.com later)

Also adds arabicnumber column when available.
"""

import json
import os
import re
import sys
from collections import defaultdict


def load_sunnah_dataset(path: str) -> dict:
    """Load the HuggingFace sunnah.com dataset into a lookup dict.

    Returns: {(book_key, chapter_id, hadith_in_book): {grade, reference, arabic, english, ...}}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lookup = {}
    for row in data:
        book = row["Book"]
        chapter = row["Chapter_Number"]
        in_book_ref = row.get("In-book reference", "")
        grade = row.get("Grade", "")
        reference = row.get("Reference", "")
        arabic = row.get("Arabic_Text", "")
        english = row.get("English_Text", "")

        # Extract hadith number from "Book 1, Hadith 2" or just use position
        hadith_in_book = None
        m = re.search(r"Book\s+\d+,\s*Hadith\s+(\d+)", in_book_ref)
        if m:
            hadith_in_book = int(m.group(1))

        # Normalize book name to match our book keys
        book_key = normalize_book(book)

        key = (book_key, chapter, hadith_in_book)
        lookup[key] = {
            "grade": grade or "",
            "reference": reference or "",
            "in_book_ref": in_book_ref or "",
            "arabic": arabic or "",
            "english": english or "",
        }

    return lookup


def normalize_book(name: str) -> str:
    """Map HuggingFace book names to our book keys."""
    mapping = {
        "Sahih al-Bukhari": "bukhari",
        "Sahih Muslim": "muslim",
        "Sunan Abi Dawud": "abudawud",
        "Sunan an-Nasa'i": "nasai",
        "Jami` at-Tirmidhi": "tirmidhi",
        "Sunan Ibn Majah": "ibnmajah",
    }
    return mapping.get(name, name.lower().replace(" ", "-"))


def escape_val(value):
    """Escape a value for toon CSV format (RFC 4180)."""
    if value is None or value == "":
        return ""
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def parse_toon_file(path: str) -> tuple:
    """Parse a .toon file. Returns (metadata_lines, header, fields, data_rows)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    metadata_lines = []
    header = None
    fields = []
    data_rows = []

    in_metadata = False
    header_found = False

    for line in lines:
        raw = line.rstrip("\n")
        stripped = raw.strip()

        if not stripped:
            continue

        if stripped == "metadata:":
            in_metadata = True
            metadata_lines.append(raw)
            continue

        if in_metadata and stripped.startswith("  "):
            metadata_lines.append(raw)
            continue
        elif in_metadata and not stripped.startswith("  "):
            in_metadata = False

        if "[" in stripped and "{" in stripped and stripped.endswith(":"):
            bracket_open = stripped.index("[")
            bracket_close = stripped.index("]")
            brace_open = stripped.index("{")
            brace_close = stripped.index("}")
            count = int(stripped[bracket_open + 1 : bracket_close])
            fields = stripped[brace_open + 1 : brace_close].split(",")
            header = stripped
            header_found = True
            continue

        if header_found and stripped:
            # Parse CSV row handling quoted fields
            import csv
            import io

            reader = csv.reader(io.StringIO(stripped))
            try:
                row = next(reader)
                data_rows.append(row)
            except StopIteration:
                pass

    return metadata_lines, header, fields, data_rows


def merge_section_file(
    path: str, sunnah_lookup: dict, book_key: str, section_id: int
) -> str:
    """Merge sunnah.com data into a section file. Returns new content."""
    metadata_lines, header, fields, data_rows = parse_toon_file(path)

    # Determine which new fields to add
    new_fields = [
        "grades",
        "reference",
        "international_number",
        "narrator_chain",
        "chapter_intro",
    ]
    existing_fields = set(fields)
    fields_to_add = [f for f in new_fields if f not in existing_fields]

    if not fields_to_add:
        return None  # Already merged

    # Build new header
    all_fields = fields + fields_to_add
    new_header = f"hadiths[{len(data_rows)}]{{{','.join(all_fields)}}}:"

    # Build new data rows
    new_rows = []
    for i, row in enumerate(data_rows):
        # Handle decimal hadith numbers like "690.2"
        try:
            hadithnumber = int(row[0]) if row else None
        except (ValueError, IndexError):
            try:
                hadithnumber = int(float(row[0])) if row else None
            except (ValueError, IndexError):
                hadithnumber = None

        # Look up sunnah.com data
        lookup_key = (book_key, section_id, hadithnumber)
        sunnah_data = sunnah_lookup.get(lookup_key, {})

        # Also try with chapter_id as hadithnumber (some datasets use different numbering)
        if not sunnah_data and hadithnumber:
            lookup_key2 = (book_key, section_id, None)
            sunnah_data = sunnah_lookup.get(lookup_key2, {})

        grades = sunnah_data.get("grade", "")
        reference = sunnah_data.get("in_book_ref", "")
        international_number = ""
        narrator_chain = ""
        chapter_intro = ""

        new_row = row + [
            grades,
            reference,
            international_number,
            narrator_chain,
            chapter_intro,
        ]
        new_rows.append(new_row)

    # Build output
    lines = []
    lines.extend(metadata_lines)
    lines.append("")
    lines.append(new_header)
    for row in new_rows:
        escaped = [escape_val(v) for v in row]
        lines.append(",".join(escaped))

    return "\n".join(lines) + "\n"


def merge_all_sections(output_dir: str, sunnah_dataset_path: str):
    """Process all section files and merge sunnah.com data."""
    sunnah_lookup = load_sunnah_dataset(sunnah_dataset_path)
    print(f"Loaded {len(sunnah_lookup)} entries from sunnah.com dataset")

    editions_dir = os.path.join(output_dir, "editions")
    total_merged = 0
    total_skipped = 0
    total_errors = 0

    # Map edition slugs to book keys
    edition_to_book = {}
    editions_toon = os.path.join(output_dir, "editions.toon")
    with open(editions_toon, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("editions["):
                continue
            if line and "," in line:
                parts = line.split(",", 7)
                if len(parts) >= 2:
                    edition_to_book[parts[0]] = parts[1]

    for edition_id in sorted(os.listdir(editions_dir)):
        book_key = edition_to_book.get(edition_id)
        if book_key not in sunnah_lookup:
            # Check if any key in lookup starts with this book key
            matching = [k for k in sunnah_lookup.keys() if k[0] == book_key]
            if not matching:
                continue

        sec_dir = os.path.join(editions_dir, edition_id, "sections")
        if not os.path.isdir(sec_dir):
            continue

        for fname in sorted(os.listdir(sec_dir)):
            if not fname.endswith(".toon"):
                continue

            section_id_str = fname.replace(".toon", "")
            try:
                section_id = int(section_id_str)
            except ValueError:
                section_id = int(float(section_id_str))
            fpath = os.path.join(sec_dir, fname)

            try:
                new_content = merge_section_file(
                    fpath, sunnah_lookup, book_key, section_id
                )
                if new_content:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    total_merged += 1
                else:
                    total_skipped += 1
            except Exception as e:
                total_errors += 1
                print(f"  ERROR {edition_id}/{fname}: {e}")

    print(f"\nMerged: {total_merged} files")
    print(f"Skipped (already merged): {total_skipped}")
    print(f"Errors: {total_errors}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base)
    sunnah_dataset = os.path.join(base, "sunnah_dataset.json")

    if len(sys.argv) > 1:
        sunnah_dataset = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    print(f"Sunnah dataset: {sunnah_dataset}")
    print(f"Output dir: {output_dir}")
    print()

    merge_all_sections(output_dir, sunnah_dataset)
