#!/usr/bin/env encoding=utf-8
import json
import re
import csv
from pathlib import Path
from datasets import load_dataset

BASE_DIR = Path("/home/saboor/code/hadith-api-toon")
TASKS_DIR = BASE_DIR / "backfill_tasks"
OUTPUT_DIR = TASKS_DIR / "output"

def main():
    print("Loading fawazahmed0/hadith-data from cache...")
    dataset = load_dataset('fawazahmed0/hadith-data', split='train')
    
    # Build cache: cache[book][lang][hadithnumber] = text
    cache = {}
    for r in dataset:
        name = r.get("name", "")
        if "-" in name:
            lang_prefix, book_suffix = name.split("-", 1)
        else:
            continue
            
        lang = {
            "eng": "en",
            "urd": "ur",
            "ben": "bn",
            "tur": "tr",
            "fra": "fr",
            "ind": "id",
            "rus": "ru",
            "tam": "ta"
        }.get(lang_prefix)
        
        if not lang:
            continue
            
        book = {
            "abudawud": "abudawud",
            "bukhari": "bukhari",
            "ibnmajah": "ibnmajah",
            "malik": "malik",
            "muslim": "muslim",
            "nasai": "nasai",
            "tirmidhi": "tirmidhi",
            "dehlawi": "dehlawi",
            "nawawi": "nawawi40",
            "qudsi": "qudsi40"
        }.get(book_suffix)
        
        if not book:
            continue
            
        hnum = str(r.get("hadith", ""))
        text = (r.get("text") or "").strip()
        
        if text:
            cache.setdefault(book, {}).setdefault(lang, {})[hnum] = text

    print("Loaded Fawaz dataset cache successfully!")
    
    unmatched_path = TASKS_DIR / "unmatched_tasks.json"
    if not unmatched_path.exists():
        print("No unmatched_tasks.json found. Nothing to do.")
        return
        
    with open(unmatched_path, "r", encoding="utf-8") as f:
        unmatched_tasks = json.load(f)
        
    print(f"Loaded {len(unmatched_tasks)} unmatched tasks.")
    
    task_to_batch = {}
    batch_files = sorted(TASKS_DIR.glob("batch_*.json"), key=lambda p: int(p.stem.split('_')[1]))
    for bf in batch_files:
        batch_num = bf.stem.split('_')[1]
        with open(bf, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        for t in tasks:
            key = (t["book"], t["lang"], t["hadithnumber"])
            task_to_batch[key] = batch_num

    toon_updates = {}
    matched_count = 0
    still_unmatched = []
    
    for t in unmatched_tasks:
        book = t["book"]
        lang = t["lang"]
        hnum = str(t["hadithnumber"])
        hnum_clean = hnum.strip()
        hnum_base = hnum_clean.split(".")[0]
        
        key = (book, lang, t["hadithnumber"])
        batch_num = task_to_batch.get(key)
        if not batch_num:
            continue
            
        text = None
        book_cache = cache.get(book, {})
        lang_cache = book_cache.get(lang, {})
        if lang_cache:
            text = lang_cache.get(hnum_clean) or lang_cache.get(hnum_base)
            
        if text and text.strip():
            toon_updates.setdefault(batch_num, []).append((t["hadithnumber"], text))
            matched_count += 1
        else:
            still_unmatched.append(t)
            
    print(f"Matched {matched_count} new translations using Fawaz dataset!")
    print(f"Still unmatched: {len(still_unmatched)}")
    
    for batch_num, new_rows in toon_updates.items():
        toon_path = OUTPUT_DIR / f"backfill_{batch_num}.toon"
        existing_rows = []
        if toon_path.exists():
            with open(toon_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                existing_rows = list(reader)
                
        existing_hnums = {row[0] for row in existing_rows}
        merged_rows = list(existing_rows)
        for hn, txt in new_rows:
            if hn not in existing_hnums:
                merged_rows.append([hn, txt])
                
        # Sort by key value safely
        def get_sort_key(row):
            val = str(row[0])
            match = re.match(r'^(\d+)', val)
            if match:
                return (0, int(match.group(1)), val)
            return (1, 0, val)

        merged_rows.sort(key=get_sort_key)
        with open(toon_path, "w", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(merged_rows)
            
        print(f"Updated backfill_{batch_num}.toon with {len(new_rows)} new translations.")
        
    with open(unmatched_path, "w", encoding="utf-8") as f:
        json.dump(still_unmatched, f, ensure_ascii=False, indent=2)
    print("Saved remaining unmatched tasks back to unmatched_tasks.json")

if __name__ == "__main__":
    main()
