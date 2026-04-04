"""
Convert chapterTranslations.json to per-book chapter_translations.toon files.

Input structure:
  {
    "bukhari": {
      "ur": { "1": "کتاب الوحی", "2": "..." },
      "ar": { "1": "...", ... },
      ...
    },
    ...
  }

Output: output/editions/{book_key}/chapter_translations.toon
  chapter_translations[lang_count]{lang,chapter_id,name}:
    ur,1,کتاب الوحی
    ur,2,...
    ar,1,...
"""

import json
import os
import sys


def escape_val(value):
    if value is None:
        return "null"
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def convert_chapter_translations(src_path: str, output_dir: str):
    with open(src_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    total_entries = 0

    for book_key in sorted(data.keys()):
        book_data = data[book_key]
        rows = []

        for lang_code in sorted(book_data.keys()):
            chapters = book_data[lang_code]
            for ch_id in sorted(chapters.keys(), key=lambda x: int(x)):
                name = chapters[ch_id]
                rows.append((lang_code, ch_id, name))

        book_dir = os.path.join(output_dir, book_key)
        os.makedirs(book_dir, exist_ok=True)
        out_path = os.path.join(book_dir, "chapter_translations.toon")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"chapter_translations[{len(rows)}]{{lang,chapter_id,name}}:\n")
            for lang, ch_id, name in rows:
                f.write(f"{lang},{ch_id},{escape_val(name)}\n")

        total_entries += len(rows)
        print(f"  {book_key}: {len(rows)} entries")

    print(
        f"\nTotal: {total_entries} chapter translation entries across {len(data)} books"
    )


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(os.path.expanduser("~"), "Downloads", "chapterTranslations.json")
    out = os.path.join(base, "editions")

    if len(sys.argv) > 1:
        src = sys.argv[1]
    if len(sys.argv) > 2:
        out = sys.argv[2]

    print(f"Source: {src}")
    print(f"Output: {out}")
    print()

    convert_chapter_translations(src, out)
