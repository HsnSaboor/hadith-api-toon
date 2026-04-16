#!/usr/bin/env python3
"""
Create metadata.toon files for each language translation.
These files contain book intros extracted from info.toon.
"""

import os
import json
import re

BASE_PATH = "/home/saboor/code/hadith-api-toon/editions"

# Map language codes from info.toon to folder names
LANG_MAP = {
    "bn": "intro_bn",
    "fr": "intro_fr",
    "id": "intro_id",
    "ru": "intro_ru",
    "ur": "intro_ur",
}


def parse_info_toon(filepath):
    """Parse info.toon and extract metadata."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    metadata = {}

    # Extract book_id
    match = re.search(r"book_id:\s*(\w+)", content)
    if match:
        metadata["book_id"] = match.group(1)

    # Extract book_name
    match = re.search(r'book_name:\s*"([^"]*)"', content)
    if match:
        metadata["book_name"] = match.group(1)

    # Extract intro fields
    for lang, field in LANG_MAP.items():
        # Match intro field with multiline content
        pattern = rf'{field}:\s*"([^"]*)"'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            metadata[field] = match.group(1).replace("\\n", "\n")

    return metadata


def create_metadata_files():
    """Create metadata.toon files for each book and language."""
    books = [
        d
        for d in os.listdir(BASE_PATH)
        if os.path.isdir(os.path.join(BASE_PATH, d)) and not d.startswith(".")
    ]

    for book in books:
        info_path = os.path.join(BASE_PATH, book, "info.toon")
        if not os.path.exists(info_path):
            continue

        metadata = parse_info_toon(info_path)
        if not metadata:
            continue

        # Create metadata.toon for each language
        for lang, field in LANG_MAP.items():
            if field not in metadata:
                continue

            trans_dir = os.path.join(BASE_PATH, book, "translations", lang)
            if not os.path.exists(trans_dir):
                continue

            # Create metadata.toon
            metadata_path = os.path.join(trans_dir, "metadata.toon")

            data = {
                "type": "book_intro",
                "book_id": metadata.get("book_id", book),
                "book_name": metadata.get("book_name", ""),
                "language": lang,
                "text": metadata[field],
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")

            print(f"Created: {book}/translations/{lang}/metadata.toon")


if __name__ == "__main__":
    create_metadata_files()
    print("\n✅ Metadata files created!")
