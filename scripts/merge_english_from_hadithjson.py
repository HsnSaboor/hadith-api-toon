"""
Download English + Arabic from AhmedBaset/hadith-json and merge into editions.
Covers: ahmed, darimi, aladab_almufrad, bulugh_almaram, mishkat_almasabih, shamail_muhammadiyah
"""

import json
import os
import requests
from collections import defaultdict


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITIONS_DIR = os.path.join(BASE, "editions")
RAW_URL = (
    "https://raw.githubusercontent.com/A7med3bdulBaset/hadith-json/main/db/by_book"
)

# Map our book keys to hadith-json filenames
BOOK_MAP = {
    "musnad-ahmed": ("the_9_books/ahmed.json", "ahmed"),
    "sunan-darmi": ("the_9_books/darimi.json", "darimi"),
    "aladab-almufrad": ("other_books/aladab_almufrad.json", "aladab_almufrad"),
    "bulugh-al-maram": ("other_books/bulugh_almaram.json", "bulugh_almaram"),
    "mishkat": ("other_books/mishkat_almasabih.json", "mishkat_almasabih"),
    "shamail-tirmazi": (
        "other_books/shamail_muhammadiyah.json",
        "shamail_muhammadiyah",
    ),
}


def escape_val(value):
    if value is None or value == "":
        return ""
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def download_book(url_path):
    """Download a book JSON from hadith-json repo."""
    url = f"{RAW_URL}/{url_path}"
    print(f"  Downloading {url}...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def generate_english_edition(book_key, data):
    """Generate eng-{book} edition from hadith-json data."""
    chapters = {ch["id"]: ch for ch in data.get("chapters", [])}
    hadiths = data.get("hadiths", [])

    # Group by chapter
    by_chapter = defaultdict(list)
    for h in hadiths:
        ch_id = h.get("chapterId", 0)
        by_chapter[ch_id].append(h)

    edition_dir = os.path.join(EDITIONS_DIR, f"eng-{book_key}", "sections")
    os.makedirs(edition_dir, exist_ok=True)

    total = 0
    for ch_id in sorted(by_chapter.keys()):
        ch_hadiths = by_chapter[ch_id]
        ch_info = chapters.get(ch_id, {})
        ch_name = ch_info.get("name", ch_info.get("englishName", f"Chapter {ch_id}"))

        valid = []
        for h in ch_hadiths:
            eng = h.get("english", {})
            if isinstance(eng, dict):
                text = eng.get("text", "")
                narrator = eng.get("narrator", "")
            else:
                text = str(eng)
                narrator = ""

            if text:
                valid.append((h, text, narrator))

        if not valid:
            continue

        metadata = {
            "section_id": str(ch_id),
            "section_name": ch_name,
            "hadith_first": str(valid[0][0].get("idInBook", "")),
            "hadith_last": str(valid[-1][0].get("idInBook", "")),
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

        def get_hn(h, t, n):
            return str(h.get("idInBook", ""))

        def get_text(h, t, n):
            return t

        def get_grades(h, t, n):
            return ""

        def get_ref(h, t, n):
            return ""

        def get_intl(h, t, n):
            return str(h.get("id", ""))

        def get_narrator(h, t, n):
            return n

        def get_chapter(h, t, n):
            return ch_name

        getters = [
            get_hn,
            get_text,
            get_grades,
            get_ref,
            get_intl,
            get_narrator,
            get_chapter,
        ]

        path = os.path.join(edition_dir, f"{ch_id}.toon")
        lines = ["metadata:"]
        for k, v in metadata.items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append(f"hadiths[{len(valid)}]{{{','.join(fields)}}}:")
        for h, text, narrator in valid:
            row = [escape_val(g(h, text, narrator)) for g in getters]
            lines.append(",".join(row))

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        total += len(valid)

    print(
        f"  eng-{book_key}: {total} hadiths in {len([f for f in os.listdir(edition_dir) if f.endswith('.toon')])} sections"
    )
    return total


# === Main ===
for book_key, (url_path, json_name) in BOOK_MAP.items():
    print(f"\n=== {book_key} ===")
    try:
        data = download_book(url_path)
        count = generate_english_edition(book_key, data)
        print(f"  ✅ {count} English hadiths")
    except Exception as e:
        print(f"  ❌ Error: {e}")
