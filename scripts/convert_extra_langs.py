#!/usr/bin/env python3
import json
import os
import re
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "sunnah.com-download", "abudawud")
EN_PATH = os.path.join(OUT_DIR, "en.json")

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def sort_key(h):
    hn = h["hadithnumber"]
    parts = hn.split(".")
    return (int(parts[0]), float(parts[1]) if len(parts) > 1 else 0)

def main():
    print(f"Loading reference English data from {EN_PATH}...")
    with open(EN_PATH, "r", encoding="utf-8") as f:
        en_data = json.load(f)
        
    # We will process each of the newly added languages
    langs = ["bn", "fr", "hi", "ro", "ru", "tr"]
    
    for lang in langs:
        print(f"\nProcessing language: {lang}...")
        lang_dir = os.path.join(OUT_DIR, lang, "sections")
        if not os.path.exists(lang_dir):
            print(f"  Directory {lang_dir} does not exist, skipping.")
            continue
            
        # Parse all .toon files and build a translation map
        trans_map = {}
        for book in range(1, 44):
            path = os.path.join(lang_dir, f"{book}.toon")
            if not os.path.exists(path):
                print(f"  Warning: Book {book} .toon file not found in {lang_dir}")
                continue
                
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()[1:] # skip header
            reader = csv.reader(lines)
            for row in reader:
                if len(row) >= 2:
                    hn = row[0].strip()
                    text = clean_html(row[1])
                    if hn:
                        # If there are duplicate hadith numbers, we prefer non-empty text, or keep the existing if already set
                        if text:
                            trans_map[hn] = text
                        elif hn not in trans_map:
                            trans_map[hn] = ""
                            
        # Align with en_data
        aligned_data = []
        for h_en in en_data:
            hn = h_en["hadithnumber"]
            text = trans_map.get(hn, "")
            
            # Copy all metadata exactly from en.json
            aligned_data.append({
                "hadithnumber": hn,
                "narrator": h_en.get("narrator", ""),
                "status": h_en.get("status", ""),
                "reference": h_en.get("reference", ""),
                "in_book_reference": h_en.get("in_book_reference", ""),
                "text": text
            })
            
        # Sort by hadith number
        sorted_data = sorted(aligned_data, key=sort_key)
        
        # Save output json
        out_path = os.path.join(OUT_DIR, f"{lang}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)
            
        empty_count = sum(1 for h in sorted_data if not h["text"])
        print(f"  Wrote {len(sorted_data)} records to {out_path} (Empty texts: {empty_count})")

    # Special handling for id (Indonesian) to verify/merge any updates from its .toon files
    print("\nVerifying/updating id (Indonesian) from its .toon files...")
    id_json_path = os.path.join(OUT_DIR, "id.json")
    if os.path.exists(id_json_path):
        with open(id_json_path, "r", encoding="utf-8") as f:
            id_data = json.load(f)
        id_map = {h["hadithnumber"]: h for h in id_data}
        
        id_toon_dir = os.path.join(OUT_DIR, "id", "sections")
        id_toon_map = {}
        if os.path.exists(id_toon_dir):
            for book in range(1, 44):
                path = os.path.join(id_toon_dir, f"{book}.toon")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()[1:]
                    reader = csv.reader(lines)
                    for row in reader:
                        if len(row) >= 2:
                            hn = row[0].strip()
                            text = clean_html(row[1])
                            if hn and text:
                                id_toon_map[hn] = text
                                
            # Merge: only if id_map has empty text or different text and toon is newer
            updated_count = 0
            for hn, text in id_toon_map.items():
                if hn in id_map:
                    if not id_map[hn]["text"].strip() and text.strip():
                        id_map[hn]["text"] = text
                        updated_count += 1
            
            if updated_count > 0:
                sorted_id = sorted(id_data, key=sort_key)
                with open(id_json_path, "w", encoding="utf-8") as f:
                    json.dump(sorted_id, f, ensure_ascii=False, indent=2)
                print(f"  Merged {updated_count} additional translations from id .toon files into id.json")
            else:
                print("  No new translations found in id .toon files to merge.")
        else:
            print("  Indonesian .toon sections directory not found, skipping id merge.")
            
    print("\nAll conversions completed successfully.")

if __name__ == "__main__":
    main()
