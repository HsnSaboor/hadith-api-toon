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
TASKS_PATH = BASE_DIR / "backfill_tasks" / "truncated_tasks.json"

LOCAL_URL = "http://localhost:8080/v1/chat/completions"
LOCAL_MODEL = "nemotron-3-ultra-free"

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

write_lock = threading.Lock()
tasks_lock = threading.Lock()

def remove_completed_task(task_to_remove):
    with tasks_lock:
        try:
            if TASKS_PATH.exists():
                with open(TASKS_PATH, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                updated_tasks = [t for t in tasks if not (
                    t["book"] == task_to_remove["book"] and 
                    t["lang"] == task_to_remove["lang"] and 
                    t["hadithnumber"] == task_to_remove["hadithnumber"]
                )]
                with open(TASKS_PATH, "w", encoding="utf-8") as f:
                    json.dump(updated_tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error updating tasks file: {e}", flush=True)

def translate_local(arabic_text, target_lang):
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
                    "max_tokens": 3000
                },
                timeout=90
            )
            if resp.status_code == 200:
                choice = resp.json()["choices"][0]
                content = choice.get("message", {}).get("content")
                if content and content.strip():
                    content = content.strip()
                    if "```" in content:
                        blocks = re.findall(r"```[^\n]*\n(.*?)\n```", content, re.DOTALL)
                        if blocks:
                            content = blocks[0].strip()
                    if content.startswith('"') and content.endswith('"'):
                        content = content[1:-1].strip()
                    elif content.startswith("'") and content.endswith("'"):
                        content = content[1:-1].strip()
                    return content
            elif resp.status_code == 429 or resp.status_code == 502:
                print(f"  [LOCAL RATE LIMIT] Attempt {attempt+1}/5 failed. Sleeping...", flush=True)
                time.sleep(5)
            else:
                print(f"  [LOCAL HTTP {resp.status_code}] {resp.text[:100]}", flush=True)
                time.sleep(2)
        except Exception as e:
            print(f"  [LOCAL ERROR] {e}", flush=True)
            time.sleep(2)
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
            return True
    return False

def process_task(task):
    filepath = BASE_DIR / task["filepath"]
    translated = translate_local(task["arabic"], task["lang"])
    if translated:
        if update_hadith_file(filepath, task["hadithnumber"], translated):
            print(f"  [SUCCESS] {task['book']}/{task['lang']} hadith {task['hadithnumber']} backfilled.", flush=True)
            remove_completed_task(task)
            return True, task
    print(f"  [FAILED] {task['book']}/{task['lang']} hadith {task['hadithnumber']} could not be translated.", flush=True)
    return False, task

def main():
    if not TASKS_PATH.exists():
        print("No truncated_tasks.json found.")
        return
        
    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        tasks = json.load(f)
        
    print(f"Starting parallel translation repair of {len(tasks)} tasks using 10 workers...", flush=True)
    
    completed = 0
    success = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_task, task): task for task in tasks}
        for future in as_completed(futures):
            res, task = future.result()
            completed += 1
            if res:
                success += 1
            if completed % 10 == 0 or completed == len(tasks):
                print(f"Progress: {completed}/{len(tasks)} completed ({success} successful).", flush=True)

    print(f"\nRepair finished! Successfully backfilled {success}/{len(tasks)} truncated translations.")

if __name__ == "__main__":
    main()
