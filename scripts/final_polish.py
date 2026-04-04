"""
Final polish tasks:
1. Update chapter_translations.toon with chapter titles from 15 new books
2. Fix 'Unknown' author names in editions.toon
3. Add pre-commit validation for empty section_name fields
"""

import json
import os
import csv
import io


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPED_DIR = os.path.join(BASE, "scraped_data")
EDITIONS_DIR = os.path.join(BASE, "editions")

# Historical authors for new books
BOOK_AUTHORS = {
    "musnad-ahmed": "Imam Ahmad bin Hanbal",
    "silsila-sahih": "Al-Albani",
    "mishkat": "Al-Baghawi / Al-Tabrizi",
    "fatah-alrabani": "Abdul-Qadir al-Jilani",
    "bayhaqi": "Imam Al-Bayhaqi",
    "shamail-tirmazi": "Imam At-Tirmidhi",
    "aladab-almufrad": "Imam Al-Bukhari",
    "mustadrak": "Imam Al-Hakim",
    "sunan-darmi": "Imam Ad-Darimi",
    "muajam-tabarani-saghir": "Imam At-Tabarani",
    "musannaf-ibn-abi-shaybah": "Ibn Abi Shaybah",
    "sahih-ibn-khuzaymah": "Ibn Khuzaymah",
    "sunan-al-daraqutni": "Imam Ad-Daraqutni",
    "bulugh-al-maram": "Ibn Hajar Al-Asqalani",
    "lulu-wal-marjan": "Muhammad Fuad Abdul Baqi",
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


def parse_csv_line(line):
    reader = csv.reader(io.StringIO(line))
    try:
        return next(reader)
    except StopIteration:
        return []


# === Task 1: Update chapter_translations.toon ===
def update_chapter_translations():
    print("=== Task 1: Update chapter_translations.toon ===")

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

    for book_key in NEW_BOOKS:
        # Collect chapter titles from scraped data
        scraped_path = os.path.join(SCRAPED_DIR, f"{book_key}_scraped.json")
        if not os.path.exists(scraped_path):
            continue

        with open(scraped_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chapters = {}  # chapter_title -> chapter_id
        for h_id_str, h_data in sorted(
            data.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0
        ):
            title = h_data.get("chapter_title_arabic", "")
            if title and title not in chapters:
                chapters[title] = len(chapters) + 1

        if not chapters:
            print(f"  {book_key}: no chapters found")
            continue

        # Write chapter_translations.toon
        out_path = os.path.join(EDITIONS_DIR, book_key, "chapter_translations.toon")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        rows = []
        for title, ch_id in sorted(chapters.items(), key=lambda x: x[1]):
            rows.append(("ar", str(ch_id), title))

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"chapter_translations[{len(rows)}]{{lang,chapter_id,name}}:\n")
            for lang, ch_id, name in rows:
                f.write(f"{lang},{ch_id},{escape_val(name)}\n")

        print(f"  {book_key}: {len(rows)} chapters")


# === Task 2: Fix author names in editions.toon ===
def fix_authors():
    print("\n=== Task 2: Fix author names in editions.toon ===")

    path = os.path.join(BASE, "editions.toon")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    fixed = 0
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("editions[") or not stripped or "," not in stripped:
            new_lines.append(line)
            continue

        parts = parse_csv_line(stripped)
        if len(parts) < 8:
            new_lines.append(line)
            continue

        edition_id = parts[0]
        book_key = parts[1]
        author = parts[2]

        if author == "Unknown" and book_key in BOOK_AUTHORS:
            parts[2] = BOOK_AUTHORS[book_key]
            new_lines.append(",".join(parts) + "\n")
            fixed += 1
        else:
            new_lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"  Fixed {fixed} author entries")


# === Task 3: Pre-commit validation ===
def validate_no_empty_metadata():
    print("\n=== Task 3: Validate no empty section_name fields ===")

    errors = 0
    warnings = 0
    total_files = 0

    for edition in sorted(os.listdir(EDITIONS_DIR)):
        sec_dir = os.path.join(EDITIONS_DIR, edition, "sections")
        if not os.path.isdir(sec_dir):
            continue

        for fname in sorted(os.listdir(sec_dir)):
            if not fname.endswith(".toon"):
                continue

            total_files += 1
            fpath = os.path.join(sec_dir, fname)

            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for empty section_name
            if "section_name: \n" in content or "section_name:\n" in content:
                print(f"  WARNING: {edition}/{fname} has empty section_name")
                warnings += 1

            # Check for empty hadith count
            if "hadiths[0]" in content:
                print(f"  ERROR: {edition}/{fname} has 0 hadiths")
                errors += 1

    print(f"  Checked {total_files} files: {errors} errors, {warnings} warnings")
    return errors == 0


if __name__ == "__main__":
    update_chapter_translations()
    fix_authors()
    ok = validate_no_empty_metadata()

    if ok:
        print("\n✅ All validation checks passed")
    else:
        print("\n❌ Validation failed - fix errors before committing")
