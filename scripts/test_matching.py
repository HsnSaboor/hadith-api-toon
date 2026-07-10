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
    # Strip tashkeel (diacritics)
    tashkeel = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
    text = tashkeel.sub('', text)
    # Keep only Arabic letters and spaces
    text = re.sub(r'[^\u0621-\u064A\s]', '', text)
    return " ".join(text.split())

def get_prefix(text):
    return clean_arabic(text)

def main():
    json_path = os.path.join(BASE_DIR, "scripts/cache/hakim.json")
    if not os.path.exists(json_path):
        print("JSON file not found")
        return
        
    print("Loading JSON...")
    with open(json_path) as f:
        data = json.load(f)
        
    # Build lookup map from JSON by number
    lookup = {}
    total_remote = 0
    for chap in data.get("chapters", []):
        for sec in chap.get("sections", []):
            for item in sec.get("items", []):
                if item.get("type") == "hadith" or "text" in item:
                    total_remote += 1
                    num_str = str(item.get("number", "")).strip()
                    if num_str:
                        lookup[num_str] = item
                            
    print(f"Loaded {total_remote} remote hadiths, built lookup map by number with {len(lookup)} keys.")
    
    # Check local hadiths in first 5 section files of mustadrak
    sections_dir = os.path.join(EDITIONS_DIR, "mustadrak", "sections")
    local_files = sorted([f for f in os.listdir(sections_dir) if f.endswith(".toon")])
    
    total_local = 0
    matched = 0
    
    # Helper to check if two texts are similar based on word overlap
    def are_similar(text1, text2):
        w1 = set(clean_arabic(text1).split())
        w2 = set(clean_arabic(text2).split())
        if not w1 or not w2:
            return False
        overlap = w1 & w2
        # If more than 30% of words overlap, they are similar
        ratio = len(overlap) / min(len(w1), len(w2))
        return ratio > 0.40

    print("\nAlignment check:")
    for fn in local_files[:5]:
        filepath = os.path.join(sections_dir, fn)
        with open(filepath, encoding="utf-8") as f:
            lines = f.read().splitlines()
        header = lines[0]
        for line in lines[1:]:
            if not line.strip():
                continue
            reader = csv.reader([line])
            row = next(reader)
            if not row:
                continue
            total_local += 1
            local_hn = str(row[0])
            local_ar = row[1]
            
            # Try direct match
            found_item = None
            if local_hn in lookup:
                item = lookup[local_hn]
                remote_ar = (item.get("chain", {}).get("ar", "") + " " + item.get("text", {}).get("ar", "")).strip()
                if are_similar(local_ar, remote_ar):
                    found_item = item
            
            # Try window search if direct match failed
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
                    
            if found_item:
                matched += 1
                if matched <= 10:
                    print(f"  Local: {local_hn} mapped to Remote: {found_item.get('number')}")
                
    print(f"Processed {total_local} local hadiths from first 5 sections.")
    print(f"Matched successfully: {matched} ({matched/total_local*100:.2f}%)")

if __name__ == "__main__":
    main()
