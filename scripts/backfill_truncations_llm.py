#!/usr/bin/env python3
import os
import re
import csv
import json
import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path("/home/saboor/code/hadith-api-toon")
EDITIONS_DIR = BASE_DIR / "editions"

# Local Server Configuration
LOCAL_URL = "http://localhost:8080/v1/chat/completions"
LOCAL_MODEL = "deepseek-v4-flash-free"

# Target language names mapping
LANG_NAMES = {
    "en": "English",
    "bn": "Bengali",
    "fr": "French",
    "id": "Indonesian",
    "ru": "Russian",
    "ur": "Urdu",
    "tr": "Turkish",
    "hi": "Hindi",
    "roman-ur": "Roman Urdu (Urdu written in Latin script)"
}

# Regex and helpers
PLACEHOLDER = re.compile(
    r'^(same as|similar to|as above|see (the )?hadith|narration about|'
    r'wrong same as|\.\.\.\s*$|\(as hadith|refer to hadith|same\b|see above|'
    r'mentioned above|same hadith)', re.I)

MARKDOWN_PLACEHOLDERS = ["### अनुवाद", "হাদিস নং", "অনুবাদ", "হাদীস নম্বর"]

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

write_lock = threading.Lock()

def translate_arabic_to_lang(arabic_text, target_lang):
    target_name = LANG_NAMES.get(target_lang, target_lang)
    system_prompt = f"You are a professional scholar and translator translating Islamic Hadith texts from Arabic to {target_name}."
    user_prompt = f"Translate the following complete Arabic Hadith text into {target_name}. Output ONLY the translated text in {target_name}, do not include any intro, explanation, quotes, or notes:\n\n{arabic_text}"
    
    for attempt in range(5):
        try:
            resp = requests.post(
                LOCAL_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "model": LOCAL_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 4000  # High token limit to accommodate DeepSeek reasoning + translation
                },
                timeout=180  # Longer timeout to prevent read timeouts during deep reasoning
            )
            if resp.status_code == 200:
                choice = resp.json()["choices"][0]
                message = choice.get("message", {})
                content = message.get("content")
                if content is not None and content.strip():
                    content = content.strip()
                    if content.startswith('"') and content.endswith('"'):
                        content = content[1:-1].strip()
                    elif content.startswith("'") and content.endswith("'"):
                        content = content[1:-1].strip()
                    return content
            else:
                print(f"  [LOCAL API HTTP ERROR {resp.status_code}] {resp.text[:100]}", flush=True)
                time.sleep(3)
        except Exception as e:
            print(f"  [LOCAL API CONNECTION ERROR] {e}", flush=True)
            time.sleep(3)
    return None

def update_hadith_file(filepath, hadithnumber, new_text):
    with write_lock:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        header = content.split("\n")[0]
        rest = content[len(header)+1:]
        reader = csv.reader(rest.splitlines())
        rows = list(reader)
        
        updated = False
        for r in rows:
            if r and r[0] == hadithnumber:
                r[1] = new_text
                updated = True
                break
                
        if updated:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header + "\n")
                writer = csv.writer(f, lineterminator="\n")
                writer.writerows(rows)

def process_task(task):
    book, lang, section_file, filepath, hn, arabic, current_text = task
    translated = translate_arabic_to_lang(arabic, lang)
    if translated:
        update_hadith_file(filepath, hn, translated)
        print(f"  [SUCCESS] {book}/{lang} hadith {hn} backfilled.", flush=True)
        return True
    else:
        print(f"  [FAILED] {book}/{lang} hadith {hn} could not be translated.", flush=True)
        return False

def main():
    print("Scanning database for truncated or placeholder translations...", flush=True)
    tasks = []
    
    # 1. Scan all books
    for book in sorted(os.listdir(EDITIONS_DIR)):
        book_dir = EDITIONS_DIR / book
        if not book_dir.is_dir():
            continue
            
        sections_dir = book_dir / "sections"
        trans_dir = book_dir / "translations"
        if not sections_dir.exists() or not trans_dir.exists():
            continue
            
        # Load Arabic text map
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
                
        # Scan each language
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
                            tasks.append((book, lang, fn, filepath, hn, arabic, text))

    total_tasks = len(tasks)
    print(f"Found {total_tasks} tasks to process.", flush=True)
    if total_tasks == 0:
        print("No truncated translations left to repair!", flush=True)
        return

    # 2. Run execution via ThreadPoolExecutor matching local capabilities
    print(f"Starting parallel translation backfill using 4 workers...", flush=True)
    completed = 0
    success = 0
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_task, task): task for task in tasks}
        for future in as_completed(futures):
            res = future.result()
            completed += 1
            if res:
                success += 1
            if completed % 10 == 0:
                print(f"Progress: {completed}/{total_tasks} tasks completed ({success} successful).", flush=True)

    print(f"\nExecution finished! Repaired {success}/{total_tasks} truncated translations.", flush=True)

if __name__ == "__main__":
    main()
