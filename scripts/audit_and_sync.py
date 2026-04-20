#!/usr/bin/env python3
import os
import json
import csv
import io
import re

BASE_DIR = os.getcwd()
EDITIONS_DIR = os.path.join(BASE_DIR, "editions")
ROOT_INFO = os.path.join(BASE_DIR, "info.toon")

def count_hadiths_in_sections(sec_dir):
    """Count non-empty rows in Arabic or primary section files."""
    if not os.path.exists(sec_dir): return 0
    total = 0
    for fname in os.listdir(sec_dir):
        if not fname.endswith(".toon"): continue
        with open(os.path.join(sec_dir, fname), "r", encoding="utf-8") as f:
            in_data = False
            for line in f:
                if line.startswith("hadiths["):
                    in_data = True
                    continue
                if in_data and line.strip() and not line.startswith("metadata:") and not line.startswith("  "):
                    total += 1
    return total

def count_translations_in_sections(sec_dir):
    """Count non-empty entries in translation section files (JSONL or Toon rows)."""
    if not os.path.exists(sec_dir): return 0
    total = 0
    for fname in os.listdir(sec_dir):
        if not fname.endswith(".toon"): continue
        with open(os.path.join(sec_dir, fname), "r", encoding="utf-8") as f:
            in_data = False
            fields = []
            for line in f:
                line = line.strip()
                if not line: continue
                
                # Detect format
                if line.startswith("{"): # JSONL format
                    try:
                        data = json.loads(line)
                        if data.get("text") and len(data["text"].strip()) > 0:
                            total += 1
                    except: pass
                elif line.startswith("hadiths["): # Toon row format
                    in_data = True
                    brace_open = line.find("{")
                    brace_close = line.find("}")
                    if brace_open != -1 and brace_close != -1:
                        fields = line[brace_open+1:brace_close].split(",")
                    continue
                elif in_data:
                    # Parse CSV row
                    reader = csv.reader(io.StringIO(line))
                    try:
                        row = next(reader)
                        if "text" in fields:
                            idx = fields.index("text")
                            if idx < len(row) and row[idx].strip():
                                total += 1
                        elif "english" in fields: # Special case for mixed files
                            idx = fields.index("english")
                            if idx < len(row) and row[idx].strip():
                                total += 1
                    except: pass
    return total

def main():
    books_data = {} # book_id -> { "ar": count, "langs": { "en": count, ... } }
    
    for book_id in sorted(os.listdir(EDITIONS_DIR)):
        b_path = os.path.join(EDITIONS_DIR, book_id)
        if not os.path.isdir(b_path): continue
        if book_id.startswith("eng-"): continue # Skip temp dirs
        
        # Arabic Count
        ar_count = count_hadiths_in_sections(os.path.join(b_path, "sections"))
        books_data[book_id] = {"ar": ar_count, "langs": {}}
        
        # Translation Counts
        trans_base = os.path.join(b_path, "translations")
        if os.path.exists(trans_base):
            for lang in sorted(os.listdir(trans_base)):
                l_path = os.path.join(trans_base, lang)
                if not os.path.isdir(l_path): continue
                
                t_count = count_translations_in_sections(os.path.join(l_path, "sections"))
                
                if t_count == 0:
                    print(f"Empty/No data in translation folder: {book_id}/{lang}")
                    continue
                
                books_data[book_id]["langs"][lang] = t_count

    # Update info.toon files
    for book_id, data in books_data.items():
        info_path = os.path.join(EDITIONS_DIR, book_id, "info.toon")
        if not os.path.exists(info_path): continue
        
        with open(info_path, "r") as f:
            lines = f.readlines()
        
        new_lines = []
        langs_str = ",".join(sorted(["ar"] + list(data["langs"].keys())))
        
        for line in lines:
            if "total_hadiths:" in line:
                new_lines.append(f"  total_hadiths: {data['ar']}\n")
            elif "available_languages:" in line:
                new_lines.append(f'  available_languages: "{langs_str}"\n')
            else:
                new_lines.append(line)
        
        with open(info_path, "w") as f:
            f.writelines(new_lines)

    # Sync Root
    if os.path.exists(ROOT_INFO):
        with open(ROOT_INFO, "r") as f:
            lines = f.readlines()
        
        root_lines = []
        in_books = False
        for line in lines:
            if line.startswith("books["):
                in_books = True
                root_lines.append(line)
                continue
            if in_books and line.strip() and not line.startswith("  "):
                in_books = False
            
            if in_books and line.strip().startswith("  "):
                parts = []
                curr = ""; in_q = False
                for c in line.strip():
                    if c == '"': in_q = not in_q; curr += c
                    elif c == "," and not in_q: parts.append(curr); curr = ""
                    else: curr += c
                parts.append(curr)
                
                bid = parts[0].strip()
                if bid in books_data:
                    parts[2] = str(books_data[bid]["ar"])
                    l_list = sorted(["ar"] + list(books_data[bid]["langs"].keys()))
                    parts[3] = f'"{",".join(l_list)}"'
                    root_lines.append("  " + ",".join(parts) + "\n")
                else: root_lines.append(line)
            else: root_lines.append(line)
            
        with open(ROOT_INFO, "w") as f:
            f.writelines(root_lines)

    # Output Report
    print("\n" + "="*80)
    print(f"{'Book ID':<25} | {'Arabic':<7} | {'Translations (Lang:Count)'}")
    print("-"*80)
    for bid, data in sorted(books_data.items()):
        trans_info = ", ".join([f"{l}:{c}" for l, c in sorted(data["langs"].items())])
        print(f"{bid:<25} | {data['ar']:<7} | {trans_info}")

if __name__ == "__main__":
    main()
