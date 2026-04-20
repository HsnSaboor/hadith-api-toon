#!/usr/bin/env python3
import json
import os
import sys
import csv
import io
import re

BASE_DIR = os.getcwd()
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
        reader = csv.reader(io.StringIO(s))
        rows.append(next(reader))
    return metadata, header, fields, rows

def merge_book(book_id):
    eng_source_dir = os.path.join(EDITIONS_DIR, f"eng-{book_id}", "sections")
    if not os.path.exists(eng_source_dir):
        print(f"No source dir for eng-{book_id}")
        return

    # Load all English from eng-book
    eng_map = {} # hn -> (text, narrator)
    for fname in os.listdir(eng_source_dir):
        if not fname.endswith(".toon"): continue
        _, _, fields, rows = parse_toon_file(os.path.join(eng_source_dir, fname))
        hn_idx = fields.index("hadithnumber")
        text_idx = fields.index("text")
        narr_idx = fields.index("narrator_chain") if "narrator_chain" in fields else -1
        for r in rows:
            hn = r[hn_idx]
            text = r[text_idx]
            narr = r[narr_idx] if narr_idx != -1 else ""
            if text:
                eng_map[hn] = (text, narr)

    target_dir = os.path.join(EDITIONS_DIR, book_id, "sections")
    if not os.path.exists(target_dir):
        print(f"No target dir for {book_id}")
        return

    print(f"Merging English into {book_id} ({len(eng_map)} source hadiths)...")
    total_changes = 0
    
    for fname in sorted(os.listdir(target_dir)):
        if not fname.endswith(".toon"): continue
        fpath = os.path.join(target_dir, fname)
        metadata, header, fields, rows = parse_toon_file(fpath)
        
        if "english" not in fields:
            fields.append("english")
        
        eng_idx = fields.index("english")
        narr_idx = fields.index("narrator_chain") if "narrator_chain" in fields else -1
        
        changed = False
        new_rows = []
        for row in rows:
            hn = row[0]
            if hn in eng_map:
                while len(row) < len(fields): row.append("")
                row[eng_idx] = eng_map[hn][0]
                if narr_idx != -1:
                    row[narr_idx] = eng_map[hn][1]
                changed = True
                total_changes += 1
            new_rows.append(row)
        
        if changed:
            new_header = f"hadiths[{len(new_rows)}]{{{','.join(fields)}}}:"
            with open(fpath, "w", encoding="utf-8") as f:
                f.writelines(metadata)
                f.write("\n" + new_header + "\n")
                for r in new_rows:
                    f.write(",".join(escape_toon_val(v) for v in r) + "\n")

    print(f"  Done. {total_changes} hadiths updated.")

if __name__ == "__main__":
    books = ["musnad-ahmed", "aladab-almufrad", "shamail-tirmazi", "mishkat", "bulugh-al-maram", "sunan-darmi"]
    for b in books:
        merge_book(b)
