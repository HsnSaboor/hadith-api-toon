#!/usr/bin/env python3
"""
Inline grades and references into section files.

Reads grades.toon and references.toon, aggregates data by book/hadithnumber,
and injects into editions/*/sections/*.toon files.
"""

import os
import re
import csv
import io
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/saboor/code/hadith-api-toon")
GRADES_FILE = ROOT / "grades.toon"
REFERENCES_FILE = ROOT / "references.toon"
EDITIONS_DIR = ROOT / "editions"


def parse_toon_file(filepath):
    """Parse a .toon file and return dict keyed by (book, hadithnumber)."""
    data = defaultdict(dict)
    content = filepath.read_text(encoding="utf-8")

    # Skip header line
    lines = content.strip().split("\n")
    if not lines:
        return data

    # Parse header to get column indices
    header_match = re.match(r'(\w+)\[(\d+)\]\{([^}]+)\}:', lines[0])
    if not header_match:
        print(f"Could not parse header: {lines[0]}")
        return data

    schema_str = header_match.group(3)
    columns = schema_str.split(",")

    # Parse data lines
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Handle CSV parsing with quotes
        reader = csv.reader([line], quotechar='"', doublequote=True)
        try:
            row = next(reader)
        except:
            continue

        if len(row) < len(columns):
            continue

        book = row[0].strip()
        hadith_num = row[1].strip()

        if filepath.name == "grades.toon":
            # grades.toon: book,hadithnumber,grader,grade
            grader = row[2].strip() if len(row) > 2 else ""
            grade = row[3].strip() if len(row) > 3 else ""
            if grader and grade:
                data[(book, hadith_num)][grader] = grade
        else:
            # references.toon: book,hadithnumber,source,takhreej
            source = row[2].strip() if len(row) > 2 else ""
            takhreej = row[3].strip() if len(row) > 3 else ""
            if source and takhreej:
                data[(book, hadith_num)][source] = takhreej

    return data


def aggregate_grades(grades_dict):
    """Aggregate grades into 'Grader1: Grade1; Grader2: Grade2' format."""
    if not grades_dict:
        return ""

    parts = []
    for grader, grade in grades_dict.items():
        if grader and grade:
            parts.append(f"{grader}: {grade}")

    return "; ".join(parts)


def aggregate_references(refs_dict):
    """Aggregate references into 'Source: Text | Source2: Text2' format."""
    if not refs_dict:
        return ""

    parts = []
    for source, text in refs_dict.items():
        if source and text:
            parts.append(f"{source}: {text}")

    return " | ".join(parts)


def reconstruct_csv_row(row):
    """Use csv.writer to properly reconstruct CSV row with quoting."""
    output = io.StringIO()
    writer = csv.writer(output, quotechar='"', quoting=csv.QUOTE_MINIMAL, doublequote=True)
    writer.writerow(row)
    return output.getvalue().strip('\r\n')


def inject_into_section(section_file, book_id, grades_agg, refs_agg):
    """Inject grades and references into section file."""
    content = section_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    if not lines:
        return False

    # Parse header to get column indices
    header_match = re.match(r'hadiths\[(\d+|\w+)\]\{([^}]+)\}:', lines[0])
    if not header_match:
        print(f"  Warning: Cannot parse header in {section_file}")
        return False

    schema_str = header_match.group(2)
    columns = schema_str.split(",")

    # Find grades and reference column indices
    try:
        grade_col_idx = columns.index("grades")
        ref_col_idx = columns.index("reference")
    except ValueError as e:
        print(f"  Warning: Missing column in {section_file}: {e}")
        return False

    # Process data lines
    new_lines = [lines[0]]  # Keep header
    updated = False

    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            new_lines.append(line)
            continue

        # Parse CSV row
        reader = csv.reader([line], quotechar='"', doublequote=True)
        try:
            row = list(next(reader))
        except StopIteration:
            new_lines.append(line)
            continue

        # Get hadith number
        if len(row) < 1:
            new_lines.append(line)
            continue

        hadith_num = row[0].strip()
        key = (book_id, hadith_num)

        # Inject grades
        if key in grades_agg and grade_col_idx < len(row):
            grade_val = grades_agg[key]
            while len(row) <= grade_col_idx:
                row.append("")
            row[grade_col_idx] = grade_val
            updated = True

        # Inject references
        if key in refs_agg and ref_col_idx < len(row):
            ref_val = refs_agg[key]
            while len(row) <= ref_col_idx:
                row.append("")
            row[ref_col_idx] = ref_val
            updated = True

        # Reconstruct line using csv.writer for proper quoting
        new_line = reconstruct_csv_row(row)
        new_lines.append(new_line)

    if updated:
        section_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return updated


def main():
    print("=== Loading grades.toon ===")
    grades_data = parse_toon_file(GRADES_FILE)
    print(f"Loaded {sum(len(v) for v in grades_data.values())} grade entries")

    print("\n=== Loading references.toon ===")
    refs_data = parse_toon_file(REFERENCES_FILE)
    print(f"Loaded {sum(len(v) for v in refs_data.values())} reference entries")

    # Aggregate
    print("\n=== Aggregating grades ===")
    grades_agg = {}
    for (book, hnum), graders in grades_data.items():
        grades_agg[(book, hnum)] = aggregate_grades(graders)
    print(f"Aggregated {len(grades_agg)} unique hadiths with grades")

    print("\n=== Aggregating references ===")
    refs_agg = {}
    for (book, hnum), sources in refs_data.items():
        refs_agg[(book, hnum)] = aggregate_references(sources)
    print(f"Aggregated {len(refs_agg)} unique hadiths with references")

    # Process each book
    print("\n=== Injecting into section files ===")
    total_updated = 0
    
    for book_dir in EDITIONS_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        book = book_dir.name
        sections_dir = book_dir / "sections"
        if not sections_dir.exists():
            continue
        
        for section_file in sections_dir.glob("*.toon"):
            if inject_into_section(section_file, book, grades_agg, refs_agg):
                print(f"  {book}/sections/{section_file.name}")
                total_updated += 1
    
    print(f"\n=== COMPLETE: Updated {total_updated} section files ===")


if __name__ == "__main__":
    main()