#!/usr/bin/env python3
"""
Scrape hadith data from sunnah.com for nawawi40, dehlawi, and qudsi
in all available languages.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re

BASE_URL = "https://sunnah.com"
BOOKS = {"nawawi": "/nawawi40", "dehlawi": "/dehlawi", "qudsi": "/qudsi"}

LANGUAGES = {
    "english": "",
    "bangla": "/bangla",
    "bosnian": "/bosnian",
    "indonesian": "/indonesian",
    "urdu": "/urdu",
    "arabic": "/arabic",
}


def scrape_book(book_name, book_path):
    """Scrape all hadiths for a book in all languages."""
    print(f"\n=== Scraping {book_name} ===")

    all_data = {}

    for lang_name, lang_path in LANGUAGES.items():
        url = f"{BASE_URL}{lang_path}{book_path}"
        print(f"  Fetching {lang_name}: {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            hadiths = extract_hadiths(soup, lang_name)

            if hadiths:
                all_data[lang_name] = hadiths
                print(f"    ✓ Found {len(hadiths)} hadiths")
            else:
                print(f"    ✗ No hadiths found")

        except Exception as e:
            print(f"    ✗ Error: {e}")

        time.sleep(1)  # Be polite

    return all_data


def extract_hadiths(soup, language):
    """Extract hadiths from BeautifulSoup object."""
    hadiths = []

    # Find all hadith containers
    hadith_elements = soup.find_all("div", class_="hadith")

    for idx, elem in enumerate(hadith_elements, 1):
        hadith = {"hadithnumber": str(idx)}

        # Extract Arabic text
        arabic_elem = elem.find("div", class_="arabic_hadith")
        if arabic_elem:
            hadith["arabic"] = clean_text(arabic_elem.get_text())

        # Extract translation text based on language
        if language == "english":
            trans_elem = elem.find("div", class_="english_hadith")
            if trans_elem:
                hadith["text"] = clean_text(trans_elem.get_text())
        elif language == "bangla":
            trans_elem = elem.find("div", class_="bangla_hadith")
            if trans_elem:
                hadith["text"] = clean_text(trans_elem.get_text())
        elif language == "urdu":
            trans_elem = elem.find("div", class_="urdu_hadith")
            if trans_elem:
                hadith["text"] = clean_text(trans_elem.get_text())
        elif language == "indonesian":
            trans_elem = elem.find("div", class_="indonesian_hadith")
            if trans_elem:
                hadith["text"] = clean_text(trans_elem.get_text())
        elif language == "bosnian":
            trans_elem = elem.find("div", class_="bosnian_hadith")
            if trans_elem:
                hadith["text"] = clean_text(trans_elem.get_text())

        # Extract grade if available
        grade_elem = elem.find("div", class_="grade")
        if grade_elem:
            hadith["grades"] = clean_text(grade_elem.get_text())

        # Extract reference
        ref_elem = elem.find("div", class_="reference")
        if ref_elem:
            hadith["reference"] = clean_text(ref_elem.get_text())

        if "text" in hadith or "arabic" in hadith:
            hadiths.append(hadith)

    return hadiths


def clean_text(text):
    """Clean up text by removing extra whitespace."""
    if not text:
        return ""
    # Remove extra whitespace and newlines
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def save_to_toon_format(book_name, all_data):
    """Save scraped data to toon format files."""
    base_path = f"/home/saboor/code/hadith-api-toon/editions/{book_name}"

    # Create translations directory
    for lang_name, hadiths in all_data.items():
        if lang_name == "arabic":
            continue  # Arabic goes in main sections

        lang_code = {
            "english": "en",
            "bangla": "bn",
            "urdu": "ur",
            "indonesian": "id",
            "bosnian": "bs",
        }.get(lang_name, lang_name[:2])

        trans_dir = os.path.join(base_path, "translations", lang_code, "sections")
        os.makedirs(trans_dir, exist_ok=True)

        # Save to section 1 (these books only have 1 section)
        output_path = os.path.join(trans_dir, "1.toon")
        with open(output_path, "w", encoding="utf-8") as f:
            for hadith in hadiths:
                if "text" in hadith:
                    json_line = json.dumps(
                        {
                            "hadithnumber": hadith["hadithnumber"],
                            "text": hadith["text"],
                        },
                        ensure_ascii=False,
                    )
                    f.write(json_line + "\n")

        print(f"  Saved {lang_name} to {output_path}")


def main():
    """Main function."""
    for book_name, book_path in BOOKS.items():
        all_data = scrape_book(book_name, book_path)
        if all_data:
            save_to_toon_format(book_name, all_data)

    print("\n✅ Scraping complete!")


if __name__ == "__main__":
    main()
