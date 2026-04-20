#!/usr/bin/env python3
"""
Fix info.toon files across all editions:
  1. Remove _extract_result.json from available_languages
  2. Ensure hi and ro are listed for books that have them
  3. Ensure ar is listed for books that have Arabic sections
  4. Rebuild the root info.toon from all per-book info.toon files

Also cleans up _extract_result.json and _unmapped.toon files from translation dirs.
"""

import os
import re
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITIONS  = os.path.join(REPO_ROOT, "editions")

# Valid language codes — only these should appear in available_languages
VALID_LANG_CODES = {"ar", "bn", "en", "fr", "hi", "id", "ro", "ru", "ta", "tr", "ur"}


def get_actual_languages(edition_dir: str) -> list:
    """Scan the actual translation directories and Arabic sections to determine real languages."""
    langs = set()

    # Arabic: check if sections/ dir exists and has toon files
    ar_dir = os.path.join(edition_dir, "sections")
    if os.path.isdir(ar_dir) and any(f.endswith(".toon") for f in os.listdir(ar_dir)):
        langs.add("ar")

    # Translations
    trans_dir = os.path.join(edition_dir, "translations")
    if os.path.isdir(trans_dir):
        for lang_code in os.listdir(trans_dir):
            if lang_code not in VALID_LANG_CODES:
                continue
            sec_dir = os.path.join(trans_dir, lang_code, "sections")
            if not os.path.isdir(sec_dir):
                continue
            # Count non-empty valid section files
            toon_files = [f for f in os.listdir(sec_dir)
                          if f.endswith(".toon") and not f.startswith("_")]
            if toon_files:
                # Check at least one toon file has content
                has_content = False
                for tf in toon_files[:5]:  # sample first 5
                    path = os.path.join(sec_dir, tf)
                    with open(path, encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        has_content = True
                        break
                if has_content:
                    langs.add(lang_code)

    return sorted(langs)


def fix_per_book_info_toon(edition_id: str) -> dict:
    """Fix a single per-book info.toon. Returns info about what changed."""
    ed_dir = os.path.join(EDITIONS, edition_id)
    info_path = os.path.join(ed_dir, "info.toon")

    if not os.path.exists(info_path):
        return {"edition": edition_id, "status": "skip - no info.toon"}

    with open(info_path, encoding="utf-8") as f:
        content = f.read()

    # Get actual languages from filesystem
    actual_langs = get_actual_languages(ed_dir)
    langs_str = ",".join(actual_langs)

    # Find current value
    m = re.search(r'available_languages:\s*"([^"]*)"', content)
    if not m:
        return {"edition": edition_id, "status": "skip - no available_languages field"}

    old_val = m.group(1)
    new_val = langs_str

    if old_val == new_val:
        return {"edition": edition_id, "status": "ok", "langs": new_val}

    # Replace
    content = re.sub(
        r'available_languages:\s*"[^"]*"',
        f'available_languages: "{new_val}"',
        content
    )

    with open(info_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "edition": edition_id,
        "status": "fixed",
        "old": old_val,
        "new": new_val,
    }


def cleanup_junk_files(edition_id: str) -> list:
    """Remove _extract_result.json and _unmapped.toon files from translation dirs."""
    ed_dir = os.path.join(EDITIONS, edition_id)
    trans_dir = os.path.join(ed_dir, "translations")
    removed = []

    if not os.path.isdir(trans_dir):
        return removed

    for lang in os.listdir(trans_dir):
        lang_dir = os.path.join(trans_dir, lang)
        if not os.path.isdir(lang_dir):
            continue

        # Remove _extract_result.json in translations/{lang}/
        result_json = os.path.join(lang_dir, "_extract_result.json")
        if os.path.exists(result_json):
            os.remove(result_json)
            removed.append(result_json.replace(REPO_ROOT + "/", ""))

        # Root _extract_result.json
        root_result = os.path.join(ed_dir, "translations", "_extract_result.json")
        if os.path.exists(root_result):
            os.remove(root_result)
            removed.append(root_result.replace(REPO_ROOT + "/", ""))

        # Remove _unmapped.toon from sections
        sec_dir = os.path.join(lang_dir, "sections")
        if os.path.isdir(sec_dir):
            unmapped = os.path.join(sec_dir, "_unmapped.toon")
            if os.path.exists(unmapped):
                os.remove(unmapped)
                removed.append(unmapped.replace(REPO_ROOT + "/", ""))

    return removed


def rebuild_root_info_toon() -> None:
    """Rebuild the root info.toon from all per-book info.toon files."""
    root_info_path = os.path.join(REPO_ROOT, "info.toon")

    if not os.path.exists(root_info_path):
        print("  WARNING: root info.toon not found, skipping root rebuild")
        return

    with open(root_info_path, encoding="utf-8") as f:
        content = f.read()

    # Parse existing book rows to get names and total_hadiths
    # Format: id,"name",total_hadiths,"available_languages",...,path
    book_rows = []
    row_pattern = re.compile(r'^\s{2}(\S+),(.+)$', re.MULTILINE)

    # Split into header + books section
    books_header_match = re.search(r'books\[\d+\]\{[^}]+\}:\s*\n', content)
    if not books_header_match:
        print("  WARNING: could not find books header in root info.toon")
        return

    header_part = content[:books_header_match.end()]

    # Rebuild each book row from per-book info.toon
    new_rows = []
    for edition_id in sorted(os.listdir(EDITIONS)):
        ed_dir = os.path.join(EDITIONS, edition_id)
        if not os.path.isdir(ed_dir):
            continue

        per_book_info = os.path.join(ed_dir, "info.toon")
        if not os.path.exists(per_book_info):
            continue

        with open(per_book_info, encoding="utf-8") as f:
            pb_content = f.read()

        # Extract fields
        book_id_m = re.search(r'book_id:\s*"?([^"\n]+)"?', pb_content)
        book_name_m = re.search(r'book_name:\s*"([^"]+)"', pb_content)
        total_m = re.search(r'total_hadiths:\s*"?(\d+)"?', pb_content)
        langs_m = re.search(r'available_languages:\s*"([^"]*)"', pb_content)

        book_id    = book_id_m.group(1).strip() if book_id_m else edition_id
        book_name  = book_name_m.group(1).strip() if book_name_m else edition_id
        total_had  = total_m.group(1).strip() if total_m else "0"
        langs      = langs_m.group(1).strip() if langs_m else ""

        new_rows.append(f'  {book_id},"{book_name}",{total_had},"{langs}",editions/{edition_id}')

    # Update book count in header
    book_count = len(new_rows)
    header_part = re.sub(r'total_books:\s*\d+', f'total_books: {book_count}', header_part)
    header_part = re.sub(r'books\[\d+\]', f'books[{book_count}]', header_part)

    new_content = header_part + "\n".join(new_rows) + "\n"

    with open(root_info_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  ✅ Rebuilt root info.toon with {book_count} books")


def main():
    print("=" * 60)
    print("Fixing info.toon files + cleaning junk files")
    print("=" * 60)

    all_junk_removed = []

    for edition_id in sorted(os.listdir(EDITIONS)):
        ed_path = os.path.join(EDITIONS, edition_id)
        if not os.path.isdir(ed_path):
            continue

        # 1. Cleanup junk files
        junk = cleanup_junk_files(edition_id)
        all_junk_removed.extend(junk)

        # 2. Fix per-book info.toon
        result = fix_per_book_info_toon(edition_id)

        if result.get("status") == "fixed":
            print(f"\n  {edition_id}:")
            print(f"    OLD: {result['old']}")
            print(f"    NEW: {result['new']}")
        elif result.get("status") == "ok":
            print(f"  {edition_id}: ✅ {result['langs']}")
        else:
            print(f"  {edition_id}: {result.get('status')}")

    if all_junk_removed:
        print(f"\n🗑  Removed {len(all_junk_removed)} junk files:")
        for f in all_junk_removed:
            print(f"    {f}")

    # 3. Rebuild root info.toon
    print("\n[Rebuilding root info.toon]")
    rebuild_root_info_toon()

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
