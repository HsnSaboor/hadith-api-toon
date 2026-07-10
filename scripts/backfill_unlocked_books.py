#!/usr/bin/env python3
import csv
import json
import os
import re

BASE_DIR = "/home/saboor/code/hadith-api-toon"
EDITIONS_DIR = os.path.join(BASE_DIR, "editions")

def clean_arabic(text):
    if not text:
        return ""
    tashkeel = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
    text = tashkeel.sub('', text)
    text = re.sub(r'[^\u0621-\u064A\s]', '', text)
    return " ".join(text.split())

def are_similar(text1, text2):
    w1 = set(clean_arabic(text1).split())
    w2 = set(clean_arabic(text2).split())
    if not w1 or not w2:
        return False
    overlap = w1 & w2
    ratio = len(overlap) / min(len(w1), len(w2))
    return ratio > 0.40

def process_book(book_name, json_name):
    json_path = os.path.join(BASE_DIR, "scripts/cache", json_name)
    if not os.path.exists(json_path):
        print(f"JSON data not found for {book_name}: {json_path}")
        return
        
    print(f"\n=== Backfilling {book_name} ===")
    print("Loading JSON compile...")
    with open(json_path) as f:
        data = json.load(f)
        
    lookup = {}
    for chap in data.get("chapters", []):
        for sec in chap.get("sections", []):
            for item in sec.get("items", []):
                if item.get("type") == "hadith" or "text" in item:
                    num_str = str(item.get("number", "")).strip()
                    if num_str:
                        lookup[num_str] = item
                        
    print(f"Loaded {len(lookup)} remote hadiths by number.")
    
    sections_dir = os.path.join(EDITIONS_DIR, book_name, "sections")
    trans_dir = os.path.join(EDITIONS_DIR, book_name, "translations", "en", "sections")
    os.makedirs(trans_dir, exist_ok=True)
    
    local_files = sorted([f for f in os.listdir(sections_dir) if f.endswith(".toon")])
    
    total_processed = 0
    total_populated = 0
    
    for fn in local_files:
        section_path = os.path.join(sections_dir, fn)
        trans_path = os.path.join(trans_dir, fn)
        
        with open(section_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            
        header = lines[0]
        output_rows = []
        
        for line in lines[1:]:
            if not line.strip():
                continue
            reader = csv.reader([line])
            row = next(reader)
            if not row:
                continue
                
            local_hn = str(row[0])
            local_ar = row[1]
            total_processed += 1
            
            # Find match in remote JSON
            found_item = None
            if local_hn in lookup:
                item = lookup[local_hn]
                remote_ar = (item.get("chain", {}).get("ar", "") + " " + item.get("text", {}).get("ar", "")).strip()
                if are_similar(local_ar, remote_ar):
                    found_item = item
                    
            if not found_item:
                try:
                    num_int = int(local_hn)
                    for offset in [-1, 1, -2, 2, -3, 3, -4, 4, -5, 5]:
                        check_num = str(num_int + offset)
                        if check_num in lookup:
                            item = lookup[check_num]
                            remote_ar = (item.get("chain", {}).get("ar", "") + " " + item.get("text", {}).get("ar", "")).strip()
                            if are_similar(local_ar, remote_ar):
                                found_item = item
                                break
                except ValueError:
                    pass
            
            # Get English translation
            en_text = ""
            if found_item:
                en_text = found_item.get("text", {}).get("en", "")
                if en_text:
                    total_populated += 1
                    
            output_rows.append([local_hn, en_text])
            
        # Write translated file
        with open(trans_path, "w", encoding="utf-8") as f:
            f.write("hadiths[count]{hadithnumber,text}:\n")
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(output_rows)
            
    print(f"Completed {book_name}. Processed {total_processed} hadiths. Populated {total_populated} translations ({(total_populated/total_processed)*100:.2f}%).")

def main():
    process_book("ibnhibban", "ibnhibban.json")
    process_book("mustadrak", "hakim.json")

if __name__ == "__main__":
    main()
