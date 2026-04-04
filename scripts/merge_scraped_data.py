"""
Merge scraped quranohadith.com data into existing .toon section files.

Adds:
- urdu text (new column)
- international_number (new column)
- chapter_title_arabic (new column)

Also generates urd-{book} editions for all 7 books.
"""

import json
import os
import sys
import csv
import io
from collections import defaultdict


def load_scraped_data(scraped_dir: str) -> dict:
    """Load all scraped JSON files into {(book_key, hadith_id): data}."""
    lookup = {}
    for fname in os.listdir(scraped_dir):
        if not fname.endswith("_scraped.json"):
            continue
        book_key = fname.replace("_scraped.json", "")
        with open(os.path.join(scraped_dir, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        # Handle both dict and list formats
        if isinstance(data, list):
            for item in data:
                h_id = item.get("hadith_number") or item.get("hadith_id")
                if h_id:
                    lookup[(book_key, int(h_id))] = item
        elif isinstance(data, dict):
            for h_id_str, h_data in data.items():
                try:
                    h_id = int(h_id_str)
                except ValueError:
                    continue
                lookup[(book_key, h_id)] = h_data
    return lookup


def parse_toon_file(path: str) -> tuple:
    """Parse a .toon file. Returns (metadata_lines, header, fields, data_rows)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    metadata_lines = []
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
            fields = stripped[brace_open + 1 : brace_close].split(",")
            header_found = True
            continue

        if header_found and stripped:
            reader = csv.reader(io.StringIO(stripped))
            try:
                row = next(reader)
                data_rows.append(row)
            except StopIteration:
                pass

    return metadata_lines, fields, data_rows


def escape_val(value):
    if value is None or value == "":
        return ""
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def merge_section_file(path: str, scraped_lookup: dict, book_key: str) -> str | None:
    """Merge scraped data into a section file. Returns new content or None if no changes."""
    metadata_lines, fields, data_rows = parse_toon_file(path)

    # Fields to add (in order)
    new_fields = ["urdu", "international_number", "chapter_title_arabic"]
    fields_to_add = [f for f in new_fields if f not in fields]

    if not fields_to_add:
        return None

    all_fields = fields + fields_to_add
    new_header = f"hadiths[{len(data_rows)}]{{{','.join(all_fields)}}}:"

    new_rows = []
    for row in data_rows:
        try:
            hadithnumber = int(row[0])
        except (ValueError, IndexError):
            try:
                hadithnumber = int(float(row[0]))
            except (ValueError, IndexError):
                hadithnumber = None

        scraped = scraped_lookup.get((book_key, hadithnumber), {})

        urdu = scraped.get("urdu", "")
        intl_num = scraped.get("international_number", "")
        chapter_title = scraped.get("chapter_title_arabic", "")

        new_row = row + [urdu, str(intl_num) if intl_num else "", chapter_title]
        new_rows.append(new_row)

    lines = []
    lines.extend(metadata_lines)
    lines.append("")
    lines.append(new_header)
    for row in new_rows:
        escaped = [escape_val(v) for v in row]
        lines.append(",".join(escaped))

    return "\n".join(lines) + "\n"


def generate_urdu_edition(book_key: str, editions_dir: str, scraped_lookup: dict):
    """Generate urd-{book} edition from existing section files + scraped Urdu data."""
    # Find source edition
    src_edition = None
    for d in os.listdir(editions_dir):
        if d.endswith(f"-{book_key}"):
            src_edition = d
            break
    if not src_edition:
        return 0

    src_sec_dir = os.path.join(editions_dir, src_edition, "sections")
    if not os.path.isdir(src_sec_dir):
        return 0

    dst_edition = f"urd-{book_key}"
    dst_sec_dir = os.path.join(editions_dir, dst_edition, "sections")
    os.makedirs(dst_sec_dir, exist_ok=True)

    total_hadiths = 0

    for fname in sorted(os.listdir(src_sec_dir)):
        if not fname.endswith(".toon"):
            continue

        src_path = os.path.join(src_sec_dir, fname)
        dst_path = os.path.join(dst_sec_dir, fname)

        metadata_lines, fields, data_rows = parse_toon_file(src_path)

        # Urdu edition only has: hadithnumber, text(urdu), grades, reference, international_number, narrator_chain, chapter_intro, urdu(from scraped), chapter_title_arabic
        # But we want just: hadithnumber, text(urdu), grades, reference, international_number, narrator_chain, chapter_intro
        # The 'text' field will be the Urdu text from scraped data

        # Find the urdu column index
        urdu_idx = None
        if "urdu" in fields:
            urdu_idx = fields.index("urdu")
        intl_idx = (
            fields.index("international_number")
            if "international_number" in fields
            else None
        )
        chapter_idx = (
            fields.index("chapter_title_arabic")
            if "chapter_title_arabic" in fields
            else None
        )
        grades_idx = fields.index("grades") if "grades" in fields else None
        ref_idx = fields.index("reference") if "reference" in fields else None

        urdu_rows = []
        for row in data_rows:
            try:
                hadithnumber = int(row[0])
            except (ValueError, IndexError):
                try:
                    hadithnumber = int(float(row[0]))
                except (ValueError, IndexError):
                    hadithnumber = None

            # Get Urdu text: prefer scraped data, fallback from existing column
            urdu_text = ""
            if urdu_idx is not None and urdu_idx < len(row):
                urdu_text = row[urdu_idx]
            if not urdu_text and hadithnumber:
                scraped = scraped_lookup.get((book_key, hadithnumber), {})
                urdu_text = scraped.get("urdu", "")

            if not urdu_text:
                continue

            grades = (
                row[grades_idx]
                if grades_idx is not None and grades_idx < len(row)
                else ""
            )
            reference = (
                row[ref_idx] if ref_idx is not None and ref_idx < len(row) else ""
            )
            intl_num = (
                row[intl_idx] if intl_idx is not None and intl_idx < len(row) else ""
            )
            chapter_title = (
                row[chapter_idx]
                if chapter_idx is not None and chapter_idx < len(row)
                else ""
            )

            urdu_rows.append(
                [
                    str(hadithnumber),
                    urdu_text,
                    grades,
                    reference,
                    intl_num,
                    "",  # narrator_chain
                    chapter_title,
                ]
            )

        if not urdu_rows:
            continue

        # Write Urdu edition
        urdu_fields = [
            "hadithnumber",
            "text",
            "grades",
            "reference",
            "international_number",
            "narrator_chain",
            "chapter_intro",
        ]
        header = f"hadiths[{len(urdu_rows)}]{{{','.join(urdu_fields)}}}:"

        lines = []
        lines.extend(metadata_lines)
        lines.append("")
        lines.append(header)
        for row in urdu_rows:
            escaped = [escape_val(v) for v in row]
            lines.append(",".join(escaped))

        with open(dst_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        total_hadiths += len(urdu_rows)

    return total_hadiths


def main(scraped_dir: str, editions_dir: str):
    print("Loading scraped data...")
    scraped_lookup = load_scraped_data(scraped_dir)
    print(f"Loaded {len(scraped_lookup)} entries")

    books = ["bukhari", "muslim", "abudawud", "ibnmajah", "malik", "nasai", "tirmidhi"]
    merged_files = 0
    skipped_files = 0

    # Merge into existing editions
    print("\n=== Merging scraped data into existing editions ===")
    for book_key in books:
        for edition in sorted(os.listdir(editions_dir)):
            if not edition.endswith(f"-{book_key}"):
                continue
            sec_dir = os.path.join(editions_dir, edition, "sections")
            if not os.path.isdir(sec_dir):
                continue

            for fname in sorted(os.listdir(sec_dir)):
                if not fname.endswith(".toon"):
                    continue
                fpath = os.path.join(sec_dir, fname)
                try:
                    new_content = merge_section_file(fpath, scraped_lookup, book_key)
                    if new_content:
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        merged_files += 1
                    else:
                        skipped_files += 1
                except Exception as e:
                    print(f"  ERROR {edition}/{fname}: {e}")

    print(f"Merged: {merged_files} files, Skipped: {skipped_files}")

    # Generate Urdu editions
    print("\n=== Generating Urdu editions ===")
    for book_key in books:
        count = generate_urdu_edition(book_key, editions_dir, scraped_lookup)
        print(f"  urd-{book_key}: {count} hadiths")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scraped_dir = os.path.join(base, "scraped_data")
    editions_dir = os.path.join(base, "editions")

    if len(sys.argv) > 1:
        scraped_dir = sys.argv[1]
    if len(sys.argv) > 2:
        editions_dir = sys.argv[2]

    main(scraped_dir, editions_dir)
