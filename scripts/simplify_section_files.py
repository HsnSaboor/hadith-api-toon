#!/usr/bin/env python3
"""
Simplify Arabic section files by removing translation columns.
Keep only: hadithnumber, arabic, grades, reference, international_number, narrator_chain
"""

import os
import csv
import json

BASE_PATH = "/home/saboor/code/hadith-api-toon/editions"


def simplify_section_file(filepath):
    """Read CSV section file and simplify to JSON Lines format."""
    hadiths = []

    with open(filepath, "r", encoding="utf-8") as f:
        # Read header line
        header_line = f.readline().strip()

        # Check if it's the expected format
        if "hadiths[" not in header_line:
            return None

        # Parse CSV
        reader = csv.reader(f)
        for row in reader:
            if (
                len(row) < 12
            ):  # Expected columns (hadithnumber, arabic, + at least 10 more)
                continue

            # Map columns: hadithnumber, arabic, bengali, english, french, indonesian, russian, urdu, grades, reference, international_number, narrator_chain, chapter_intro
            hadith = {
                "hadithnumber": row[0].strip().strip('"'),
                "arabic": row[1].strip().strip('"'),
                "grades": row[8].strip().strip('"') if len(row) > 8 else "",
                "reference": row[9].strip().strip('"') if len(row) > 9 else "",
                "international_number": row[10].strip().strip('"')
                if len(row) > 10
                else "",
                "narrator_chain": row[11].strip().strip('"') if len(row) > 11 else "",
            }

            # Only add if has valid hadithnumber
            if hadith["hadithnumber"] and hadith["hadithnumber"] != "hadithnumber":
                hadiths.append(hadith)

    return hadiths


def process_all_books():
    """Process all books and simplify their section files."""
    books = [
        d
        for d in os.listdir(BASE_PATH)
        if os.path.isdir(os.path.join(BASE_PATH, d)) and not d.startswith(".")
    ]

    for book in books:
        sections_dir = os.path.join(BASE_PATH, book, "sections")
        if not os.path.exists(sections_dir):
            continue

        section_files = [f for f in os.listdir(sections_dir) if f.endswith(".toon")]
        if not section_files:
            continue

        print(f"Processing {book}: {len(section_files)} sections")

        for section_file in section_files:
            filepath = os.path.join(sections_dir, section_file)
            hadiths = simplify_section_file(filepath)

            if hadiths is None:
                continue

            # Write simplified format
            with open(filepath, "w", encoding="utf-8") as f:
                for hadith in hadiths:
                    json_line = json.dumps(hadith, ensure_ascii=False)
                    f.write(json_line + "\n")


if __name__ == "__main__":
    process_all_books()
    print("\n✅ Section files simplified!")
