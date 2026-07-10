#!/usr/bin/env python3
"""Translate fatah-alrabani hadiths to English and fill bayhaqi 9027 Arabic using OpenRouter."""

import os
import re
import csv
import sys
import time
import requests

KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]

MODEL = "meta-llama/llama-3-8b-instruct"
key_idx = 0

def call_llm(system, prompt):
    global key_idx
    for attempt in range(10):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {KEYS[key_idx % len(KEYS)]}", "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 4000
                },
                timeout=120
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1].strip()
                return content
            elif resp.status_code == 401:
                key_idx += 1
            elif resp.status_code == 429:
                time.sleep(10)
        except Exception as e:
            time.sleep(5)
    return None

def translate_hadith_en(arabic_text):
    system = "You are an expert translator of Islamic Hadith literature. Translate the Arabic hadith into clear, scholarly English. Output ONLY the English translation - no Arabic, no explanations, no notes."
    prompt = f"Translate this Arabic hadith into English:\n\n{arabic_text}"
    return call_llm(system, prompt)

def translate_commentary_ar(urdu_text):
    system = "You are an expert Islamic translator. Translate the Urdu commentary of Imam al-Bayhaqi / Imam al-Shafi'i into classical Arabic. Output ONLY the Arabic translation, nothing else."
    prompt = f"Translate this Urdu text into Arabic:\n\n{urdu_text}"
    return call_llm(system, prompt)

def fix_bayhaqi_9027():
    print("Fixing Bayhaqi Hadith 9027 EMPTY_ARABIC...")
    path = "/home/saboor/code/hadith-api-toon/editions/bayhaqi/sections/8.toon"
    if not os.path.exists(path):
        print("Bayhaqi section 8 not found")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split('\n')
    header = lines[0]
    rows = []
    reader = csv.reader(lines[1:])
    
    updated = False
    for row in reader:
        if not row:
            continue
        if row[0] == "9027":
            # Translate Urdu to Arabic
            # Urdu text is in row[6] (chapter_intro)
            urdu_text = row[6].strip()
            print(f"  Translating Urdu: {urdu_text[:100]}...")
            arabic_text = translate_commentary_ar(urdu_text)
            if arabic_text:
                row[1] = arabic_text
                updated = True
                print(f"  Translated Arabic: {arabic_text[:100]}...")
            else:
                print("  Failed to translate Arabic")
        rows.append(row)
        
    if updated:
        new_content = [header]
        for r in rows:
            import io
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator='')
            w.writerow(r)
            new_content.append(buf.getvalue())
            
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_content) + "\n")
        print("Successfully updated Bayhaqi Hadith 9027 Arabic.")

def fix_fatah_alrabani_en():
    print("\nTranslating Fatah al-Rabani placeholders to English...")
    base_dir = "/home/saboor/code/hadith-api-toon/editions/fatah-alrabani"
    sections_dir = os.path.join(base_dir, "sections")
    
    # 1. Gather all Arabic texts mapped by hadith number
    hadith_arabic = {}
    for sec_file in sorted(os.listdir(sections_dir)):
        if not sec_file.endswith(".toon"):
            continue
        path = os.path.join(sections_dir, sec_file)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().split('\n')
        reader = csv.reader(lines[1:])
        for row in reader:
            if row:
                hadith_arabic[row[0]] = row[1].strip()
                
    print(f"Gathered {len(hadith_arabic)} Arabic texts from fatah-alrabani sections.")
    
    # 2. Translate and write english translations for sections 1.toon, 2.toon, 3.toon
    en_sections_dir = os.path.join(base_dir, "translations", "en", "sections")
    for sec_file in sorted(os.listdir(sections_dir)):
        if not sec_file.endswith(".toon"):
            continue
            
        main_sec_path = os.path.join(sections_dir, sec_file)
        with open(main_sec_path, "r", encoding="utf-8") as f:
            main_lines = f.read().split('\n')
            
        hns = []
        reader = csv.reader(main_lines[1:])
        for row in reader:
            if row:
                hns.append(row[0])
                
        # Re-build English translation slice
        header = f"hadiths[{len(hns)}]{{hadithnumber,text}}:"
        new_lines = [header]
        
        for hn in hns:
            ar_text = hadith_arabic.get(hn, "")
            if ar_text:
                print(f"  Translating Fatah al-Rabani Hadith {hn}...", end=' ', flush=True)
                en_text = translate_hadith_en(ar_text)
                if en_text:
                    print("OK")
                else:
                    en_text = f"Fatah Al-Rabani Hadith {hn}"
                    print("FAILED")
            else:
                en_text = f"Fatah Al-Rabani Hadith {hn}"
                print(f"  Hadith {hn} has no Arabic to translate")
                
            # Write to buffer
            import io
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator='')
            w.writerow([hn, en_text])
            new_lines.append(buf.getvalue())
            
        en_sec_path = os.path.join(en_sections_dir, sec_file)
        with open(en_sec_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
        print(f"Wrote translation slice: en/sections/{sec_file}")

def main():
    fix_bayhaqi_9027()
    fix_fatah_alrabani_en()

if __name__ == "__main__":
    main()
