#!/usr/bin/env python3
"""
Script to translate intros using Python deep_translator library
"""

from deep_translator import GoogleTranslator
import re
import os

BASE_DIR = "/home/saboor/code/hadith-api-toon/editions"

ALL_LANGS = ["en", "bn", "fr", "id", "ru", "ur"]
LANG_MAP = {
    "bengali": "bn",
    "english": "en",
    "french": "fr",
    "indonesian": "id",
    "russian": "ru",
    "urdu": "ur",
}


def translate_text(text, target_lang):
    """Translate text to target language"""
    try:
        translator = GoogleTranslator(source="en", target=target_lang)
        # Translate in chunks if text is too long
        if len(text) > 1000:
            # Split into chunks
            chunks = []
            for i in range(0, len(text), 500):
                chunk = text[i : i + 500]
                # Find last period to avoid cutting words
                last_period = chunk.rfind(".")
                if last_period > 100:
                    chunk = chunk[: last_period + 1]
                chunks.append(chunk)

            translated = ""
            for chunk in chunks:
                result = translator.translate(chunk)
                if result:
                    translated += result + " "
            return translated.strip()
        else:
            result = translator.translate(text)
            return result if result else None
    except Exception as e:
        print(f"Translation error to {target_lang}: {e}")
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


def process_book(book_name, book_path):
    """Process a single book"""
    print(f"\n=== {book_name} ===")

    available_langs = get_languages_for_book(book_path)
    available_short = [LANG_MAP.get(l, l) for l in available_langs]
    print(f"Available: {available_langs} -> {available_short}")

    current_intro = get_current_intro(book_path)
    if not current_intro:
        print("No intro found!")
        return

    # Detect if intro is not English
    if (
        current_intro.startswith("تمام")
        or current_intro.startswith("امام")
        or current_intro.startswith("ال")
        or current_intro.startswith("সব")
    ):
        print("Non-English intro detected")
        # Try to detect source
        if "ال" in current_intro[:10]:
            source = "ar"
        else:
            source = "ur"

        # Translate to English first
        print(f"Translating from {source} to English...")
        try:
            temp_translator = GoogleTranslator(source=source, target="en")
            english_intro = temp_translator.translate(current_intro)
            if english_intro:
                current_intro = english_intro
                print(f"English: {current_intro[:80]}...")
        except Exception as e:
            print(f"Failed: {e}")
            return
    else:
        print(f"English intro: {current_intro[:60]}...")

    translations = {"en": current_intro}

    # Translate to other languages
    for lang in ALL_LANGS:
        if lang == "en":
            continue
        if lang in available_short:
            print(f"Translating to {lang}...")
            print(f"Translating to {lang}...")
            translated = translate_text(current_intro, lang)
            if translated:
                translations[lang] = translated
                print(f"  {lang}: {translated[:50]}...")

    # Update file
    update_file(book_path, translations)


def update_file(book_path, translations):
    """Update the metadata in the file"""
    section_file = os.path.join(book_path, "sections", "1.toon")

    with open(section_file, "r", encoding="utf-8") as f:
        content = f.read()

    existing = set()
    for lang in ["bn", "fr", "id", "ru", "ur"]:
        if f"intro_{lang}:" in content:
            existing.add(lang)
    print(f"Existing translations: {existing}")

    lines = content.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip().startswith("intro:"):
            for lang in ["bn", "fr", "id", "ru", "ur"]:
                if lang in translations and lang != "en" and lang not in existing:
                    new_lines.append(f'  intro_{lang}: "{translations[lang]}"')

    with open(section_file, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    print("Updated!")


def main():
    for book_name in sorted(os.listdir(BASE_DIR)):
        book_path = os.path.join(BASE_DIR, book_name)
        if os.path.isdir(book_path):
            try:
                process_book(book_name, book_path)
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
