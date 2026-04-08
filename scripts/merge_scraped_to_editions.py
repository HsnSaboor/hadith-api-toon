#!/usr/bin/env python3
"""
Merge scraped_data (enriched with Urdu from fawazahmed0 and English from hadith-json)
into the final edition .toon files.

For each .toon section file:
1. Find the urdu column index and fill empty Urdu cells
2. Find the english column index and fill empty English cells
3. Update Arabic if empty
"""

import json
import os
import sys
import csv
import io

SCRAPED_DIR = "/home/saboor/code/hadith-api-toon/scraped_data"
EDITIONS_DIR = "/home/saboor/code/hadith-api-toon/editions"


def load_scraped_data(scraped_dir):
    """Load all scraped JSON files keyed by (book_key, hadith_number)."""
    lookup = {}
    for fname in os.listdir(scraped_dir):
        if not fname.endswith("_scraped.json"):
            continue
        book_key = fname.replace("_scraped.json", "")
        with open(os.path.join(scraped_dir, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for h_id_str, h_data in data.items():
                try:
                    h_id = int(h_id_str)
                except ValueError:
                    continue
                lookup[(book_key, h_id)] = h_data
    return lookup


def parse_toon_file(path):
    """Parse a .toon file into (metadata_lines, fields, data_rows)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    metadata_lines = []
    fields = []
    data_rows = []
    in_metadata = False

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
            brace_open = stripped.index("{")
            brace_close = stripped.index("}")
            fields = stripped[brace_open + 1 : brace_close].split(",")
            continue

        if fields and stripped:
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


def merge_section_file(path, scraped_lookup, book_key):
    """Merge scraped data into a section file. Returns (new_content, changes_count)."""
    metadata_lines, fields, data_rows = parse_toon_file(path)

    # Find column indices
    urdu_idx = fields.index("urdu") if "urdu" in fields else None
    eng_idx = fields.index("english") if "english" in fields else None
    ar_idx = fields.index("arabic") if "arabic" in fields else None
    intl_idx = (
        fields.index("international_number")
        if "international_number" in fields
        else None
    )

    changes = 0
    new_rows = []

    for row in data_rows:
        try:
            hadithnumber = int(row[0])
        except (ValueError, IndexError):
            try:
                hadithnumber = int(float(row[0]))
            except (ValueError, IndexError):
                new_rows.append(row)
                continue

        scraped = scraped_lookup.get((book_key, hadithnumber), {})

        # Fill Urdu
        if urdu_idx is not None and urdu_idx < len(row):
            current = row[urdu_idx].strip()
            if not current:
                new_urdu = scraped.get("urdu", "").strip()
                if new_urdu:
                    row[urdu_idx] = new_urdu
                    changes += 1

        # Fill English
        if eng_idx is not None and eng_idx < len(row):
            current = row[eng_idx].strip()
            if not current:
                new_eng = scraped.get("english", "").strip()
                if new_eng:
                    row[eng_idx] = new_eng
                    changes += 1

        # Fill Arabic
        if ar_idx is not None and ar_idx < len(row):
            current = row[ar_idx].strip()
            if not current:
                new_ar = scraped.get("arabic", "").strip()
                if new_ar:
                    row[ar_idx] = new_ar
                    changes += 1

        # Fill international_number
        if intl_idx is not None and intl_idx < len(row):
            current = row[intl_idx].strip()
            if not current:
                new_intl = scraped.get("international_number", "")
                if new_intl:
                    row[intl_idx] = str(new_intl)

        new_rows.append(row)

    if changes == 0:
        return None, 0

    # Rebuild file
    header = f"hadiths[{len(new_rows)}]{{{','.join(fields)}}}:"
    out_lines = []
    out_lines.extend(metadata_lines)
    out_lines.append("")
    out_lines.append(header)
    for row in new_rows:
        escaped = [escape_val(v) for v in row]
        out_lines.append(",".join(escaped))

    return "\n".join(out_lines) + "\n", changes


def main():
    print("Loading scraped data...")
    scraped_lookup = load_scraped_data(SCRAPED_DIR)
    print(f"Loaded {len(scraped_lookup)} entries from scraped_data")

    # Map edition dir names to book keys
    book_key_map = {}
    for edition in os.listdir(EDITIONS_DIR):
        ed_path = os.path.join(EDITIONS_DIR, edition)
        if not os.path.isdir(ed_path):
            continue
        # Extract book key from edition name (e.g., "bukhari", "aladab-almufrad")
        # Edition names might have prefixes like "ara-", "eng-", "urd-"
        parts = edition.split("-")
        if len(parts) > 1 and parts[0] in (
            "ara",
            "eng",
            "urd",
            "ben",
            "fre",
            "ind",
            "rus",
        ):
            book_key = "-".join(parts[1:])
        else:
            book_key = edition
        book_key_map[edition] = book_key

    print(f"\nFound {len(book_key_map)} editions")

    total_changes = 0
    total_files = 0

    for edition, book_key in sorted(book_key_map.items()):
        sec_dir = os.path.join(EDITIONS_DIR, edition, "sections")
        if not os.path.isdir(sec_dir):
            continue

        edition_changes = 0
        edition_files = 0

        for fname in sorted(os.listdir(sec_dir)):
            if not fname.endswith(".toon"):
                continue
            fpath = os.path.join(sec_dir, fname)
            try:
                new_content, changes = merge_section_file(
                    fpath, scraped_lookup, book_key
                )
                if new_content and changes > 0:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    edition_changes += changes
                    edition_files += 1
            except Exception as e:
                print(f"  ERROR {edition}/{fname}: {e}")

        if edition_changes > 0:
            print(f"  {edition}: {edition_changes} changes in {edition_files} files")
            total_changes += edition_changes
            total_files += edition_files

    print(f"\n{'=' * 60}")
    print(f"DONE: {total_changes} total changes in {total_files} files")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
