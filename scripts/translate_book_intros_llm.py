#!/usr/bin/env python3
"""Translate missing book intros using OpenRouter API keys."""

import os
import re
import sys
import json
import time
import requests
from collections import OrderedDict

KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]

MODEL = "meta-llama/llama-3-8b-instruct"
BASE_DIR = "/home/saboor/code/hadith-api-toon/editions"

LANG_NAMES = {
    "en": "English",
    "bn": "Bengali",
    "fr": "French",
    "id": "Indonesian",
    "ru": "Russian",
    "ur": "Urdu",
    "ar": "Arabic",
    "tr": "Turkish",
    "hi": "Hindi",
    "ro": "Romanian",
    "de": "German",
    "es": "Spanish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "bs": "Bosnian",
}

key_idx = 0

def translate_text(text, target_name):
    global key_idx
    if not text or not text.strip() or text == "...":
        return ""
    
    prompt = f"Translate this Islamic book description into {target_name}. Output ONLY the translated text, do not include any intro, explanation, quotes, or notes:\n\n{text}"
    system = f"You are a professional translator translating Islamic books from English to {target_name}. Output ONLY the exact translation of the text provided."
    
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
                print(f"  Key {key_idx % len(KEYS)} returned 401. Rotating...")
                key_idx += 1
            elif resp.status_code == 429:
                print("  Rate limited (429). Sleeping...")
                time.sleep(20)
            else:
                print(f"  HTTP {resp.status_code}: {resp.text[:100]}")
                time.sleep(5)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(5)
    return None

def parse_info_toon(content):
    """Parse info.toon to metadata lines and other sections."""
    lines = content.split('\n')
    meta = OrderedDict()
    meta_start = -1
    meta_end = -1
    
    # Locate metadata block
    for i, line in enumerate(lines):
        if line.strip() == "metadata:":
            meta_start = i
            break
            
    if meta_start != -1:
        # Find end of metadata block (first blank line or next table)
        for i in range(meta_start + 1, len(lines)):
            if not lines[i].strip() or 'translations[' in lines[i] or 'sections[' in lines[i]:
                meta_end = i
                break
        if meta_end == -1:
            meta_end = len(lines)
            
        # Parse key-values
        for i in range(meta_start + 1, meta_end):
            l = lines[i].strip()
            if not l:
                continue
            m = re.match(r'^([A-Za-z_]+)\s*:\s*(.*)$', l)
            if m:
                k, v = m.group(1), m.group(2).strip()
                # strip surrounding quotes if any
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                # decode escaped sequences
                v = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
                meta[k] = v
                
    # Extract translation languages list
    langs = []
    for line in lines:
        if line.strip().startswith('"') and ',' in line:
            parts = line.strip().split(',')
            if len(parts) >= 3 and parts[2].strip().strip('"').startswith('translations/'):
                lang = parts[0].strip().strip('"')
                langs.append(lang)
                
    return meta, langs, meta_start, meta_end

def rebuild_metadata_block(meta):
    block = ["metadata:"]
    for k, v in meta.items():
        # Encode value
        v_escaped = v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        block.append(f'  {k}: "{v_escaped}"')
    return "\n".join(block)

def main():
    books = sorted(d for d in os.listdir(BASE_DIR) 
                   if os.path.isdir(os.path.join(BASE_DIR, d)) and 
                   os.path.exists(os.path.join(BASE_DIR, d, 'info.toon')))
                   
    print(f"Found {len(books)} books in editions/")
    
    for book in books:
        path = os.path.join(BASE_DIR, book, "info.toon")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        meta, langs, start, end = parse_info_toon(content)
        if not meta:
            print(f"[{book}] Could not parse metadata block, skipping")
            continue
            
        intro = meta.get('intro', '').strip()
        if not intro or intro == "...":
            print(f"[{book}] No English intro, skipping")
            continue
            
        changed = False
        
        # 1. Check if intro_en is missing or placeholder
        if 'en' in langs and not meta.get('intro_en', '').strip():
            meta['intro_en'] = intro
            changed = True
            print(f"[{book}] Copying intro to intro_en")
            
        # 2. Check other translation intros
        for lang in langs:
            key = f"intro_{lang}"
            if key not in meta or not meta[key].strip() or meta[key] == "...":
                target_name = LANG_NAMES.get(lang, lang.upper())
                print(f"[{book}] Translating intro to {target_name} ({lang})...", end=' ', flush=True)
                translated = translate_text(intro, target_name)
                if translated:
                    meta[key] = translated
                    changed = True
                    print("OK")
                else:
                    print("FAILED")
                    
        if changed:
            # Reconstruct content
            lines = content.split('\n')
            new_block = rebuild_metadata_block(meta)
            # Replace old metadata block
            lines[start:end] = [new_block]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"[{book}] Updated info.toon with translated intros.")
            time.sleep(1)

if __name__ == '__main__':
    main()
