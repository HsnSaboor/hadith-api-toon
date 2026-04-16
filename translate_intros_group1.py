#!/usr/bin/env python3
"""
Translate book intros for Group 1: abudawud, aladab-almufrad, bayhaqi, bukhari, bulugh-al-maram
Target languages: Spanish (es), Turkish (tr), Hindi (hi)
"""

from deep_translator import GoogleTranslator
import re


def split_text_into_chunks(text, max_chars=4000):
    if len(text) <= max_chars:
        return [text]
    chunks = []
    current_chunk = ""
    paragraphs = text.split("\n\n")
    for para in paragraphs:
        if len(para) > max_chars:
            lines = para.split("\n")
            for line in lines:
                if len(current_chunk) + len(line) + 1 <= max_chars:
                    current_chunk += line + "\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
        else:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def translate_text(text, target_lang):
    if not text or not text.strip():
        return None
    try:
        translator = GoogleTranslator(source="en", target=target_lang)
        if len(text) <= 4000:
            return translator.translate(text)
        chunks = split_text_into_chunks(text, max_chars=4000)
        translated_chunks = []
        for chunk in chunks:
            if chunk.strip():
                translated = translator.translate(chunk)
                translated_chunks.append(translated)
        return "\n\n".join(translated_chunks)
    except Exception as e:
        print(f"Error translating to {target_lang}: {e}")
        return None


def read_info_file(filepath):
    """Read info.toon file and return content as string"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def extract_intro(content):
    """Extract the intro field from the toon content"""
    # Match intro: "...content..." (multiline)
    match = re.search(r'intro:\s*"([^"]*)"', content, re.DOTALL)
    if match:
        return match.group(1)
    return None


def replace_intro(content, field_name, new_value):
    """Replace a specific intro field in the content"""
    # Escape special characters for regex
    escaped_value = (
        new_value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    )
    pattern = rf'({field_name}:\s*)"[^"]*"'
    replacement = rf'\1"{escaped_value}"'
    return re.sub(pattern, replacement, content, flags=re.DOTALL)


def process_book(book_id, base_path):
    filepath = f"{base_path}/editions/{book_id}/info.toon"
    print(f"\n{'=' * 60}")
    print(f"Processing: {book_id}")
    print(f"{'=' * 60}")

    content = read_info_file(filepath)
    intro_en = extract_intro(content)

    if not intro_en:
        print(f"ERROR: Could not extract intro for {book_id}")
        return

    print(f"English intro char count: {len(intro_en)}")

    # Translate to Spanish
    print("Translating to Spanish...")
    intro_es = translate_text(intro_en, "es")
    if intro_es:
        print(f"Spanish char count: {len(intro_es)}")
        content = replace_intro(content, "intro_es", intro_es)
    else:
        print("ERROR: Spanish translation failed")

    # Translate to Turkish
    print("Translating to Turkish...")
    intro_tr = translate_text(intro_en, "tr")
    if intro_tr:
        print(f"Turkish char count: {len(intro_tr)}")
        content = replace_intro(content, "intro_tr", intro_tr)
    else:
        print("ERROR: Turkish translation failed")

    # Translate to Hindi
    print("Translating to Hindi...")
    intro_hi = translate_text(intro_en, "hi")
    if intro_hi:
        print(f"Hindi char count: {len(intro_hi)}")
        content = replace_intro(content, "intro_hi", intro_hi)
    else:
        print("ERROR: Hindi translation failed")

    # Write back to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ Updated {filepath}")


def main():
    base_path = "/home/saboor/code/hadith-api-toon"
    books = ["abudawud", "aladab-almufrad", "bayhaqi", "bukhari", "bulugh-al-maram"]

    for book in books:
        process_book(book, base_path)

    print(f"\n{'=' * 60}")
    print("All books processed successfully!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
