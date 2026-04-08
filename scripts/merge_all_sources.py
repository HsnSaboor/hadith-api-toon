#!/usr/bin/env python3
"""
Merge Urdu from fawazahmed0/hadith-api and English from AhmedBaset/hadith-json
into our scraped_data files.

Sources:
1. fawazahmed0/hadith-api (local zip) - Urdu for 7 books + English for 10 books
2. AhmedBaset/hadith-json (sunnah.com) - Arabic + English for 16 books

Both use `hadithnumber` / `idInBook` that aligns with our numbering.
"""

import json
import os
import re

SCRAPED_DIR = "/home/saboor/code/hadith-api-toon/scraped_data"
FAWAZ_DIR = "/home/saboor/code/fawazahmed0-data/hadith-api-1/database/linebyline"
HJSON_DIR = "/home/saboor/code/hadith-json-data"

# fawazahmed0 Urdu files
FAWAZ_URDU = {
    "bukhari": "urd-bukhari.txt",
    "muslim": "urd-muslim.txt",
    "abudawud": "urd-abudawud.txt",
    "nasai": "urd-nasai.txt",
    "ibnmajah": "urd-ibnmajah.txt",
    "malik": "urd-malik.txt",
    "tirmidhi": "urd-tirmidhi.txt",
}

# fawazahmed0 English files
FAWAZ_ENGLISH = {
    "bukhari": "eng-bukhari.txt",
    "muslim": "eng-muslim.txt",
    "abudawud": "eng-abudawud.txt",
    "nasai": "eng-nasai.txt",
    "ibnmajah": "eng-ibnmajah.txt",
    "malik": "eng-malik.txt",
    "tirmidhi": "eng-tirmidhi.txt",
    "nawawi": "eng-nawawi.txt",
    "qudsi": "eng-qudsi.txt",
    "dehlawi": "eng-dehlawi.txt",
}

# hadith-json files (sunnah.com data)
HJSON_MAP = {
    "bukhari": "bukhari.json",
    "muslim": "muslim.json",
    "abudawud": "abudawud.json",
    "nasai": "nasai.json",
    "ibnmajah": "ibnmajah.json",
    "malik": "malik.json",
    "tirmidhi": "tirmidhi.json",
    "musnad-ahmed": "ahmed.json",
    "sunan-darmi": "darimi.json",
    "aladab-almufrad": "aladab_almufrad.json",
    "bulugh-al-maram": "bulugh_almaram.json",
    "mishkat": "mishkat_almasabih.json",
    "shamail-tirmazi": "shamail_muhammadiyah.json",
    "nawawi": "nawawi40.json",
    "qudsi": "qudsi40.json",
    "dehlawi": "shahwaliullah40.json",
}


def parse_fawaz_linebyline(filepath):
    """Parse fawazahmed0 line-by-line format: 'number | text'"""
    results = {}
    if not os.path.exists(filepath):
        return results

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^(\d+(?:\.\d+)?)\s*\|\s*(.+)$", line)
            if match:
                hnum = match.group(1).split(".")[0]  # Handle decimal numbers
                text = match.group(2).strip()
                if hnum not in results:
                    results[hnum] = text

    return results


def parse_hadith_json(filepath):
    """Parse AhmedBaset/hadith-json format."""
    results = {}
    if not os.path.exists(filepath):
        return results

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    hadiths = data.get("hadiths", [])
    for h in hadiths:
        hnum = str(h.get("idInBook", ""))
        if not hnum:
            continue

        entry = {}

        # Arabic
        arabic = h.get("arabic", "")
        if arabic:
            entry["arabic"] = arabic

        # English
        english = h.get("english", {})
        if isinstance(english, dict):
            narrator = english.get("narrator", "")
            text = english.get("text", "")
            if narrator or text:
                entry["english"] = f"{narrator}: {text}" if narrator else text

        results[hnum] = entry

    return results


def main():
    os.makedirs(SCRAPED_DIR, exist_ok=True)

    print("=" * 70)
    print("MERGING URDU + ENGLISH FROM ALIGNED SOURCES")
    print("=" * 70)

    # Process each book
    all_books = set(
        list(FAWAZ_URDU.keys()) + list(FAWAZ_ENGLISH.keys()) + list(HJSON_MAP.keys())
    )

    for book_key in sorted(all_books):
        print(f"\n{'=' * 60}")
        print(f"Processing: {book_key}")
        print(f"{'=' * 60}")

        # Load existing scraped data
        scraped_path = os.path.join(SCRAPED_DIR, f"{book_key}_scraped.json")
        existing = {}
        if os.path.exists(scraped_path):
            with open(scraped_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    existing = raw

        # Load fawazahmed0 Urdu
        fawaz_urdu = {}
        if book_key in FAWAZ_URDU:
            fawaz_path = os.path.join(FAWAZ_DIR, FAWAZ_URDU[book_key])
            fawaz_urdo = parse_fawaz_linebyline(fawaz_path)
            fawaz_urdu = fawaz_urdo
            print(f"  fawazahmed0 Urdu: {len(fawaz_urdu)} hadiths")

        # Load fawazahmed0 English
        fawaz_eng = {}
        if book_key in FAWAZ_ENGLISH:
            fawaz_path = os.path.join(FAWAZ_DIR, FAWAZ_ENGLISH[book_key])
            fawaz_eng = parse_fawaz_linebyline(fawaz_path)
            print(f"  fawazahmed0 English: {len(fawaz_eng)} hadiths")

        # Load hadith-json
        hjson_data = {}
        if book_key in HJSON_MAP:
            hjson_path = os.path.join(HJSON_DIR, HJSON_MAP[book_key])
            hjson_data = parse_hadith_json(hjson_path)
            print(f"  hadith-json Arabic+English: {len(hjson_data)} hadiths")

        if not fawaz_urdu and not fawaz_eng and not hjson_data:
            print(f"  No new data available, skipping")
            continue

        # Merge all data
        merged = dict(existing)
        all_keys = set(
            list(fawaz_urdu.keys())
            + list(fawaz_eng.keys())
            + list(hjson_data.keys())
            + list(merged.keys())
        )

        for hnum in all_keys:
            if hnum not in merged:
                merged[hnum] = {
                    "hadith_number": int(hnum) if hnum.isdigit() else 0,
                    "urdu": "",
                    "arabic": "",
                    "english": "",
                    "international_number": None,
                    "chapter_title": "",
                }

            entry = merged[hnum]

            # Urdu from fawazahmed0
            if hnum in fawaz_urdu and not entry.get("urdu", "").strip():
                entry["urdu"] = fawaz_urdu[hnum]

            # English from fawazahmed0
            if hnum in fawaz_eng and not entry.get("english", "").strip():
                entry["english"] = fawaz_eng[hnum]

            # Arabic from hadith-json
            if hnum in hjson_data:
                hj = hjson_data[hnum]
                if hj.get("arabic") and not entry.get("arabic", "").strip():
                    entry["arabic"] = hj["arabic"]
                if hj.get("english") and not entry.get("english", "").strip():
                    entry["english"] = hj["english"]

        # Save
        with open(scraped_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        urdu_count = sum(1 for v in merged.values() if v.get("urdu", "").strip())
        eng_count = sum(1 for v in merged.values() if v.get("english", "").strip())
        ar_count = sum(1 for v in merged.values() if v.get("arabic", "").strip())

        print(
            f"  RESULT: {len(merged)} hadiths | Arabic: {ar_count} | Urdu: {urdu_count} | English: {eng_count}"
        )

    print(f"\n{'=' * 70}")
    print("MERGE COMPLETE!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
