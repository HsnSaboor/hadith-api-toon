#!/usr/bin/env python3
"""
Extract hadith translations from git commit 56db4b8^ (before unification)
and create per-language translation files in the new structure.
"""

import subprocess
import json
import os
import re

# Mapping from old directory names to new book names
BOOK_MAPPING = {
    "abudawud": "abudawud",
    "bukhari": "bukhari",
    "dehlawi": "dehlawi",
    "ibnmajah": "ibnmajah",
    "malik": "malik",
    "muslim": "muslim",
    "nasai": "nasai",
    "nawawi": "nawawi",
    "qudsi": "qudsi",
    "tirmidhi": "tirmidhi",
}

# Language codes: old prefix -> new folder name
LANG_MAPPING = {
    "ben": "bn",
    "fra": "fr",
    "ind": "id",
    "rus": "ru",
    "urd": "ur",
}


def run_git_command(cmd):
    """Run git command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


def get_files_for_book_lang(book, lang):
    """Get all section files for a specific book and language at commit 56db4b8^."""
    old_book_name = f"{lang}-{book}"
    cmd = f"git ls-tree -r 56db4b8^ --name-only | grep '^editions/{old_book_name}/sections/'"
    output = run_git_command(cmd)
    if output:
        return output.split("\n")
    return []


def parse_old_toon(content):
    """Parse old toon format and extract hadithnumber and text."""
    hadiths = []
    lines = content.strip().split("\n")

    # Skip metadata header
    data_started = False
    for line in lines:
        if "hadiths[" in line:
            data_started = True
            continue
        if not data_started:
            continue
        if not line.strip():
            continue

        # Parse CSV-like format: hadithnumber,text,grades,reference...
        # Handle quoted fields properly
        parts = []
        current = ""
        in_quotes = False
        i = 0
        while i < len(line):
            char = line[i]
            if char == '"':
                if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                    current += '"'
                    i += 2
                    continue
                in_quotes = not in_quotes
            elif char == "," and not in_quotes:
                parts.append(current)
                current = ""
            else:
                current += char
            i += 1
        parts.append(current)

        if len(parts) >= 2:
            hadithnumber = parts[0].strip().strip('"')
            text = parts[1].strip().strip('"')
            if hadithnumber and text:
                hadiths.append({"hadithnumber": hadithnumber, "text": text})

    return hadiths


def extract_translations():
    """Main extraction function."""
    base_path = "/home/saboor/code/hadith-api-toon/editions"

    for old_lang, new_lang in LANG_MAPPING.items():
        print(f"\n=== Processing {old_lang} -> {new_lang} ===")

        for book in BOOK_MAPPING.keys():
            files = get_files_for_book_lang(book, old_lang)
            if not files:
                continue

            print(f"  {book}: {len(files)} section files")

            # Create translations directory
            trans_dir = os.path.join(
                base_path, book, "translations", new_lang, "sections"
            )
            os.makedirs(trans_dir, exist_ok=True)

            for file_path in files:
                # Get section number from filename
                section = os.path.basename(file_path).replace(".toon", "")

                # Get file content from git
                cmd = f"git show 56db4b8^:{file_path}"
                content = run_git_command(cmd)

                if not content:
                    continue

                # Parse and convert
                hadiths = parse_old_toon(content)

                if hadiths:
                    # Write new format
                    output_path = os.path.join(trans_dir, f"{section}.toon")
                    with open(output_path, "w", encoding="utf-8") as f:
                        for hadith in hadiths:
                            json_line = json.dumps(hadith, ensure_ascii=False)
                            f.write(json_line + "\n")


if __name__ == "__main__":
    extract_translations()
    print("\n✅ Extraction complete!")
