#!/usr/bin/env python3
import json
import re

# Load translations
with open("/tmp/translations_group2.json", "r", encoding="utf-8") as f:
    translations = json.load(f)


def clean_translation(text):
    """Remove the translation header and return just the result"""
    if not text:
        return ""
    # Extract just the translation result
    match = re.search(r"Translation result:\s*(.+)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# Process each book
books = ["dehlawi", "fatah-alrabani", "ibnmajah", "lulu-wal-marjan", "malik"]

for book in books:
    info_path = f"/home/saboor/code/hadith-api-toon/editions/{book}/info.toon"

    with open(info_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Get translations for this book
    es_text = clean_translation(translations[book]["es"])
    tr_text = clean_translation(translations[book]["tr"])
    hi_text = clean_translation(translations[book]["hi"])

    # Find the intro_ur line and add new translations after it
    # Look for the pattern: intro_ur: "..."
    ur_match = re.search(r'(intro_ur: ".*?"\n)', content, re.DOTALL)
    if ur_match:
        insert_pos = ur_match.end()

        # Prepare new fields
        new_fields = f"""  intro_es: "{es_text}"
  intro_tr: "{tr_text}"
  intro_hi: "{hi_text}"
"""

        # Insert after intro_ur
        new_content = content[:insert_pos] + new_fields + content[insert_pos:]

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✓ Updated {book}/info.toon")
    else:
        print(f"✗ Could not find intro_ur in {book}/info.toon")

print("\nDone!")
