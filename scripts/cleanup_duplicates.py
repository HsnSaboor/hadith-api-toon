#!/usr/bin/env python3
import os
import sys
import re
import csv
from collections import defaultdict

BASE = "/home/saboor/code/hadith-api-toon"
sys.path.append(os.path.join(BASE, "scripts"))
from audit_1000_deep import read_toon_rows

def write_toon_file(path, name, fields, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{name}[{len(rows)}]{{{','.join(fields)}}}:\n")
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        for r in rows:
            writer.writerow([r.get(fd, "") for fd in fields])

def analyze_and_cleanup(book):
    bpath = os.path.join(BASE, "editions", book)
    ar_dir = os.path.join(bpath, "sections")
    ur_dir = os.path.join(bpath, "translations", "ur", "sections")
    
    if not os.path.isdir(ar_dir) or not os.path.isdir(ur_dir):
        print(f"Skipping {book} - directories not found.")
        return
        
    print(f"\n==================================================")
    print(f"Analyzing duplicates in {book} (ur)...")
    print(f"==================================================")
    
    # 1. Load all Urdu translations
    ur_data = {} # (section_file, hadithnumber) -> row dict
    text_to_hns = defaultdict(list) # text -> list of (section_file, hadithnumber)
    
    section_files = sorted([f for f in os.listdir(ur_dir) if f.endswith(".toon")])
    
    for sf in section_files:
        _, _, rows = read_toon_rows(os.path.join(ur_dir, sf))
        for r in rows:
            hn = r.get("hadithnumber")
            txt = r.get("text", "").strip()
            if hn:
                ur_data[(sf, hn)] = r
                if txt and len(txt) > 30: # ignore very short common strings like "ہاں" or "نہیں"
                    text_to_hns[txt].append((sf, hn))

    # 2. Find duplicate texts
    duplicates = {txt: hns for txt, hns in text_to_hns.items() if len(hns) > 1}
    print(f"Found {len(duplicates)} distinct text strings that are duplicated.")
    total_duplicate_instances = sum(len(hns) for hns in duplicates.values())
    print(f"Total rows involved in duplicates: {total_duplicate_instances}")

    # 3. For each duplicate group, inspect Arabic texts
    artifacts_cleared = 0
    legitimate_count = 0
    generic_placeholder_count = 0
    
    # We will read Arabic rows on demand and cache them
    ar_cache = {} # (section_file, hadithnumber) -> arabic text
    
    def get_arabic(sf, hn):
        key = (sf, hn)
        if key in ar_cache:
            return ar_cache[key]
        
        ar_path = os.path.join(ar_dir, sf)
        if not os.path.exists(ar_path):
            ar_cache[key] = ""
            return ""
            
        _, _, rows = read_toon_rows(ar_path)
        for r in rows:
            cur_hn = r.get("hadithnumber")
            if cur_hn:
                txt = r.get("text", "").strip() or r.get("arabic", "").strip()
                ar_cache[(sf, cur_hn)] = txt
        return ar_cache.get(key, "")

    # Common generic Urdu translation placeholder phrases
    generic_phrases = [
        "سند سے بھی",
        "دوسری سند سے",
        "حدیث اسی طرح مروی ہے",
        "مذکورہ بالا حدیث مروی ہے",
        "اس سند سے بھی یہی حدیث منقول ہے",
        "اسی طرح کی حدیث",
        "سابقہ حدیث منقول ہے",
        "ماخذ کا متن",
        "ترجمہ کے لیے",
        "مذکورہ بالا حدیث"
    ]

    modified_files = set()
    
    for txt, hns in duplicates.items():
        # Load all Arabic texts for these hadith numbers
        ar_texts = []
        for sf, hn in hns:
            ar = get_arabic(sf, hn)
            if ar:
                ar_texts.append(ar)
        
        # Check if they are actually the same Arabic text
        if len(ar_texts) < 2:
            continue
            
        # Compare first Arabic text with others
        first_ar = ar_texts[0]
        all_same_arabic = True
        for other_ar in ar_texts[1:]:
            # Simple heuristic: if length difference is massive, or Jaccard similarity is low
            # Let's clean up punctuation/spaces for comparison
            def clean(t):
                return re.sub(r'\s+', '', re.sub(r'[^\w]', '', t))
            c1 = clean(first_ar)
            c2 = clean(other_ar)
            
            # If they are very different in length or content
            if not c1 or not c2:
                all_same_arabic = False
                break
            len_ratio = min(len(c1), len(c2)) / max(len(c1), len(c2))
            if len_ratio < 0.8:
                all_same_arabic = False
                break
        
        is_generic = any(gp in txt for gp in generic_phrases)
        
        if all_same_arabic:
            # Genuinely same hadith repeated in different parts/chains
            legitimate_count += len(hns)
        else:
            # Different Arabic but identical translation. This is an LLM artifact!
            # Or it's a generic phrase that the translator outputted
            if is_generic:
                generic_placeholder_count += len(hns)
            
            # Clear these translations
            for sf, hn in hns:
                row = ur_data[(sf, hn)]
                row["text"] = "" # Clear it
                modified_files.add(sf)
                artifacts_cleared += 1

    print(f"Analysis summary:")
    print(f"  Legitimate duplicates (same Arabic text): {legitimate_count}")
    print(f"  Generic placeholders/artifacts cleared: {artifacts_cleared} (including {generic_placeholder_count} generic phrases)")
    
    # Save modified files
    if modified_files:
        print(f"Rewriting {len(modified_files)} modified Urdu translation files...")
        for sf in modified_files:
            path = os.path.join(ur_dir, sf)
            # Re-read to get correct schema and original rows to rewrite properly
            name, fields, rows = read_toon_rows(path)
            # update rows with cleared texts
            for r in rows:
                hn = r.get("hadithnumber")
                if hn and (sf, hn) in ur_data:
                    r["text"] = ur_data[(sf, hn)]["text"]
            write_toon_file(path, name, fields, rows)
        print("Files successfully updated!")
    else:
        print("No files modified.")

if __name__ == "__main__":
    analyze_and_cleanup("muajam-tabarani-saghir")
    analyze_and_cleanup("sahih-ibn-khuzaymah")
