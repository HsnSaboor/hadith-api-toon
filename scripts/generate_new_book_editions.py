"""
Generate ara/urd/eng editions for the 15 new scraped books.
"""

import json
import os
import csv
import io


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPED_DIR = os.path.join(BASE, "scraped_data")
EDITIONS_DIR = os.path.join(BASE, "editions")

NEW_BOOKS = [
    "musnad-ahmed",
    "silsila-sahih",
    "mishkat",
    "fatah-alrabani",
    "bayhaqi",
    "shamail-tirmazi",
    "aladab-almufrad",
    "mustadrak",
    "sunan-darmi",
    "muajam-tabarani-saghir",
    "musannaf-ibn-abi-shaybah",
    "sahih-ibn-khuzaymah",
    "sunan-al-daraqutni",
    "bulugh-al-maram",
    "lulu-wal-marjan",
]


def escape_val(value):
    if value is None or value == "":
        return ""
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def load_scraped(book_key):
    path = os.path.join(SCRAPED_DIR, f"{book_key}_scraped.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {str(item.get("hadith_number", i)): item for i, item in enumerate(data)}
    return data


def group_by_chapter(scraped_data):
    """Group hadiths by chapter_title_arabic."""
    chapters = {}
    for h_id_str, h_data in sorted(
        scraped_data.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0
    ):
        chapter = h_data.get("chapter_title_arabic", "Unknown")
        if chapter not in chapters:
            chapters[chapter] = []
        chapters[chapter].append((h_id_str, h_data))
    return chapters


def write_section_file(path, metadata, hadiths_list, fields, field_getters):
    """Write a .toon section file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["metadata:"]
    for k, v in metadata.items():
        lines.append(f"  {k}: {v}")
    lines.append("")

    lines.append(f"hadiths[{len(hadiths_list)}]{{{','.join(fields)}}}:")
    for h_id_str, h_data in hadiths_list:
        row = [escape_val(getter(h_id_str, h_data)) for getter in field_getters]
        lines.append(",".join(row))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def generate_editions(book_key):
    """Generate ara, urd, eng editions for a book."""
    scraped = load_scraped(book_key)
    if not scraped:
        print(f"  {book_key}: no scraped data")
        return

    chapters = group_by_chapter(scraped)
    print(f"  {book_key}: {len(scraped)} hadiths in {len(chapters)} chapters")

    for edition_lang, lang_code, text_field in [
        ("ara", "Arabic", "arabic"),
        ("urd", "Urdu", "urdu"),
    ]:
        edition_dir = os.path.join(
            EDITIONS_DIR, f"{edition_lang}-{book_key}", "sections"
        )
        total_hadiths = 0

        for sec_idx, (chapter_name, hadiths) in enumerate(chapters.items(), 1):
            # Filter out hadiths without text in this language
            valid = [(h_id, h) for h_id, h in hadiths if h.get(text_field)]
            if not valid:
                continue

            metadata = {
                "section_id": str(sec_idx),
                "section_name": chapter_name,
                "hadith_first": valid[0][0],
                "hadith_last": valid[-1][0],
            }

            fields = [
                "hadithnumber",
                "text",
                "grades",
                "reference",
                "international_number",
                "narrator_chain",
                "chapter_intro",
            ]

            def get_hn(h_id, h):
                return h_id

            def get_text(h_id, h):
                return h.get(text_field, "")

            def get_grades(h_id, h):
                return ""

            def get_ref(h_id, h):
                return ""

            def get_intl(h_id, h):
                return str(h.get("international_number", ""))

            def get_narrator(h_id, h):
                return ""

            def get_chapter(h_id, h):
                return h.get("chapter_title_arabic", "")

            getters = [
                get_hn,
                get_text,
                get_grades,
                get_ref,
                get_intl,
                get_narrator,
                get_chapter,
            ]

            path = os.path.join(edition_dir, f"{sec_idx}.toon")
            write_section_file(path, metadata, valid, fields, getters)
            total_hadiths += len(valid)

        print(
            f"    {edition_lang}-{book_key}: {total_hadiths} hadiths in {len([f for f in os.listdir(edition_dir) if f.endswith('.toon')])} sections"
        )


if __name__ == "__main__":
    for book_key in NEW_BOOKS:
        generate_editions(book_key)
