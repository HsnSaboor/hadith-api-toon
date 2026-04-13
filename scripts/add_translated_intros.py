#!/usr/bin/env python3
"""
Script to add translated intros to all hadith books
"""

import os
import re

# Base directory
BASE_DIR = "/home/saboor/code/hadith-api-toon/editions"

# Language mapping for intro fields
LANG_MAP = {
    "en": "intro_en",
    "bn": "intro_bn",
    "fr": "intro_fr",
    "id": "intro_id",
    "ru": "intro_ru",
    "ur": "intro_ur",
}

# Language names for translation
LANG_NAMES = {
    "en": "English",
    "bn": "Bengali",
    "fr": "French",
    "id": "Indonesian",
    "ru": "Russian",
    "ur": "Urdu",
}


def get_languages_for_book(book_path):
    """Extract available languages from the hadiths header"""
    section_file = os.path.join(book_path, "sections", "1.toon")
    if not os.path.exists(section_file):
        return []

    with open(section_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("hadiths["):
                # Extract language columns
                match = re.search(r"hadiths\[\d+\]\{([^}]+)\}", line)
                if match:
                    cols = match.group(1).split(",")
                    # Filter out non-language columns
                    langs = [
                        c.strip()
                        for c in cols
                        if c.strip()
                        not in [
                            "hadithnumber",
                            "arabic",
                            "grades",
                            "reference",
                            "international_number",
                            "narrator_chain",
                            "chapter_intro",
                        ]
                    ]
                    return langs
    return []


def get_current_intro(book_path):
    """Get the current intro text"""
    section_file = os.path.join(book_path, "sections", "1.toon")
    if not os.path.exists(section_file):
        return None

    with open(section_file, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'intro:\s*"(.+?)"', content, re.DOTALL)
        if match:
            return match.group(1)
    return None


def get_book_info():
    """Get info for all books"""
    books = {}
    for book_name in os.listdir(BASE_DIR):
        book_path = os.path.join(BASE_DIR, book_name)
        if os.path.isdir(book_path):
            langs = get_languages_for_book(book_path)
            intro = get_current_intro(book_path)
            books[book_name] = {
                "path": book_path,
                "languages": langs,
                "current_intro": intro,
            }
    return books


def main():
    books = get_book_info()

    for book_name, info in books.items():
        print(f"\n=== {book_name} ===")
        print(f"Languages: {info['languages']}")
        print(
            f"Current intro (first 100 chars): {info['current_intro'][:100] if info['current_intro'] else 'None'}..."
        )


if __name__ == "__main__":
    main()
