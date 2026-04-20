#!/usr/bin/env python3
"""
Import missing language translations from hadith-new/editions/ JSON files
into the toon format at editions/{book}/translations/{lang}/sections/*.toon

Usage:
    python3 scripts/import_hadith_new_langs.py [--dry-run]

What it does:
  1. For each missing (book, lang) pair, reads the source JSON
  2. Splits hadiths by section using existing sections/*.toon boundaries
  3. Writes JSONL .toon files in translations/{lang}/sections/
  4. Writes metadata.toon for the language
  5. Updates editions/{book}/info.toon available_languages
  6. Updates root info.toon available_languages column
"""

import json
import os
import sys
import re

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HADITH_NEW_DIR = os.path.join(BASE_DIR, "hadith-new", "editions")
EDITIONS_DIR = os.path.join(BASE_DIR, "editions")
ROOT_INFO = os.path.join(BASE_DIR, "info.toon")

# Source 3-letter prefix → toon 2-letter lang folder
LANG_MAP = {
    "tur": "tr",
    "tam": "ta",
    "rus": "ru",
    "ben": "bn",
    "eng": "en",
    "fra": "fr",
    "ind": "id",
    "urd": "ur",
}

LANG_NAMES = {
    "tr": "Turkish",
    "ta": "Tamil",
    "ru": "Russian",
    "bn": "Bengali",
    "en": "English",
    "fr": "French",
    "id": "Indonesian",
    "ur": "Urdu",
    "ar": "Arabic",
}

LANG_SCRIPTS = {
    "tr": "Latin",
    "ta": "Tamil",
    "ru": "Cyrillic",
    "bn": "Bengali",
    "en": "Latin",
    "fr": "Latin",
    "id": "Latin",
    "ur": "Arabic",
    "ar": "Arabic",
}

