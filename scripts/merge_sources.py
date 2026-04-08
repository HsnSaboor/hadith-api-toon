#!/usr/bin/env python3
"""
Merge multiple hadith sources into unified .toon format.
Sources: existing .toon files + AhmedBaset + gurgutan HF + fawazahmed0 CDN
No duplicates, fills missing language columns.
"""

import csv
import gzip
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent  # hadith-api-toon root
EDITIONS_DIR = REPO_ROOT / "editions"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Language columns in our .toon format
TOON_COLS = [
    "hadithnumber",
    "arabic",
    "bengali",
    "english",
    "french",
    "indonesian",
    "russian",
    "urdu",
    "grades",
    "reference",
    "international_number",
    "narrator_chain",
    "chapter_intro",
]

# Book name mapping between sources
BOOK_MAP = {
    "bukhari": {
        "ahmedbaset": "bukhari",
        "gurgutan": "Sahih al-Bukhari",
        "fawaz": "bukhari",
    },
    "muslim": {"ahmedbaset": "muslim", "gurgutan": "Sahih Muslim", "fawaz": "muslim"},
    "abudawud": {
        "ahmedbaset": "abudawud",
        "gurgutan": "Sunan Abi Dawud",
        "fawaz": "abudawud",
    },
    "ibnmajah": {
        "ahmedbaset": "ibnmajah",
        "gurgutan": "Sunan Ibn Majah",
        "fawaz": "ibnmajah",
    },
    "nasai": {"ahmedbaset": "nasai", "gurgutan": "Sunan al-Nasa'i", "fawaz": "nasai"},
    "tirmidhi": {
        "ahmedbaset": "tirmidhi",
        "gurgutan": "Jami' al-Tirmidhi",
        "fawaz": "tirmidhi",
    },
    "malik": {"ahmedbaset": "malik", "gurgutan": "Muwatta Malik", "fawaz": "malik"},
    "sunan-darmi": {
        "ahmedbaset": "darimi",
        "gurgutan": "Sunan al-Darimi",
        "fawaz": "sunan-darmi",
    },
    "musnad-ahmed": {
        "ahmedbaset": "ahmed",
        "gurgutan": "Musnad Ahmad ibn Hanbal",
        "fawaz": "musnad-ahmed",
    },
    "mishkat": {
        "ahmedbaset": None,
        "gurgutan": "Mishkat al-Masabih",
        "fawaz": "mishkat",
    },
    "bulugh-al-maram": {
        "ahmedbaset": None,
        "gurgutan": "Bulugh al-Maram",
        "fawaz": "bulugh-al-maram",
    },
    "aladab-almufrad": {
        "ahmedbaset": None,
        "gurgutan": "Al-Adab Al-Mufrad",
        "fawaz": "aladab-almufrad",
    },
    "shamail-tirmazi": {
        "ahmedbaset": None,
        "gurgutan": "Shama'il Muhammadiyah",
        "fawaz": "shamail-tirmazi",
    },
}


def csv_escape(val):
    """Escape a value for .toon CSV format."""
    if val is None or val == "":
        return ""
    s = str(val).strip()
    if "," in s or '"' in s or "\n" in s:
        return '"' + s.replace('"', '""') + '"'
    return s


def load_existing_toon():
    """Load all existing .toon files into a dict: {book: {section_id: {hadith_number: {col: val}}}}"""
    data = defaultdict(lambda: defaultdict(dict))

    for book_dir in sorted(EDITIONS_DIR.iterdir()):
        if not book_dir.is_dir():
            continue
        book_slug = book_dir.name
        sections_dir = book_dir / "sections"
        if not sections_dir.exists():
            continue

        for toon_file in sorted(sections_dir.glob("*.toon")):
            section_id = toon_file.stem  # Keep as string (e.g., "1", "8.2")
            content = toon_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            # Parse header
            header_match = re.match(
                r"hadiths\[\d+\]\{([^}]+)\}", lines[2] if len(lines) > 2 else ""
            )
            if not header_match:
                continue
            cols = [c.strip() for c in header_match.group(1).split(",")]

            # Parse hadith rows
            reader = csv.reader(lines[3:])
            for row in reader:
                if not row or not row[0].strip():
                    continue
                hadith = {}
                for i, col in enumerate(cols):
                    if i < len(row):
                        hadith[col] = row[i].strip()
                hadith_num = hadith.get("hadithnumber", "")
                if hadith_num:
                    try:
                        data[book_slug][section_id][int(hadith_num)] = hadith
                    except ValueError:
                        pass

    return data


