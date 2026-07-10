#!/usr/bin/env python3
import os
import csv
import json
from pathlib import Path

BASE_DIR = Path("/home/saboor/code/hadith-api-toon")
TASKS_DIR = BASE_DIR / "backfill_tasks"
OUTPUT_DIR = TASKS_DIR / "output"

def main():
    print("Loading backfill configuration and generated translations...")
    
    # Map hadithnumber to filepath by scanning batch files
    # Structure: hadith_mapping[(book, lang, section_file, hadithnumber)] = filepath
    hadith_to_filepath = {}
    
    batch_files = sorted(TASKS_DIR.glob("batch_*.json"), key=lambda p: int(p.stem.split('_')[1]))
    for bf in batch_files:
        with open(bf, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        for t in tasks:
            key = (t["book"], t["lang"], t["section_file"], t["hadithnumber"])
            hadith_to_filepath[key] = t["filepath"]

    # Load all translations from backfill_*.toon output files
    # Structure: updates[filepath][hadithnumber] = translated_text
    updates_by_file = {}
    
    toon_files = sorted(OUTPUT_DIR.glob("backfill_*.toon"), key=lambda p: int(p.stem.split('_')[1]))
    for tf in toon_files:
        batch_num = tf.stem.split('_')[1]
        # Match the tasks in the corresponding batch json
        bf = TASKS_DIR / f"batch_{batch_num}.json"
        if not bf.exists():
            print(f"Warning: batch configuration file {bf.name} not found for translation {tf.name}")
            continue
            
        with open(bf, "r", encoding="utf-8") as f:
            tasks = json.load(f)
            
        # Read the generated translations
        translations_map = {}
        with open(tf, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 2: continue
                translations_map[row[0]] = row[1]
                
        for t in tasks:
            hn = t["hadithnumber"]
            filepath = t["filepath"]
            if hn in translations_map:
                updates_by_file.setdefault(filepath, {})[hn] = translations_map[hn]

    total_files = len(updates_by_file)
    total_hadiths = sum(len(v) for v in updates_by_file.values())
    print(f"Loaded {total_hadiths} translated hadiths across {total_files} files.")
    
    if total_hadiths == 0:
        print("No translations to apply.")
        return

    # Apply updates
    print("Applying translations to editions...")
    applied_count = 0
    
    for filepath_rel, hadith_updates in sorted(updates_by_file.items()):
        filepath = BASE_DIR / filepath_rel
        if not filepath.exists():
            print(f"Warning: destination file {filepath_rel} does not exist.")
            continue
            
        # Read the existing content
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        header = content.split("\n")[0]
        rest = content[len(header)+1:]
        reader = csv.reader(rest.splitlines())
        rows = list(reader)
        
        modified = False
        for row in rows:
            if not row: continue
            hn = row[0]
            if hn in hadith_updates:
                row[1] = hadith_updates[hn]
                modified = True
                applied_count += 1
                
        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header + "\n")
                writer = csv.writer(f, lineterminator="\n")
                writer.writerows(rows)
            print(f"  [UPDATED] {filepath_rel} ({len(hadith_updates)} hadiths)")

    print(f"\nBackfill apply completed! Successfully merged {applied_count} hadith translations.")

if __name__ == "__main__":
    main()