# All (book_id_in_toon, source_lang_prefix) pairs to import
# Only pairs that are missing from existing editions
MISSING_PAIRS = [
    ("abudawud",  "tur"),
    ("bukhari",   "tam"),
    ("bukhari",   "tur"),
    ("ibnmajah",  "tur"),
    ("malik",     "tur"),
    ("muslim",    "rus"),
    ("muslim",    "tam"),
    ("muslim",    "tur"),
    ("nasai",     "tur"),
    ("nawawi",    "tur"),
    ("tirmidhi",  "tur"),
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_section_boundaries(book: str) -> dict:
    """
    Read existing sections/*.toon for a book and return {sec_id: (first, last)}
    by scanning hadithnumber from the first column of each data row.
    """
    sec_dir = os.path.join(EDITIONS_DIR, book, "sections")
    boundaries = {}
    for fname in os.listdir(sec_dir):
        if not fname.endswith(".toon"):
            continue
        sec_id = fname.replace(".toon", "")
        path = os.path.join(sec_dir, fname)
        nums = []
        with open(path, encoding="utf-8") as f:
            in_data = False
            for line in f:
                stripped = line.rstrip("\r\n")
                if stripped.startswith("hadiths["):
                    in_data = True
                    continue
                if not in_data:
                    continue
                if not stripped:
                    continue
                # First field is hadithnumber (always bare integer)
                try:
                    hn = int(stripped.split(",")[0])
                    nums.append(hn)
                except (ValueError, IndexError):
                    pass
        if nums:
            boundaries[sec_id] = (min(nums), max(nums))
    return boundaries


def load_source_json(book: str, lang_prefix: str) -> dict:
    """Load hadith-new/editions/{lang_prefix}-{book}.json"""
    path = os.path.join(HADITH_NEW_DIR, f"{lang_prefix}-{book}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Source not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_hadith_map(hadiths: list) -> dict:
    """Build {hadithnumber: text} index from hadiths list."""
    return {h["hadithnumber"]: h["text"] for h in hadiths}


def write_translation_sections(
    book: str,
    lang: str,
    hadith_map: dict,
    boundaries: dict,
    dry_run: bool,
) -> tuple:
    """
    Write JSONL .toon files for each section.
    Returns (sections_written, hadiths_written, sections_skipped).
    """
    out_base = os.path.join(EDITIONS_DIR, book, "translations", lang, "sections")
    if not dry_run:
        os.makedirs(out_base, exist_ok=True)

    written_sections = 0
    written_hadiths = 0
    skipped_sections = 0
    missing_hadiths = 0

    for sec_id, (first, last) in sorted(boundaries.items(), key=lambda x: int(x[0])):
        out_path = os.path.join(out_base, f"{sec_id}.toon")

        # Collect hadiths in this section's range (inclusive)
        rows = []
        for hn in range(first, last + 1):
            text = hadith_map.get(hn)
            if text is not None:
                rows.append({"hadithnumber": str(hn), "text": text})
            else:
                missing_hadiths += 1

        if not rows:
            # Section has no translations (e.g. section 0 in some books)
            skipped_sections += 1
            continue

        if dry_run:
            written_sections += 1
            written_hadiths += len(rows)
            continue

        lines = [json.dumps(row, ensure_ascii=False) for row in rows]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        written_sections += 1
        written_hadiths += len(rows)

    if missing_hadiths:
        print(f"      ⚠ {missing_hadiths} hadith numbers had no translation text")

    return written_sections, written_hadiths, skipped_sections


def write_metadata_toon(book: str, lang: str, total_hadiths: int, dry_run: bool):
    """Write translations/{lang}/metadata.toon"""
    out_path = os.path.join(EDITIONS_DIR, book, "translations", lang, "metadata.toon")
    if not dry_run:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

    content = (
        f"metadata:\n"
        f"  language: {lang}\n"
        f"  language_name: {LANG_NAMES.get(lang, lang)}\n"
        f"  script: {LANG_SCRIPTS.get(lang, 'Latin')}\n"
        f"  total_hadiths: {total_hadiths}\n"
        f'  source: "hadith-new"\n'
    )

    if dry_run:
        print(f"      [dry] would write {out_path}")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)


def update_book_info_toon(book: str, lang: str, dry_run: bool):
    """
    Update editions/{book}/info.toon: add lang to available_languages metadata line.
    """
    info_path = os.path.join(EDITIONS_DIR, book, "info.toon")
    if not os.path.exists(info_path):
        print(f"      ⚠ {info_path} not found, skipping update")
        return

    with open(info_path, encoding="utf-8") as f:
        content = f.read()

    # Match: available_languages: "bn,fr,id,ru,ur,en"
    pattern = r'(  available_languages:\s*")([^"]*?)(")'

    def add_lang(m):
        langs = [l.strip() for l in m.group(2).split(",") if l.strip()]
        if lang not in langs:
            langs.append(lang)
            langs.sort()
        return m.group(1) + ",".join(langs) + m.group(3)

    new_content, count = re.subn(pattern, add_lang, content)

    if count == 0:
        print(f"      ⚠ Could not find available_languages in {info_path}")
        return

    if dry_run:
        # Extract new value for display
        m = re.search(pattern, new_content)
        if m:
            print(f"      [dry] would set available_languages: \"{m.group(2)}\"")
    else:
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(new_content)


def update_root_info_toon(book: str, lang: str, dry_run: bool):
    """
    Update root info.toon: update available_languages column in the book's row.
    Row format (CSV): id,name,total_hadiths,available_languages,path
    """
    if not os.path.exists(ROOT_INFO):
        print(f"      ⚠ Root {ROOT_INFO} not found, skipping")
        return

    with open(ROOT_INFO, encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    new_lines = []

    for line in lines:
        # Only process data rows (not header/metadata lines)
        stripped = line.rstrip("\r\n")
        # Data rows start with book id (no spaces, no colon)
        if stripped.startswith("  " + book + ",") or stripped.startswith(book + ","):
            # Parse: id,"name",total,langs,path
            # Use a careful split: first field is id
            prefix = "  " if line.startswith("  ") else ""
            inner = stripped.lstrip()
            # Split on comma but respect quoted fields
            parts = []
            current = ""
            in_quotes = False
            for ch in inner:
                if ch == '"':
                    in_quotes = not in_quotes
                    current += ch
                elif ch == "," and not in_quotes:
                    parts.append(current)
                    current = ""
                else:
                    current += ch
            parts.append(current)

            if len(parts) >= 4:
                langs_field = parts[3]
                langs = [l.strip() for l in langs_field.split(",") if l.strip()]
                if lang not in langs:
                    langs.append(lang)
                    langs.sort()
                parts[3] = ",".join(langs)
                new_row = prefix + ",".join(parts)
                new_lines.append(new_row + "\n")
                updated = True
                continue

        new_lines.append(line)

    if not updated:
        print(f"      ⚠ Book '{book}' not found in root info.toon")
        return

    if dry_run:
        # Find the updated line for display
        for l in new_lines:
            if l.strip().startswith(book + ","):
                print(f"      [dry] root info.toon row: {l.strip()[:80]}...")
                break
    else:
        with open(ROOT_INFO, "w", encoding="utf-8") as f:
            f.writelines(new_lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN MODE (no files written) ===\n")

    total_sections = 0
    total_hadiths = 0
    errors = []

    for book, lang_prefix in MISSING_PAIRS:
        lang = LANG_MAP[lang_prefix]
        print(f"▶ {book} / {lang_prefix} → {lang}")

        # Skip if already exists
        trans_dir = os.path.join(EDITIONS_DIR, book, "translations", lang, "sections")
        if os.path.isdir(trans_dir) and os.listdir(trans_dir):
            print(f"  ✓ Already exists: {trans_dir} — skipping\n")
            continue

        try:
            # Load source JSON
            print(f"  Loading hadith-new/editions/{lang_prefix}-{book}.json ...")
            data = load_source_json(book, lang_prefix)
            hadiths = data["hadiths"]
            hadith_map = build_hadith_map(hadiths)
            print(f"  Loaded {len(hadiths)} hadiths")

            # Get section boundaries from existing toon sections
            print(f"  Reading section boundaries from editions/{book}/sections/ ...")
            boundaries = get_section_boundaries(book)
            print(f"  Found {len(boundaries)} sections")

            # Write translation section files
            s_written, h_written, s_skipped = write_translation_sections(
                book, lang, hadith_map, boundaries, dry_run
            )
            print(f"  Wrote {s_written} section files ({h_written} hadiths), skipped {s_skipped} empty sections")

            # Write metadata.toon
            write_metadata_toon(book, lang, len(hadiths), dry_run)
            print(f"  Wrote metadata.toon (total_hadiths={len(hadiths)})")

            # Update book info.toon
            update_book_info_toon(book, lang, dry_run)
            print(f"  Updated editions/{book}/info.toon")

            # Update root info.toon
            update_root_info_toon(book, lang, dry_run)
            print(f"  Updated root info.toon")

            total_sections += s_written
            total_hadiths += h_written

        except FileNotFoundError as e:
            msg = f"  ✗ SKIP: {e}"
            print(msg)
            errors.append(msg)
        except Exception as e:
            msg = f"  ✗ ERROR: {e}"
            print(msg)
            errors.append(f"{book}/{lang_prefix}: {e}")

        print()

    print("=" * 60)
    print(f"Done. Total: {total_sections} section files, {total_hadiths} hadiths written")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