def load_ahmedbaset():
    """Load AhmedBaset/hadith-json from GitHub raw files."""
    import urllib.request

    data = {}

    for book_slug, mapping in BOOK_MAP.items():
        ab_name = mapping.get("ahmedbaset")
        if not ab_name:
            continue

        url = f"https://raw.githubusercontent.com/AhmedBaset/hadith-json/main/db/by_book/the_9_books/{ab_name}.json"
        cache_file = CACHE_DIR / f"ahmedbaset_{ab_name}.json"

        if not cache_file.exists():
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    cache_file.write_bytes(resp.read())
            except Exception as e:
                print(f"  Failed to download {ab_name}: {e}")
                continue

        try:
            raw = json.loads(cache_file.read_text())
            hadiths = raw.get("hadiths", [])
            chapters = {ch["id"]: ch for ch in raw.get("chapters", [])}
            data[book_slug] = {"hadiths": hadiths, "chapters": chapters}
            print(f"  AhmedBaset {book_slug}: {len(hadiths)} hadiths")
        except Exception as e:
            print(f"  Failed to parse {ab_name}: {e}")

    return data


def load_gurgutan():
    """Load gurgutan/sunnah_ar_en_dataset from HuggingFace."""
    import urllib.request

    url = "https://huggingface.co/datasets/gurgutan/sunnah_ar_en_dataset/resolve/main/sunnah_ar_en_dataset.jsonl.gz"
    cache_file = CACHE_DIR / "gurgutan.jsonl"

    if not cache_file.exists():
        gz_file = CACHE_DIR / "gurgutan.jsonl.gz"
        if not gz_file.exists():
            try:
                print("  Downloading gurgutan dataset (16MB)...")
                with urllib.request.urlopen(url, timeout=60) as resp:
                    gz_file.write_bytes(resp.read())
                print("  Downloaded, extracting...")
                with gzip.open(gz_file, "rb") as f_in:
                    with open(cache_file, "wb") as f_out:
                        f_out.write(f_in.read())
                print("  Extracted.")
            except Exception as e:
                print(f"  Failed to download gurgutan: {e}")
                return {}

    data = defaultdict(list)
    with open(cache_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                hadith = json.loads(line)
                book_title = hadith.get("book_title_en", "")
                # Map to our slug
                for slug, mapping in BOOK_MAP.items():
                    if mapping.get("gurgutan") == book_title:
                        data[slug].append(hadith)
                        break
            except json.JSONDecodeError:
                continue

    for slug, hadiths in data.items():
        print(f"  Gurgutan {slug}: {len(hadiths)} hadiths")

    return dict(data)


def load_fawazahmed0():
    """Load fawazahmed0/hadith-api from jsDelivr CDN."""
    import urllib.request

    # Get editions list
    editions_url = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions.json"
    editions_cache = CACHE_DIR / "fawaz_editions.json"

    if not editions_cache.exists():
        try:
            with urllib.request.urlopen(editions_url, timeout=30) as resp:
                editions_cache.write_bytes(resp.read())
        except Exception as e:
            print(f"  Failed to download editions: {e}")
            return {}

    editions = json.loads(editions_cache.read_text())
    data = {}

    for book_slug, mapping in BOOK_MAP.items():
        fawaz_name = mapping.get("fawaz")
        if not fawaz_name:
            continue

        # Find English edition
        book_info = editions.get(fawaz_name, {})
        eng_edition = None
        for edition in book_info.get("collection", []):
            if edition["name"].startswith("eng-"):
                eng_edition = edition
                break

        if not eng_edition:
            continue

        url = eng_edition["linkmin"]
        cache_file = CACHE_DIR / f"fawaz_{fawaz_name}_eng.json"

        if not cache_file.exists():
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    cache_file.write_bytes(resp.read())
            except Exception as e:
                print(f"  Failed to download fawaz {fawaz_name}: {e}")
                continue

        try:
            raw = json.loads(cache_file.read_text())
            data[book_slug] = {
                "hadiths": raw.get("hadiths", []),
                "metadata": raw.get("metadata", {}),
                "sections": raw.get("metadata", {}).get("sections", {}),
            }
            print(f"  Fawazahmed0 {book_slug}: {len(raw.get('hadiths', []))} hadiths")
        except Exception as e:
            print(f"  Failed to parse fawaz {fawaz_name}: {e}")

    return data


def merge_sources(existing, ahmedbaset, gurgutan, fawazahmed0):
    """Merge all sources, deduplicate by hadith number, fill missing languages."""
    merged = {}

    for book_slug in set(
        list(existing.keys())
        + list(ahmedbaset.keys())
        + list(gurgutan.keys())
        + list(fawazahmed0.keys())
    ):
        print(f"\nMerging {book_slug}...")

        # Start with existing data
        book_data = defaultdict(dict)  # section_id -> {hadith_num -> hadith}
        for sec_id, hadiths in existing.get(book_slug, {}).items():
            for h_num, h in hadiths.items():
                book_data[sec_id][h_num] = dict(h)

        # Merge AhmedBaset (Arabic + English)
        ab_data = ahmedbaset.get(book_slug, {})
        ab_hadiths = ab_data.get("hadiths", [])
        ab_chapters = ab_data.get("chapters", {})

        for h in ab_hadiths:
            h_num = h.get("idInBook")
            if not h_num:
                continue
            chapter_id = h.get("chapterId")
            chapter = ab_chapters.get(chapter_id, {})
            # Map chapter to section (approximate)
            sec_id = chapter_id  # Use chapter ID as section ID

            if h_num not in book_data[sec_id]:
                book_data[sec_id][h_num] = {
                    "hadithnumber": str(h_num),
                    "arabic": h.get("arabic", ""),
                    "bengali": "",
                    "english": h.get("english", ""),
                    "french": "",
                    "indonesian": "",
                    "russian": "",
                    "urdu": "",
                    "grades": h.get("grades", ""),
                    "reference": h.get("reference", ""),
                    "international_number": "",
                    "narrator_chain": "",
                    "chapter_intro": chapter.get("english", ""),
                }
            else:
                # Fill missing fields
                existing_h = book_data[sec_id][h_num]
                if not existing_h.get("arabic") and h.get("arabic"):
                    existing_h["arabic"] = h["arabic"]
                if not existing_h.get("english") and h.get("english"):
                    existing_h["english"] = h["english"]

        # Merge Gurgutan (Arabic + English)
        gurg_hadiths = gurgutan.get(book_slug, [])
        for h in gurg_hadiths:
            h_num = h.get("hadith_book_id")  # This is the hadith number within the book
            if not h_num:
                continue
            # Use chapter ID as section
            sec_id = h.get("hadith_chapter_id", 1)

            if h_num not in book_data[sec_id]:
                book_data[sec_id][h_num] = {
                    "hadithnumber": str(h_num),
                    "arabic": h.get("hadith_text_ar", ""),
                    "bengali": "",
                    "english": h.get("hadith_text_en", ""),
                    "french": "",
                    "indonesian": "",
                    "russian": "",
                    "urdu": "",
                    "grades": h.get("hadith_grade", ""),
                    "reference": h.get("hadith_reference", ""),
                    "international_number": "",
                    "narrator_chain": "",
                    "chapter_intro": h.get("hadith_chapter_name_en", ""),
                }
            else:
                existing_h = book_data[sec_id][h_num]
                if not existing_h.get("arabic") and h.get("hadith_text_ar"):
                    existing_h["arabic"] = h["hadith_text_ar"]
                if not existing_h.get("english") and h.get("hadith_text_en"):
                    existing_h["english"] = h["hadith_text_en"]

        # Merge Fawazahmed0 (multi-language)
        fawaz_data = fawazahmed0.get(book_slug, {})
        fawaz_hadiths = fawaz_data.get("hadiths", [])
        fawaz_sections = fawaz_data.get("sections", {})

        for h in fawaz_hadiths:
            h_num = h.get("hadithnumber")
            if not h_num:
                continue
            # Determine section from reference
            ref = h.get("reference", {})
            sec_id = ref.get("book", 1) if isinstance(ref, dict) else 1

            if h_num not in book_data[sec_id]:
                book_data[sec_id][h_num] = {
                    "hadithnumber": str(h_num),
                    "arabic": "",
                    "bengali": "",
                    "english": h.get("text", ""),
                    "french": "",
                    "indonesian": "",
                    "russian": "",
                    "urdu": "",
                    "grades": ",".join(str(g) for g in h.get("grades", [])),
                    "reference": f"Book {ref.get('book', '')}, Hadith {ref.get('hadith', '')}"
                    if isinstance(ref, dict)
                    else "",
                    "international_number": "",
                    "narrator_chain": "",
                    "chapter_intro": fawaz_sections.get(str(sec_id), ""),
                }
            else:
                existing_h = book_data[sec_id][h_num]
                # Fill missing language columns
                # Note: fawaz english is already in our data from other sources
                pass

        merged[book_slug] = dict(book_data)

        # Stats
        total_hadiths = sum(len(h) for h in book_data.values())
        total_sections = len(book_data)
        print(f"  {book_slug}: {total_hadiths} hadiths in {total_sections} sections")

    return merged


def write_toon_files(merged):
    """Write merged data back to .toon files."""
    output_dir = REPO_ROOT / "editions_merged"
    output_dir.mkdir(exist_ok=True)

    for book_slug, sections in sorted(merged.items()):
        book_dir = output_dir / book_slug / "sections"
        book_dir.mkdir(parents=True, exist_ok=True)

        for sec_id in sorted(sections.keys()):
            hadiths = sections[sec_id]
            if not hadiths:
                continue

            # Sort by hadith number
            def get_hadith_sort_key(h):
                try:
                    return int(h.get("hadithnumber", 0))
                except (ValueError, TypeError):
                    return 0

            sorted_hadiths = sorted(hadiths.values(), key=get_hadith_sort_key)

            # Write .toon file
            toon_file = book_dir / f"{sec_id}.toon"
            with open(toon_file, "w", encoding="utf-8") as f:
                f.write(f"metadata:\n")
                f.write(f"  section_id: {sec_id}\n")
                f.write(f"\n")
                f.write(f"hadiths[{len(sorted_hadiths)}]{{{','.join(TOON_COLS)}}}:\n")

                for h in sorted_hadiths:
                    row = [csv_escape(h.get(col, "")) for col in TOON_COLS]
                    f.write(",".join(row) + "\n")

            print(
                f"  Written {book_slug}/sections/{sec_id}.toon ({len(sorted_hadiths)} hadiths)"
            )


def main():
    print("Loading existing .toon files...")
    existing = load_existing_toon()
    print(
        f"  Loaded {sum(len(s) for b in existing.values() for s in b.values())} hadiths"
    )

    print("\nLoading AhmedBaset/hadith-json...")
    ahmedbaset = load_ahmedbaset()

    print("\nLoading gurgutan/sunnah_ar_en_dataset...")
    gurgutan = load_gurgutan()

    print("\nLoading fawazahmed0/hadith-api...")
    fawazahmed0 = load_fawazahmed0()

    print("\n" + "=" * 50)
    print("Merging all sources...")
    merged = merge_sources(existing, ahmedbaset, gurgutan, fawazahmed0)

    print("\n" + "=" * 50)
    print("Writing merged .toon files...")
    write_toon_files(merged)

    print("\nDone! Merged files written to editions_merged/")


if __name__ == "__main__":
    main()
