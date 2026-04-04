"""
Update info.toon and editions.toon with the 15 new books.
"""

import os
import json


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITIONS_DIR = os.path.join(BASE, "editions")

NEW_BOOKS = {
    "musnad-ahmed": {"name": "Musnad Ahmed", "total_hadiths": 329},
    "silsila-sahih": {"name": "Silsila Sahiha", "total_hadiths": 52},
    "mishkat": {"name": "Mishkat al-Masabih", "total_hadiths": 494},
    "fatah-alrabani": {"name": "Fatah Al-Rabani", "total_hadiths": 193},
    "bayhaqi": {"name": "Sunan Al Kubra Bayhaqi", "total_hadiths": 125},
    "shamail-tirmazi": {"name": "Shamail-e-Tirmazi", "total_hadiths": 147},
    "aladab-almufrad": {"name": "Al-Adab Al-Mufrad", "total_hadiths": 49},
    "mustadrak": {"name": "Al Mustadrak", "total_hadiths": 668},
    "sunan-darmi": {"name": "Sunan Darmi", "total_hadiths": 245},
    "muajam-tabarani-saghir": {"name": "Muajam Saghir Tabarani", "total_hadiths": 26},
    "musannaf-ibn-abi-shaybah": {
        "name": "Musannaf Ibn Abi Shaybah",
        "total_hadiths": 264,
    },
    "sahih-ibn-khuzaymah": {"name": "Sahih Ibn Khuzaymah", "total_hadiths": 50},
    "sunan-al-daraqutni": {"name": "Sunan al-Daraqutni", "total_hadiths": 219},
    "bulugh-al-maram": {"name": "Bulugh al-Maram", "total_hadiths": 196},
    "lulu-wal-marjan": {"name": "Al-Lu'lu wal-Marjan", "total_hadiths": 47},
}


def count_sections_and_hadiths(book_key):
    """Count sections and hadiths for a book's editions."""
    sections = {}
    for edition in os.listdir(EDITIONS_DIR):
        if not edition.endswith(f"-{book_key}"):
            continue
        sec_dir = os.path.join(EDITIONS_DIR, edition, "sections")
        if not os.path.isdir(sec_dir):
            continue
        for fname in sorted(
            os.listdir(sec_dir),
            key=lambda x: (
                int(x.replace(".toon", "").split(".")[0])
                if x.replace(".toon", "").split(".")[0].isdigit()
                else 0
            ),
        ):
            if not fname.endswith(".toon"):
                continue
            sec_id = fname.replace(".toon", "")
            # Count hadiths
            hadith_count = 0
            with open(os.path.join(sec_dir, fname), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("hadiths[") and "{" in line:
                        hadith_count = int(line.split("[")[1].split("]")[0])
                        break
            if sec_id not in sections:
                sections[sec_id] = {
                    "name": "",
                    "hadith_first": "",
                    "hadith_last": "",
                    "count": 0,
                }
            sections[sec_id]["count"] = max(sections[sec_id]["count"], hadith_count)
            # Read metadata
            with open(os.path.join(sec_dir, fname), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("section_name:"):
                        sections[sec_id]["name"] = (
                            line.split(":", 1)[1].strip().strip('"')
                        )
                    elif line.startswith("hadith_first:"):
                        sections[sec_id]["hadith_first"] = line.split(":", 1)[1].strip()
                    elif line.startswith("hadith_last:"):
                        sections[sec_id]["hadith_last"] = line.split(":", 1)[1].strip()
    return sections


def update_editions_toon():
    """Add new editions to editions.toon."""
    path = os.path.join(BASE, "editions.toon")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse existing
    existing = set()
    for line in lines:
        line = line.strip()
        if line.startswith("editions["):
            continue
        if line and "," in line:
            existing.add(line.split(",")[0])

    # Find new editions
    new_entries = []
    for edition in sorted(os.listdir(EDITIONS_DIR)):
        if edition in existing:
            continue
        # Check if it's a new book
        book_key = None
        for bk in NEW_BOOKS:
            if edition.endswith(f"-{bk}"):
                book_key = bk
                break
        if not book_key:
            continue

        sec_dir = os.path.join(EDITIONS_DIR, edition, "sections")
        has_sections = os.path.isdir(sec_dir) and any(
            f.endswith(".toon") for f in os.listdir(sec_dir)
        )

        # Determine language and direction
        lang_prefix = edition.split("-")[0]
        lang_map = {"ara": "Arabic", "urd": "Urdu", "eng": "English"}
        dir_map = {"ara": "rtl", "urd": "rtl", "eng": "ltr"}
        lang = lang_map.get(lang_prefix, "Unknown")
        direction = dir_map.get(lang_prefix, "ltr")

        new_entries.append(
            f"{edition},{book_key},Unknown,{lang},{str(has_sections).lower()},{direction},,editions/{edition}"
        )

    if new_entries:
        # Find the header line and update count
        for i, line in enumerate(lines):
            if line.strip().startswith("editions[") and line.strip().endswith(":"):
                old_count = int(line.strip().split("[")[1].split("]")[0])
                new_count = old_count + len(new_entries)
                lines[i] = line.replace(f"[{old_count}]", f"[{new_count}]")
                break

        lines.extend(e + "\n" for e in new_entries)

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(
            f"editions.toon: added {len(new_entries)} new editions (total: {old_count + len(new_entries)})"
        )


def update_info_toon():
    """Add new books to info.toon."""
    path = os.path.join(BASE, "info.toon")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Add new books to books section
    new_books_lines = []
    for book_key, info in NEW_BOOKS.items():
        new_books_lines.append(f"{book_key},{info['name']},{info['total_hadiths']}")

    # Find the books section and update count
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("books[") and line.strip().endswith(":"):
            old_count = int(line.strip().split("[")[1].split("]")[0])
            new_count = old_count + len(NEW_BOOKS)
            lines[i] = line.replace(f"[{old_count}]", f"[{new_count}]")
            # Insert new books after existing ones (before empty line or next section)
            insert_at = i + 1
            while (
                insert_at < len(lines)
                and lines[insert_at].strip()
                and not lines[insert_at].startswith("sections_")
            ):
                insert_at += 1
            for j, nb_line in enumerate(new_books_lines):
                lines.insert(insert_at + j, nb_line)
            break

    # Add sections for each new book
    for book_key, info in NEW_BOOKS.items():
        sections = count_sections_and_hadiths(book_key)
        if not sections:
            continue

        # Find the last sections_ entry for this book (or add after books section)
        sections_header = f"sections_{book_key}[{len(sections)}]{{id,name,hadith_first,hadith_last,arabic_first,arabic_last}}:"

        # Find insertion point (after the last sections_ line or at end)
        insert_at = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith(f"sections_{book_key}"):
                # Already exists, skip
                insert_at = -1
                break
            if line.strip().startswith("sections_"):
                insert_at = i + 1

        if insert_at > 0:
            lines.insert(insert_at, "")
            lines.insert(insert_at + 1, sections_header)
            for sec_id in sorted(
                sections.keys(), key=lambda x: int(x) if x.isdigit() else float(x)
            ):
                sec = sections[sec_id]
                lines.insert(
                    insert_at + 2,
                    f"{sec_id},{sec['name']},{sec['hadith_first']},{sec['hadith_last']},,",
                )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"info.toon: added {len(NEW_BOOKS)} new books")


if __name__ == "__main__":
    update_editions_toon()
    update_info_toon()
