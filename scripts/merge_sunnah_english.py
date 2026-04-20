#!/usr/bin/env python3
import json
import os
import sys
import csv
import io

BASE_DIR = os.getcwd()
SCRAPED_DIR = os.path.join(BASE_DIR, "scraped_data")
EDITIONS_DIR = os.path.join(BASE_DIR, "editions")

def escape_toon_val(value):
    if value is None: return ""
    s = str(value).strip()
    if not s: return ""
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s

def parse_toon_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    metadata = []
    header = ""
    fields = []
    rows = []
    in_data = False
    for line in lines:
        s = line.strip()
        if not s: continue
        if s.startswith("hadiths["):
            header = s
            fields = s[s.index("{")+1:s.index("}")].split(",")
            in_data = True
            continue
        if not in_data:
            metadata.append(line)
            continue
        # Data rows
        reader = csv.reader(io.StringIO(s))
        rows.append(next(reader))
    return metadata, header, fields, rows

def merge_book(book_id):
    scraped_path = os.path.join(SCRAPED_DIR, f"{book_id}_english.json")
    if not os.path.exists(scraped_path):
        print(f"No scraped data for {book_id}")
        return

    with open(scraped_path, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)
    
    sec_dir = os.path.join(EDITIONS_DIR, book_id, "sections")
    if not os.path.exists(sec_dir):
        print(f"Sections dir not found for {book_id}")
        return

    print(f"Merging English for {book_id}...")
    total_changes = 0
    
    for fname in sorted(os.listdir(sec_dir)):
        if not fname.endswith(".toon"): continue
        fpath = os.path.join(sec_dir, fname)
        metadata, header, fields, rows = parse_toon_file(fpath)
        
        # Ensure 'english' and 'narrator_chain' columns exist or we map them correctly
        # Mustadrak/Islam360 format: hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro
        # We'll use 'narrator_chain' for Sunnah narrator and 'chapter_intro' for English text temporarily or adjust fields
        
        # Let's check current fields
        if "english" not in fields:
            # If no english column, let's see if we can use chapter_intro or add a column
            # For simplicity, if we are using the Islam360 format I generated:
            # hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro
            # I will RE-WRITE the header to include 'english' if missing
            if "english" not in fields:
                fields.append("english")
        
        eng_idx = fields.index("english")
        narr_idx = fields.index("narrator_chain") if "narrator_chain" in fields else -1
        
        changed = False
        new_rows = []
        for row in rows:
            hn = row[0]
            # Sunnah.com refs might be strings or ints
            data = scraped_data.get(hn)
            if data:
                # Extend row if needed
                while len(row) < len(fields): row.append("")
                
                row[eng_idx] = data["english"]
                if narr_idx != -1:
                    row[narr_idx] = data["narrator"]
                changed = True
                total_changes += 1
            new_rows.append(row)
        
        if changed:
            # Rebuild header with new count and fields
            new_header = f"hadiths[{len(new_rows)}]{{{','.join(fields)}}}:"
            with open(fpath, "w", encoding="utf-8") as f:
                f.writelines(metadata)
                f.write("\n" + new_header + "\n")
                for r in new_rows:
                    f.write(",".join(escape_toon_val(v) for v in r) + "\n")

    # Update available_languages in info.toon
    info_path = os.path.join(EDITIONS_DIR, book_id, "info.toon")
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(info_path, "w", encoding="utf-8") as f:
            for line in lines:
                if "available_languages:" in line:
                    if '"ar,ur"' in line:
                        f.write(line.replace('"ar,ur"', '"ar,en,ur"'))
                    elif 'en' not in line:
                        # Append en
                        m = re.search(r'available_languages:\s*"([^"]+)"', line)
                        if m:
                            langs = m.group(1).split(",")
                            if "en" not in langs:
                                langs.append("en")
                                langs.sort()
                                f.write(f'  available_languages: "{",".join(langs)}"\n')
                            else: f.write(line)
                        else: f.write(line)
                    else: f.write(line)
                else: f.write(line)
    
    print(f"  Done. {total_changes} hadiths updated with English.")

if __name__ == "__main__":
    import re
    books = ["musnad-ahmed", "aladab-almufrad", "shamail-tirmazi", "mishkat", "bulugh-al-maram"]
    for b in books:
        merge_book(b)
