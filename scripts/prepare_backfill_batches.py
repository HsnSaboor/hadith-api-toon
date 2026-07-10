#!/usr/bin/env python3
import os
import re
import csv
import json
from pathlib import Path

BASE_DIR = Path("/home/saboor/code/hadith-api-toon")
EDITIONS_DIR = BASE_DIR / "editions"
TASKS_DIR = BASE_DIR / "backfill_tasks"
TASKS_DIR.mkdir(exist_ok=True)

LANG_NAMES = {
    "en": "English",
    "bn": "Bengali",
    "fr": "French",
    "id": "Indonesian",
    "ru": "Russian",
    "ur": "Urdu",
    "tr": "Turkish",
    "hi": "Hindi",
    "roman-ur": "Roman Urdu"
}

PLACEHOLDER = re.compile(
    r'^(same as|similar to|as above|see (the )?hadith|narration about|'
    r'wrong same as|\.\.\.\s*$|\(as hadith|refer to hadith|same\b|see above|'
    r'mentioned above|same hadith)', re.I)

MARKDOWN_PLACEHOLDERS = ["### अनुवाद", "হাদيس নং", "অনুবাদ", "হাদীس নম্বর"]

def is_truncated(arabic, text):
    if not arabic.strip() or not text.strip():
        return False
    if len(arabic) > 200 and len(text) < 80 and len(text) < 0.1 * len(arabic):
        return True
    return False

def is_placeholder(text):
    text_stripped = text.strip()
    if PLACEHOLDER.match(text_stripped):
        return True
    for mp in MARKDOWN_PLACEHOLDERS:
        if mp in text_stripped:
            return True
    return False

def main():
    print("Scanning database for truncated translations...")
    tasks = []
    
    for book in sorted(os.listdir(EDITIONS_DIR)):
        book_dir = EDITIONS_DIR / book
        if not book_dir.is_dir():
            continue
            
        sections_dir = book_dir / "sections"
        trans_dir = book_dir / "translations"
        if not sections_dir.exists() or not trans_dir.exists():
            continue
            
        # Load Arabic
        arabic_map = {}
        for fn in os.listdir(sections_dir):
            if not fn.endswith(".toon"):
                continue
            with open(sections_dir / fn, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            if not lines: continue
            reader = csv.reader(lines[1:])
            for row in reader:
                if not row: continue
                arabic_map[row[0]] = row[1] if len(row) > 1 else ""
                
        # Scan languages
        for lang in os.listdir(trans_dir):
            if lang not in LANG_NAMES:
                continue
            lang_sections = trans_dir / lang / "sections"
            if not lang_sections.exists():
                continue
                
            for fn in os.listdir(lang_sections):
                if not fn.endswith(".toon"):
                    continue
                filepath = lang_sections / fn
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                if not lines: continue
                reader = csv.reader(lines[1:])
                for row in reader:
                    if not row or len(row) < 2: continue
                    hn = row[0]
                    text = row[1]
                    arabic = arabic_map.get(hn, "")
                    
                    if is_truncated(arabic, text) or is_placeholder(text):
                        if arabic.strip():
                            tasks.append({
                                "book": book,
                                "lang": lang,
                                "section_file": fn,
                                "filepath": str(filepath.relative_to(BASE_DIR)),
                                "hadithnumber": hn,
                                "arabic": arabic
                            })

    total_tasks = len(tasks)
    print(f"Total remaining truncated hadiths: {total_tasks}")
    
    # Save into batches of 100
    batch_size = 100
    for i in range(0, total_tasks, batch_size):
        batch = tasks[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        batch_file = TASKS_DIR / f"batch_{batch_num}.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(batch)} tasks to {batch_file.name}")

if __name__ == "__main__":
    main()
