"""
Final integration: merge English data, fix gitignore, update editions.toon
"""

import json
import os
import csv
import io


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPED_DIR = os.path.join(BASE, "scraped_data")
EDITIONS_DIR = os.path.join(BASE, "editions")

ENGLISH_BOOKS = {
    "musnad-ahmed": "musnad-ahmed",
    "aladab-almufrad": "aladab-almufrad",
    "shamail-tirmazi": "shamail-tirmazi",
    "mishkat": "mishkat",
    "bulugh-al-maram": "bulugh-al-maram",
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


def load_scraped(book_key):
    path = os.path.join(SCRAPED_DIR, f"{book_key}_scraped.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {str(item.get("hadith_number", i)): item for i, item in enumerate(data)}
    return data


def load_english(book_key):
    path = os.path.join(SCRAPED_DIR, f"{book_key}_english.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def group_by_chapter(scraped_data):
    chapters = {}
    for h_id_str, h_data in sorted(
        scraped_data.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0
    ):
        chapter = h_data.get("chapter_title_arabic", "Unknown")
        if chapter not in chapters:
            chapters[chapter] = []
        chapters[chapter].append((h_id_str, h_data))
    return chapters


def generate_english_edition(book_key):
    """Generate eng-{book} edition with English text + narrator chains."""
    scraped = load_scraped(book_key)
    english = load_english(book_key)

    if not scraped:
        print(f"  {book_key}: no scraped data")
        return

    chapters = group_by_chapter(scraped)
    edition_dir = os.path.join(EDITIONS_DIR, f"eng-{book_key}", "sections")
    total_hadiths = 0

    for sec_idx, (chapter_name, hadiths) in enumerate(chapters.items(), 1):
        valid = []
        for h_id_str, h_data in hadiths:
            # Try to find English text by hadith number
            eng_text = ""
            narrator = ""
            h_num = h_id_str
            if h_num in english:
                eng_text = english[h_num].get("english", "")
                narrator = english[h_num].get("narrator", "")

            if eng_text:
                valid.append((h_id_str, h_data, eng_text, narrator))

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

        def get_hn(h_id, h, t, n):
            return h_id

        def get_text(h_id, h, t, n):
            return t

        def get_grades(h_id, h, t, n):
            return ""

        def get_ref(h_id, h, t, n):
            return ""

        def get_intl(h_id, h, t, n):
            return str(h.get("international_number", ""))

        def get_narrator(h_id, h, t, n):
            return n

        def get_chapter(h_id, h, t, n):
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

        os.makedirs(edition_dir, exist_ok=True)
        path = os.path.join(edition_dir, f"{sec_idx}.toon")
        lines = ["metadata:"]
        for k, v in metadata.items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append(f"hadiths[{len(valid)}]{{{','.join(fields)}}}:")
        for h_id, h_data, eng_text, narrator in valid:
            row = [escape_val(g(h_id, h_data, eng_text, narrator)) for g in getters]
            lines.append(",".join(row))

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        total_hadiths += len(valid)

    print(
        f"  eng-{book_key}: {total_hadiths} hadiths in {len([f for f in os.listdir(edition_dir) if f.endswith('.toon')])} sections"
    )


def update_editions_toon_for_english():
    """Add eng-{book} entries to editions.toon."""
    path = os.path.join(BASE, "editions.toon")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    existing = set()
    for line in lines:
        line = line.strip()
        if line.startswith("editions["):
            continue
        if line and "," in line:
            existing.add(line.split(",")[0])

    new_entries = []
    for book_key in ENGLISH_BOOKS:
        edition_id = f"eng-{book_key}"
        if edition_id in existing:
            continue

        sec_dir = os.path.join(EDITIONS_DIR, edition_id, "sections")
        has_sections = (
            os.path.isdir(sec_dir)
            and any(f.endswith(".toon") for f in os.listdir(sec_dir))
            if os.path.isdir(sec_dir)
            else False
        )

        new_entries.append(
            f"{edition_id},{book_key},Unknown,English,{str(has_sections).lower()},ltr,,editions/{edition_id}"
        )

    if new_entries:
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
            f"editions.toon: added {len(new_entries)} English editions (total: {new_count})"
        )


# === Task 1: Generate English editions ===
print("=== Task 1: Generate English editions ===")
for book_key in ENGLISH_BOOKS:
    generate_english_edition(book_key)

# === Task 2: Update editions.toon ===
print("\n=== Task 2: Update editions.toon ===")
update_editions_toon_for_english()

# === Task 3: Fix .gitignore ===
print("\n=== Task 3: Fix .gitignore ===")
gitignore_path = os.path.join(BASE, ".gitignore")
with open(gitignore_path, "a") as f:
    f.write("\n# Scraped data and logs\nscraped_data/\n*.log\n.venv/\n__pycache__/\n")
print("  Updated .gitignore")

# Remove scraped_data from git index
os.system(f"cd {BASE} && git rm -r --cached scraped_data/ 2>/dev/null")
os.system(f"cd {BASE} && git rm --cached '*.log' 2>/dev/null")
os.system(f"cd {BASE} && git rm --cached .venv/ 2>/dev/null")
print("  Removed scraped_data and logs from git index")
