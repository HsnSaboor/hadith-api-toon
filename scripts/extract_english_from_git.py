#!/usr/bin/env python3
"""
Extract English translations from git commit 56db4b8^.
English was in editions/eng-{book}/sections/ folders.
"""

import os
import subprocess
import csv
import json

BOOKS = [
    "abudawud",
    "bukhari",
    "ibnmajah",
    "malik",
    "muslim",
    "nasai",
    "tirmidhi",
    "nawawi",
    "qudsi",
    "dehlawi",
]

BASE_PATH = "/home/saboor/code/hadith-api-toon/editions"
COMMIT = "56db4b8^"


def get_eng_file_from_git(book, section):
    """Get English section file content from git."""
    path = f"editions/eng-{book}/sections/{section}.toon"
    try:
        result = subprocess.run(
            ["git", "show", f"{COMMIT}:{path}"],
            capture_output=True,
            text=True,
            cwd="/home/saboor/code/hadith-api-toon",
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def extract_from_csv(content):
    """Extract hadiths from CSV content."""
    hadiths = []
    lines = content.strip().split("\n")

    # Find header line (starts with hadiths[)
    header_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("hadiths["):
            header_idx = i
            break

    if header_idx == -1:
        return hadiths

    reader = csv.reader(lines[header_idx + 1 :])
    for row in reader:
        if len(row) < 2:
            continue

        hadith = {
            "hadithnumber": row[0].strip().strip('"'),
            "text": row[1].strip().strip('"') if len(row) > 1 else "",
        }

        if hadith["hadithnumber"] and hadith["text"]:
            hadiths.append(hadith)

    return hadiths


def process_book(book):
    """Extract English for a book."""
    # Get list of sections from current directory
    sections_dir = os.path.join(BASE_PATH, book, "sections")
    if not os.path.exists(sections_dir):
        return 0

    section_files = [f for f in os.listdir(sections_dir) if f.endswith(".toon")]

    en_dir = os.path.join(BASE_PATH, book, "translations", "en", "sections")
    os.makedirs(en_dir, exist_ok=True)

    total = 0
    for section_file in section_files:
        section_num = section_file.replace(".toon", "")
        content = get_eng_file_from_git(book, section_num)

        if not content:
            continue

        hadiths = extract_from_csv(content)
        if not hadiths:
            continue

        # Write English translations
        en_path = os.path.join(en_dir, section_file)
        with open(en_path, "w", encoding="utf-8") as f:
            for hadith in hadiths:
                json_line = json.dumps(hadith, ensure_ascii=False)
                f.write(json_line + "\n")
                total += 1

    return total


def main():
    grand_total = 0
    for book in BOOKS:
        count = process_book(book)
        if count > 0:
            print(f"✅ {book}: {count} English hadiths")
            grand_total += count

    print(f"\n✅ Total English hadiths extracted: {grand_total}")


if __name__ == "__main__":
    main()
