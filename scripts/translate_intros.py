#!/usr/bin/env python3
"""
Script to translate intros to all languages for hadith books
Uses deep-translator CLI for translation
"""

import os
import re
import subprocess
import time

BASE_DIR = "/home/saboor/code/hadith-api-toon/editions"

# Language codes for deep-translator
LANG_CODES = {"en": "en", "bn": "bn", "fr": "fr", "id": "id", "ru": "ru", "ur": "ur"}

# Language columns we need to support
ALL_LANGS = ["en", "bn", "fr", "id", "ru", "ur"]


def translate_text(text, target_lang):
    """Translate text using deep-translator"""
    if not text:
        return None

    try:
        cmd = [
            "deep-translator",
            "-trans",
            "Google",
            "-src",
            "en",
            "-tg",
            target_lang,
            "-txt",
            text[:500],  # Limit text length for safety
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error: {result.stderr}")
            return None

    except Exception as e:
        print(f"Translation error: {e}")
        return None


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


def get_languages_for_book(book_path):
    """Extract available languages from the hadiths header"""
    section_file = os.path.join(book_path, "sections", "1.toon")
    if not os.path.exists(section_file):
        return []

    with open(section_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("hadiths["):
                match = re.search(r"hadiths\[\d+\]\{([^}]+)\}", line)
                if match:
                    cols = match.group(1).split(",")
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


def update_intro_metadata(book_path, translations, available_langs):
    """Update the 1.toon file with translated intros"""
    section_file = os.path.join(book_path, "sections", "1.toon")
    if not os.path.exists(section_file):
        return

    with open(section_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the intro line and extract the full intro text
    lines = content.split("\n")
    new_lines = []
    intro_found = False

    for i, line in enumerate(lines):
        if line.strip().startswith("intro:"):
            intro_found = True
            # This is the intro line, keep it as is for now (it's the English one)
            new_lines.append(line)
            # Add translated intros after this
            for lang in ALL_LANGS:
                lang_key = f"intro_{lang}"
                if lang in translations and translations[lang]:
                    new_lines.append(f'  {lang_key}: "{translations[lang]}"')
        else:
            new_lines.append(line)

    with open(section_file, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))


def process_book(book_name, book_path):
    """Process a single book"""
    print(f"\n=== Processing {book_name} ===")

    # Get available languages in this book
    available_langs = get_languages_for_book(book_path)
    print(f"Available language columns: {available_langs}")

    # Get current intro
    current_intro = get_current_intro(book_path)
    if not current_intro:
        print("No intro found!")
        return

    print(f"Current intro (first 80 chars): {current_intro[:80]}...")

    # If intro is not English, we need to first translate it to English
    # Then translate from English to other languages
    translations = {}

    # Determine source language
    # If it's Urdu/Bengali, translate to English first
    if (
        current_intro.startswith("تمام")
        or current_intro.startswith("امام")
        or current_intro.startswith("ال")
    ):
        # Arabic/Urdu text
        print("Detected non-English intro, translating to English first...")
        english_intro = translate_text(current_intro, "en")
        if english_intro:
            translations["en"] = english_intro
            source_intro = english_intro
            print(f"Translated to English: {source_intro[:80]}...")
        else:
            print("Failed to translate to English!")
            source_intro = current_intro
    else:
        # Already in English
        translations["en"] = current_intro
        source_intro = current_intro

    # Translate to other languages
    for lang in ALL_LANGS:
        if lang == "en":
            continue
        if lang in available_langs:
            print(f"Translating to {lang}...")
            translated = translate_text(source_intro, lang)
            if translated:
                translations[lang] = translated
                print(f"  {lang}: {translated[:50]}...")
            else:
                print(f"  Failed to translate to {lang}")
            time.sleep(0.5)  # Rate limiting
        else:
            print(f"Skipping {lang} - not available in this book")

    # Update the metadata
    print(f"Updating metadata with translations...")
    update_intro_metadata(book_path, translations, available_langs)
    print(f"Done!")


def main():
    # Process each book directory
    for book_name in sorted(os.listdir(BASE_DIR)):
        book_path = os.path.join(BASE_DIR, book_name)
        if os.path.isdir(book_path):
            try:
                process_book(book_name, book_path)
            except Exception as e:
                print(f"Error processing {book_name}: {e}")
            time.sleep(1)  # Rate limiting between books


if __name__ == "__main__":
    main()
