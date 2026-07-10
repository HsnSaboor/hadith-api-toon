#!/usr/bin/env python3
import os
import re
from pathlib import Path

# Human-readable names for all 31 collections
BOOK_NAMES = {
    "abdurrazzaq": "Musannaf Abdur Razzaq",
    "abudawud": "Sunan Abu Dawud",
    "aladab-almufrad": "Al-Adab Al-Mufrad",
    "bayhaqi": "Sunan Al-Kubra Bayhaqi",
    "bukhari": "Sahih al-Bukhari",
    "bulugh-al-maram": "Bulugh al-Maram",
    "dehlawi": "Forty Hadith of Shah Waliullah Dehlawi",
    "fatah-alrabani": "Fatah Al-Rabani",
    "hisn": "Hisn al-Muslim",
    "ibnhibban": "Sahih Ibn Hibban",
    "ibnmajah": "Sunan Ibn Majah",
    "lulu-wal-marjan": "Al-Lulu wal-Marjan",
    "malik": "Muwatta Malik",
    "mishkat": "Mishkat al-Masabih",
    "muajam-tabarani-saghir": "Muajam Tabarani Saghir",
    "musannaf-ibn-abi-shaybah": "Musannaf Ibn Abi Shaybah",
    "muslim": "Sahih Muslim",
    "musnad-ahmed": "Musnad Ahmad",
    "mustadrak": "Al-Mustadrak",
    "nasai": "Sunan an-Nasai",
    "nasaikubra": "Sunan al-Kubra an-Nasai",
    "nawawi": "Forty Hadith of an-Nawawi",
    "qudsi": "Forty Hadith Qudsi",
    "riyadussalihin": "Riyad as-Salihin",
    "sahih-ibn-khuzaymah": "Sahih Ibn Khuzaymah",
    "shamail-tirmazi": "Shamail-e-Tirmazi",
    "silsila-sahih": "Silsila Sahiha",
    "sunan-al-daraqutni": "Sunan al-Daraqutni",
    "sunan-darmi": "Sunan ad-Darimi",
    "tirmidhi": "Jami At-Tirmidhi",
    "virtues": "Virtues of Good Deeds"
}

def count_hadiths_on_disk(book_id):
    sections_dir = Path("editions") / book_id / "sections"
    if not sections_dir.exists():
        return 0
        
    count = 0
    for sec_file in sections_dir.glob("*.toon"):
        content = sec_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if re.match(r'^\s*\"?\d+\"?\s*,', line_str):
                count += 1
    return count

def get_available_languages(book_id):
    langs = ["ar"]
    trans_dir = Path("editions") / book_id / "translations"
    if trans_dir.exists():
        for lang_dir in sorted(trans_dir.iterdir()):
            if lang_dir.is_dir() and lang_dir.name != "ar":
                langs.append(lang_dir.name)
    return ",".join(langs)

def sync_metadata():
    root = Path("editions")
    all_books = sorted([d.name for d in root.iterdir() if d.is_dir()])
    
    total_db_hadiths = 0
    actual_counts = {}
    
    root_lines = [f"books[{len(all_books)}]{{id,name,total_hadiths,available_languages,path}}:"]
    
    # 1. Update book-level info.toon first
    for book_id in all_books:
        actual_count = count_hadiths_on_disk(book_id)
        actual_counts[book_id] = actual_count
        total_db_hadiths += actual_count
        
        langs_str = get_available_languages(book_id)
        pretty_name = BOOK_NAMES.get(book_id, book_id)
        
        # Add to root list
        root_lines.append(f'"{book_id}","{pretty_name}","{actual_count}","{langs_str}","editions/{book_id}"')
        
        # Update individual book info.toon
        book_info_path = Path("editions") / book_id / "info.toon"
        if not book_info_path.exists():
            continue
            
        content = book_info_path.read_text(encoding="utf-8")
        
        # Sync book_name, total_hadiths, available_languages in metadata block
        updated_content = re.sub(
            r'(book_name:\s*")([^"]*)(")',
            rf'\g<1>{pretty_name}\3',
            content
        )
        updated_content = re.sub(
            r'(total_hadiths:\s*")\d+(")',
            rf'\g<1>{actual_count}\2',
            updated_content
        )
        # Handle unquoted counts
        updated_content = re.sub(
            r'(total_hadiths:\s*)(\d+)(\s*\n)',
            rf'\g<1>{actual_count}\3',
            updated_content
        )
        updated_content = re.sub(
            r'(available_languages:\s*")([^"]*)(")',
            rf'\g<1>{langs_str}\3',
            updated_content
        )
        
        book_info_path.write_text(updated_content, encoding="utf-8")
        print(f"Updated editions/{book_id}/info.toon -> name: {pretty_name}, count: {actual_count}, langs: {langs_str}")
        
    # 2. Write updated root info.toon
    root_info_path = Path("info.toon")
    # Replace backslashes in header line for toon format
    header_line = root_lines[0].replace("\\", "")
    final_root_content = [header_line] + root_lines[1:]
    
    root_info_path.write_text("\n".join(final_root_content) + "\n", encoding="utf-8")
    print(f"\nWritten root info.toon. Registered all {len(all_books)} books. Total hadiths: {total_db_hadiths:,}")

if __name__ == "__main__":
    sync_metadata()
