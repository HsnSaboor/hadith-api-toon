#!/usr/bin/env python3
import re
from pathlib import Path

# Mapping of the 25 active registered books in info.toon
ACTIVE_BOOKS = {
    "abudawud", "aladab-almufrad", "bayhaqi", "bukhari", "bulugh-al-maram",
    "dehlawi", "fatah-alrabani", "ibnmajah", "lulu-wal-marjan", "malik",
    "mishkat", "muajam-tabarani-saghir", "musannaf-ibn-abi-shaybah", "muslim",
    "musnad-ahmed", "mustadrak", "nasai", "nawawi", "qudsi", "sahih-ibn-khuzaymah",
    "shamail-tirmazi", "silsila-sahih", "sunan-al-daraqutni", "sunan-darmi", "tirmidhi"
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
            # Row count check via CSV prefix
            if re.match(r'^\s*\"?\d+\"?\s*,', line_str):
                count += 1
    return count

def sync_metadata():
    root_info_path = Path("info.toon")
    if not root_info_path.exists():
        print("Error: root info.toon not found.")
        return
        
    root_lines = root_info_path.read_text(encoding="utf-8").splitlines()
    new_root_lines = []
    
    # 1. Update root info.toon
    header = root_lines[0]
    new_root_lines.append(header)
    
    total_db_hadiths = 0
    actual_counts = {}
    
    # Simple CSV parser for root
    for line in root_lines[1:]:
        trimmed = line.strip()
        if not trimmed:
            continue
            
        # Parse fields: id, name, total_hadiths, available_languages, path
        # Using a regex to split CSV line safely
        parts = re.findall(r'"([^"]*)"|([^,]+)', trimmed)
        parts = [p[0] if p[0] else p[1] for p in parts]
        
        if len(parts) >= 5:
            book_id = parts[0]
            if book_id in ACTIVE_BOOKS:
                actual_count = count_hadiths_on_disk(book_id)
                actual_counts[book_id] = actual_count
                total_db_hadiths += actual_count
                
                # Reconstruct the line with the actual count
                parts[2] = str(actual_count)
                reconstructed = ",".join(f'"{x}"' for x in parts)
                new_root_lines.append(reconstructed)
            else:
                new_root_lines.append(line)
        else:
            new_root_lines.append(line)
            
    root_info_path.write_text("\n".join(new_root_lines) + "\n", encoding="utf-8")
    print(f"Updated root info.toon. Total active hadiths: {total_db_hadiths:,}")
    
    # 2. Update each book-level info.toon
    for book_id in ACTIVE_BOOKS:
        book_info_path = Path("editions") / book_id / "info.toon"
        if not book_info_path.exists():
            continue
            
        content = book_info_path.read_text(encoding="utf-8")
        actual_count = actual_counts.get(book_id, 0)
        
        # Regex replace total_hadiths in metadata block
        updated_content = re.sub(
            r'(total_hadiths:\s*")\d+(")',
            rf'\g<1>{actual_count}\2',
            content
        )
        # Handle unquoted integers just in case
        updated_content = re.sub(
            r'(total_hadiths:\s*)(\d+)(\s*\n)',
            rf'\g<1>{actual_count}\3',
            updated_content
        )
        
        book_info_path.write_text(updated_content, encoding="utf-8")
        print(f"Updated editions/{book_id}/info.toon with count: {actual_count}")

if __name__ == "__main__":
    sync_metadata()
