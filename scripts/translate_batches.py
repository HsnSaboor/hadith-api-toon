#!/usr/bin/env python3
import os
import re
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from deep_translator import GoogleTranslator

BASE_DIR = Path("/home/saboor/code/hadith-api-toon")
TASKS_DIR = BASE_DIR / "backfill_tasks"
OUTPUT_DIR = BASE_DIR / "backfill_tasks" / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

UR_TO_ROMAN_MAP = {
    'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ٹ': 't', 'ث': 's', 'ج': 'j', 'چ': 'ch',
    'ح': 'h', 'خ': 'kh', 'د': 'd', 'ڈ': 'd', 'ذ': 'z', 'ر': 'r', 'ڑ': 'r', 'ز': 'z',
    'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a',
    'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'و': 'w', 'ہ': 'h', 'ھ': 'h', 'ء': 'a', 'ی': 'y', 'ے': 'ay', 'ں': 'n', 'ؤ': 'o',
    'آ': 'aa', 'ة': 't'
}

def transliterate_urdu_to_roman(text):
    res = []
    for c in text:
        res.append(UR_TO_ROMAN_MAP.get(c, c))
    cleaned = "".join(res)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def translate_text_chunked(text, target_lang):
    # Clean text
    clean_text = text.replace('\\n', ' ').replace('\\"', '"').replace('\\', '').strip()
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # If short enough, translate directly
    if len(clean_text) <= 900:
        translator = GoogleTranslator(source='ar', target=target_lang)
        return translator.translate(clean_text)
        
    # Split into chunks of under 900 characters on space boundaries
    words = clean_text.split(' ')
    chunks = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + 1 > 900:
            chunks.append(' '.join(curr))
            curr = [w]
            curr_len = len(w)
        else:
            curr.append(w)
            curr_len += len(w) + 1
    if curr:
        chunks.append(' '.join(curr))
        
    translated_chunks = []
    translator = GoogleTranslator(source='ar', target=target_lang)
    for c in chunks:
        # Retry logic per chunk
        for attempt in range(5):
            try:
                res = translator.translate(c)
                if res:
                    translated_chunks.append(res)
                    break
                time.sleep(1)
            except Exception:
                time.sleep(2)
        else:
            # If a chunk fails, fallback to passing empty
            translated_chunks.append("")
            
    return " ".join(translated_chunks).strip()

def translate_task(task):
    book = task["book"]
    lang = task["lang"]
    hn = task["hadithnumber"]
    arabic = task["arabic"]
    
    target_lang = lang
    if lang == "roman-ur":
        target_lang = "ur"
        
    for attempt in range(5):
        try:
            translation = translate_text_chunked(arabic, target_lang)
            if translation:
                if lang == "roman-ur":
                    translation = transliterate_urdu_to_roman(translation)
                return hn, translation
            time.sleep(1)
        except Exception as e:
            print(f"Error translating {book}/{lang} {hn} (attempt {attempt+1}): {e}")
            time.sleep(2)
    return hn, None

def process_batch_file(filepath):
    batch_num = filepath.stem.split('_')[1]
    output_toon = OUTPUT_DIR / f"backfill_{batch_num}.toon"
    
    # Resume check: if output file already exists, skip it
    if output_toon.exists() and output_toon.stat().st_size > 0:
        print(f"Skipping {filepath.name} (already processed)")
        return
        
    with open(filepath, "r", encoding="utf-8") as f:
        tasks = json.load(f)
        
    print(f"Processing {filepath.name} with {len(tasks)} tasks...")
    
    results = []
    # Using 3 workers is gentle and prevents anti-bot triggers
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(translate_task, task): task for task in tasks}
        for future in as_completed(futures):
            hn, trans = future.result()
            if trans:
                results.append((hn, trans))
                
    results.sort(key=lambda x: x[0])
    
    with open(output_toon, "w", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(results)
        
    print(f"Saved {len(results)} translations to {output_toon.name}")

def main():
    batch_files = sorted(TASKS_DIR.glob("batch_*.json"), key=lambda p: int(p.stem.split('_')[1]))
    print(f"Found {len(batch_files)} batches to translate.")
    
    for bf in batch_files:
        process_batch_file(bf)

if __name__ == "__main__":
    main()
