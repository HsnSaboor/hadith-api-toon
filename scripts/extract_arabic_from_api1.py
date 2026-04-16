#!/usr/bin/env python3
"""
Extract Arabic text from hadith-api-1 folder for all books.
This script verifies and extracts Arabic data from the JSON files.
"""

import json
import os
import glob

# Mapping from our book names to hadith-api-1 book names
BOOK_MAPPING = {
    "abudawud": "ara-abudawud",
    "bukhari": "ara-bukhari",
    "dehlawi": "ara-dehlawi",
    "ibnmajah": "ara-ibnmajah",
    "malik": "ara-malik",
    "muslim": "ara-muslim",
    "nasai": "ara-nasai",
    "nawawi": "ara-nawawi",
    "qudsi": "ara-qudsi",
    "tirmidhi": "ara-tirmidhi",
    "musnad-ahmed": "ara-musnadahmed",
    "aladab-almufrad": "ara-aladab",
    "bulugh-al-maram": "ara-bulugh",
    "mishkat": "ara-mishkat",
    "shamail-tirmazi": "ara-shamail",
    "sunan-darmi": "ara-darimi",
    "muajam-tabarani-saghir": "ara-tabarani",
    "musannaf-ibn-abi-shaybah": "ara-musannaf",
    "mustadrak": "ara-mustadrak",
    "sahih-ibn-khuzaymah": "ara-ibnkhuzaymah",
    "silsila-sahih": "ara-silsila",
    "sunan-al-daraqutni": "ara-daraqutni",
    "fatah-alrabani": "ara-fathalrabbani",
    "lulu-wal-marjan": "ara-lulu",
    "bayhaqi": "ara-bayhaqi",
}

BASE_API_PATH = "/home/saboor/code/hadith-api-toon/hadith-api-1/editions"
BASE_OUTPUT_PATH = "/home/saboor/code/hadith-api-toon/editions"


def extract_arabic_from_book(book_name, api_book_name):
    """Extract Arabic text for a specific book."""
    print(f"\n=== Processing {book_name} ({api_book_name}) ===")

    # Find all JSON files for this book
    book_path = os.path.join(BASE_API_PATH, api_book_name)
    if not os.path.exists(book_path):
        print(f"  ✗ Path not found: {book_path}")
        return 0

    # Get all JSON files (non-minified)
    json_files = sorted(
        [
            f
            for f in os.listdir(book_path)
            if f.endswith(".json") and not f.endswith(".min.json")
        ]
    )

    if not json_files:
        print(f"  ✗ No JSON files found")
        return 0

    print(f"  Found {len(json_files)} section files")

    # Create output directory
    output_dir = os.path.join(
        BASE_OUTPUT_PATH, book_name, "translations", "ar", "sections"
    )
    os.makedirs(output_dir, exist_ok=True)

    total_hadiths = 0

    for json_file in json_files:
        section_num = json_file.replace(".json", "")
        input_path = os.path.join(book_path, json_file)
        output_path = os.path.join(output_dir, f"{section_num}.toon")

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            hadiths = data.get("hadiths", [])

            with open(output_path, "w", encoding="utf-8") as out_f:
                for hadith in hadiths:
                    hadith_num = hadith.get("hadithnumber", "")
                    arabic_text = hadith.get("text", "")

                    if hadith_num and arabic_text:
                        json_line = json.dumps(
                            {"hadithnumber": str(hadith_num), "text": arabic_text},
                            ensure_ascii=False,
                        )
                        out_f.write(json_line + "\n")
                        total_hadiths += 1

        except Exception as e:
            print(f"  ✗ Error processing {json_file}: {e}")

    print(f"  ✓ Extracted {total_hadiths} hadiths")
    return total_hadiths


def main():
    """Main function to extract Arabic for all books."""
    total_books = 0
    total_hadiths = 0

    for book_name, api_book_name in BOOK_MAPPING.items():
        hadiths = extract_arabic_from_book(book_name, api_book_name)
        if hadiths > 0:
            total_books += 1
            total_hadiths += hadiths

    print(f"\n{'=' * 50}")
    print(f"✅ Completed!")
    print(f"   Books processed: {total_books}")
    print(f"   Total hadiths: {total_hadiths}")


if __name__ == "__main__":
    main()
