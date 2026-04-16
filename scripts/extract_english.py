#!/usr/bin/env python3
"""
Extract English translations from main section files to translations/en/
"""

import os
import csv
import json

BASE_PATH = "/home/saboor/code/hadith-api-toon/editions"


def extract_english_from_section(filepath):
    """Extract English translations from CSV section file."""
    hadiths = []

    with open(filepath, "r", encoding="utf-8") as f:
        header_line = f.readline().strip()
        if "hadiths[" not in header_line:
            return None

        reader = csv.reader(f)
        for row in reader:
            if len(row) < 14:
                continue

            hadith = {
                "hadithnumber": row[0].strip().strip('"'),
                "text": row[3].strip().strip('"'),  # English column
            }

            if hadith["hadithnumber"] and hadith["hadithnumber"] != "hadithnumber":
                hadiths.append(hadith)

    return hadiths


def process_all_books():
    """Extract English from all books."""
    books = [
        d
        for d in os.listdir(BASE_PATH)
        if os.path.isdir(os.path.join(BASE_PATH, d)) and not d.startswith(".")
    ]

    total = 0
    for book in books:
        sections_dir = os.path.join(BASE_PATH, book, "sections")
        en_dir = os.path.join(BASE_PATH, book, "translations", "en", "sections")

        if not os.path.exists(sections_dir):
            continue

        # Create English translations dir
        os.makedirs(en_dir, exist_ok=True)

        section_files = [f for f in os.listdir(sections_dir) if f.endswith(".toon")]
        if not section_files:
            continue

        book_count = 0
        for section_file in section_files:
            filepath = os.path.join(sections_dir, section_file)
            hadiths = extract_english_from_section(filepath)

            if hadiths is None:
                continue

            # Write English translations
            en_path = os.path.join(en_dir, section_file)
            with open(en_path, "w", encoding="utf-8") as f:
                for hadith in hadiths:
                    json_line = json.dumps(hadith, ensure_ascii=False)
                    f.write(json_line + "\n")
                    book_count += 1

        if book_count > 0:
            print(f"✅ {book}: {book_count} English hadiths extracted")
            total += book_count

    print(f"\n✅ Total English hadiths extracted: {total}")


if __name__ == "__main__":
    process_all_books()
