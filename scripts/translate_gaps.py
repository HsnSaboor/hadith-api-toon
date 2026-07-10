#!/usr/bin/env python3
import os, sys, re, csv, io, requests, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

BASE = "/home/saboor/code/hadith-api-toon"
EDITIONS = os.path.join(BASE, "editions")

sys.path.append(os.path.join(BASE, "scripts"))
from audit_1000_deep import parse_info, read_toon_rows

KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]

LANG_PROFILES = {
    "en": "English",
    "ur": "Urdu",
    "id": "Indonesian",
    "bn": "Bengali",
    "tr": "Turkish",
    "fr": "French",
    "hi": "Hindi (Devanagari script)",
    "ru": "Russian",
    "ta": "Tamil",
    "roman-ur": "Roman Urdu"
}

SYSTEM_PROMPT_TPL = """You are an expert Islamic translator. Your ONLY task is to translate hadith text into {target_lang}.

Rules:
1. Output ONLY translations in {target_lang}. Do NOT output Arabic text. Do NOT output English text (unless target is English).
2. Each translation MUST start with [N] where N is the index number, e.g. [1], [2], etc.
3. Do NOT use markdown headers, bold, or any formatting. Just [N] followed by the translation text.
4. Do NOT add introductions, notes, or explanations.
5. Preserve Islamic terms (Salah, Wudu) and honorifics (ﷺ, رضي الله عنه).
6. Translate ALL entries. Do not skip any.

Example output format:
[1] Translation of first hadith in {target_lang}
[2] Translation of second hadith in {target_lang}"""

print_lock = Lock()

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)

LOCAL_MODELS = ["nemotron-3-ultra-free", "hy3-free", "deepseek-v4-flash-free"]

def call_local_api(system_prompt, user_prompt):
    # Try each local model
    for model in LOCAL_MODELS:
        for attempt in range(2):
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1
                }
                # Timeout increased to 600s to allow deep reasoning on batch size 20
                resp = requests.post("http://localhost:8080/v1/chat/completions", json=payload, timeout=600)
                if resp.status_code == 200:
                    result = resp.json()
                    choices = result.get("choices", [])
                    if choices and len(choices) > 0:
                        text = choices[0].get("message", {}).get("content", "").strip()
                        if text:
                            safe_print(f"      [Local API {model}] Success on attempt {attempt+1}")
                            return text
                        else:
                            safe_print(f"      [Local API {model} Attempt {attempt+1}] Empty content in response")
                    else:
                        safe_print(f"      [Local API {model} Attempt {attempt+1}] No choices in response: {str(result)[:200]}")
                else:
                    safe_print(f"      [Local API {model} Attempt {attempt+1}] Failed: HTTP {resp.status_code} - {resp.text[:200]}")
            except Exception as e:
                safe_print(f"      [Local API {model} Attempt {attempt+1}] Exception: {e}")
            time.sleep(3)
    return None

def call_openrouter_api(task_idx, system_prompt, user_prompt):
    num_keys = len(KEYS)
    for step in range(num_keys):
        key_idx = (task_idx + step) % num_keys
        key = KEYS[key_idx]
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/HsnSaboor/hadith-api-toon",
                "X-Title": "Hadith API Translation Fixer"
            }
            payload = {
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1
            }
            # Timeout increased to 600s
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=600)
            if resp.status_code == 200:
                result = resp.json()
                choices = result.get("choices", [])
                if choices and len(choices) > 0:
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if text:
                        safe_print(f"      [OpenRouter Key {key_idx}] Success")
                        return text
                    else:
                        safe_print(f"      [OpenRouter Key {key_idx}] Empty content")
                else:
                    safe_print(f"      [OpenRouter Key {key_idx}] No choices: {str(result)[:200]}")
            else:
                safe_print(f"      [OpenRouter Key {key_idx}] Failed: HTTP {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            safe_print(f"      [OpenRouter Key {key_idx}] Exception: {e}")
        time.sleep(2)
    return None

# Languages that use Arabic script (so Arabic char filter must be skipped)
ARABIC_SCRIPT_LANGS = {"ur", "ar", "fa", "ps", "ks", "sd"}

def parse_batch_results(content, batch, lang=""):
    results = {}
    # Build map of idx -> hadithnumber
    idx_map = {item["idx"]: item["hadithnumber"] for item in batch}
    skip_arabic_filter = lang in ARABIC_SCRIPT_LANGS
    
    # Try multiple patterns to match different LLM output formats
    patterns = [
        # [N] text
        r'\[(\d+)\]\s*(.+?)(?=\n\s*\[\d+\]|\Z)',
        # ### **N** or ### N followed by text (skip markdown header line)
        r'###\s*\*{0,2}(\d+)\*{0,2}\s*\n+(.+?)(?=\n###\s*\*{0,2}\d+|\Z)',
        # N. text or N: text  
        r'(?:^|\n)(\d+)[.:\)]\s*(.+?)(?=\n\d+[.:\)]|\Z)',
    ]
    
    for pattern in patterns:
        for m in re.finditer(pattern, content, re.DOTALL):
            idx = int(m.group(1))
            text = m.group(2).strip()
            if idx in idx_map:
                hn = idx_map[idx]
                # Clean outer quotes if any
                if text.startswith('"') and text.endswith('"'):
                    text = text[1:-1].strip()
                # Remove any markdown bold/formatting
                text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text)
                # Skip if text is mostly Arabic (model repeated input instead of translating)
                # But skip this check for Arabic-script languages (Urdu, Persian, etc.)
                if not skip_arabic_filter:
                    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
                    total_chars = max(len(text), 1)
                    if arabic_chars / total_chars >= 0.5:
                        continue
                if text.strip():
                    results[hn] = text.strip()
        if results:
            break  # Use first pattern that produces results
            
    return results

def process_batch(task_idx, batch_info):
    book = batch_info["book"]
    lang = batch_info["lang"]
    batch = batch_info["batch"]
    
    lang_name = LANG_PROFILES.get(lang, lang)
    system_prompt = SYSTEM_PROMPT_TPL.format(target_lang=lang_name)
    
    user_lines = []
    for item in batch:
        idx = item["idx"]
        arabic = item["arabic_text"]
        english = item["english_text"]
        parts = []
        if arabic:
            parts.append(f"Arabic: {arabic}")
        if english:
            parts.append(f"English: {english}")
        user_lines.append(f"[{idx}]\n" + "\n".join(parts))
        
    user_prompt = f"Translate ALL {len(batch)} entries below into {lang_name}. Output ONLY the {lang_name} translation for each, prefixed with [N]. Do NOT output Arabic or English text.\n\n" + "\n\n".join(user_lines)
    
    # Priority 1: Local API (hy3-free)
    safe_print(f"  [{book}/{lang}] Batch of {len(batch)} hadiths: Trying Local 8080...")
    content = call_local_api(system_prompt, user_prompt)
    
    # Fallback to OpenRouter (nemotron-3-ultra-free)
    if not content:
        safe_print(f"  [{book}/{lang}] Local 8080 failed. Falling back to OpenRouter...")
        content = call_openrouter_api(task_idx, system_prompt, user_prompt)
        
    if content:
        safe_print(f"  [{book}/{lang}] Got response ({len(content)} chars). First 500 chars:\n{content[:500]}")
        parsed = parse_batch_results(content, batch, lang=lang)
        if parsed:
            safe_print(f"  [{book}/{lang}] Successfully parsed {len(parsed)}/{len(batch)} translations.")
            return parsed
        else:
            safe_print(f"  [{book}/{lang}] PARSE FAILED! Full response:\n{content[:2000]}")
            
    safe_print(f"  [{book}/{lang}] Failed to translate batch.")
    return {}

def write_toon_file(path, name, fields, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{name}[{len(rows)}]{{{','.join(fields)}}}:\n")
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        for r in rows:
            writer.writerow([r.get(fd, "") for fd in fields])

def main():
    # 1. Identify target books and languages with >= 95% progress
    targets = []
    
    for book in sorted(os.listdir(EDITIONS)):
        bpath = os.path.join(EDITIONS, book)
        info_path = os.path.join(bpath, "info.toon")
        if not os.path.isdir(bpath) or not os.path.exists(info_path):
            continue
        
        meta, translations_block, _ = parse_info(info_path)
        book_id = meta.get("book_id", book)
        
        # Calculate actual total hadiths from sections
        sections_dir = os.path.join(bpath, "sections")
        all_hns = []
        if os.path.isdir(sections_dir):
            for fn in os.listdir(sections_dir):
                if fn.endswith(".toon"):
                    _, _, rows = read_toon_rows(os.path.join(sections_dir, fn))
                    all_hns.extend(r.get("hadithnumber") for r in rows if r.get("hadithnumber"))
        all_hns = set(all_hns)
        total_actual = len(all_hns)
        if total_actual == 0:
            continue
            
        # Get declared translations
        info_langs = sorted(tb.get("language", "") for tb in translations_block if tb.get("language"))
        for lang in info_langs:
            lsec = os.path.join(bpath, "translations", lang, "sections")
            non_empty = 0
            if os.path.isdir(lsec):
                for fn in os.listdir(lsec):
                    if fn.endswith(".toon"):
                        _, _, rows = read_toon_rows(os.path.join(lsec, fn))
                        non_empty += sum(1 for r in rows if r.get("text", "").strip())
            ratio = non_empty / total_actual
            if ratio >= 0.95 and ratio < 1.0:
                targets.append((book, lang, non_empty, total_actual, ratio))
                print(f"Target identified: {book} ({lang}) - Progress: {ratio:.2%} ({non_empty}/{total_actual})")

    print(f"\nFound {len(targets)} books/languages to complete to 100%. Collecting missing entries...")
    
    # 2. Gather all missing/empty translations across all targets
    batches_to_process = []
    
    # We will keep mapping metadata to update files later
    # (book, lang) -> section_file -> (tr_name, tr_fields, ar_rows, tr_map, filename)
    file_registry = {}
    
    for book, lang, _, _, _ in targets:
        bpath = os.path.join(EDITIONS, book)
        sections_dir = os.path.join(bpath, "sections")
        trans_dir = os.path.join(bpath, "translations", lang, "sections")
        os.makedirs(trans_dir, exist_ok=True)
        
        # Load English translation map if available
        en_map = {}
        en_dir = os.path.join(bpath, "translations", "en", "sections")
        if lang != "en" and os.path.isdir(en_dir):
            for fn in os.listdir(en_dir):
                if fn.endswith(".toon"):
                    _, _, rows = read_toon_rows(os.path.join(en_dir, fn))
                    for r in rows:
                        hn = r.get("hadithnumber")
                        txt = r.get("text", "").strip()
                        if hn and txt:
                            en_map[hn] = txt
                            
        book_missing = []
        for fn in sorted(os.listdir(sections_dir), key=lambda x: int(re.sub(r'\D', '', x)) if re.sub(r'\D', '', x) else 0):
            if not fn.endswith(".toon"):
                continue
                
            arabic_file = os.path.join(sections_dir, fn)
            trans_file = os.path.join(trans_dir, fn)
            
            ar_name, ar_fields, ar_rows = read_toon_rows(arabic_file)
            
            tr_rows = []
            tr_name = "hadiths"
            tr_fields = ["hadithnumber", "text"]
            
            if os.path.exists(trans_file):
                tr_name, tr_fields, tr_rows = read_toon_rows(trans_file)
                
            tr_map = {r.get("hadithnumber"): r for r in tr_rows if r.get("hadithnumber")}
            
            # Register the section file details
            file_key = (book, lang, fn)
            file_registry[file_key] = {
                "trans_file_path": trans_file,
                "tr_name": tr_name,
                "tr_fields": tr_fields,
                "ar_rows": ar_rows,
                "tr_map": tr_map
            }
            
            for ar_row in ar_rows:
                hn = ar_row.get("hadithnumber")
                if not hn:
                    continue
                    
                tr_row = tr_map.get(hn)
                tr_text = tr_row.get("text", "").strip() if tr_row else ""
                
                # Check for Arabic copy optimization first
                if not tr_text and lang == "ar":
                    arabic_text = ar_row.get("text", "").strip() or ar_row.get("arabic", "").strip()
                    if tr_row:
                        tr_row["text"] = arabic_text
                    else:
                        new_row = {"hadithnumber": hn, "text": arabic_text}
                        for f in tr_fields:
                            if f not in new_row:
                                new_row[f] = ""
                        tr_rows.append(new_row)
                        tr_map[hn] = new_row
                    continue
                
                if not tr_text:
                    # Find Arabic text
                    arabic_text = ar_row.get("text", "").strip()
                    if not arabic_text:
                        arabic_text = ar_row.get("arabic", "").strip()
                    if not arabic_text:
                        for val in ar_row.values():
                            if val and len(re.findall(r'[\u0600-\u06FF]', val)) > 10:
                                arabic_text = val.strip()
                                break
                                
                    english_text = en_map.get(hn, "").strip()
                    
                    book_missing.append({
                        "hadithnumber": hn,
                        "arabic_text": arabic_text,
                        "english_text": english_text,
                        "file_key": file_key
                    })
                    
        # Split book_missing into batches of 20
        for i in range(0, len(book_missing), 10):
            chunk = book_missing[i:i+10]
            # assign indexes within the chunk starting from 1
            for idx, item in enumerate(chunk):
                item["idx"] = idx + 1
            batches_to_process.append({
                "book": book,
                "lang": lang,
                "batch": chunk
            })
            
    total_batches = len(batches_to_process)
    print(f"\nCollected {total_batches} batches of size 20 to process. Translating concurrently using 8 workers...")
    
    # 3. Translate in parallel (using 8 concurrent workers)
    results_map = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(process_batch, idx, b_info): b_info 
            for idx, b_info in enumerate(batches_to_process)
        }
        
        completed = 0
        for future in as_completed(futures):
            b_info = futures[future]
            batch_results = future.result()
            
            # Group batch results back into file_key mappings
            for item in b_info["batch"]:
                hn = item["hadithnumber"]
                file_key = item["file_key"]
                if hn in batch_results:
                    results_map.setdefault(file_key, {})[hn] = batch_results[hn]
                    
            completed += 1
            if completed % 5 == 0 or completed == total_batches:
                safe_print(f"--- Progress: {completed}/{total_batches} batches finished ---")
                
    # 4. Apply translations and save files
    print("\nApplying translations and writing updated section files...")
    updated_files = 0
    for file_key, trans_results in results_map.items():
        reg = file_registry[file_key]
        trans_file_path = reg["trans_file_path"]
        tr_name = reg["tr_name"]
        tr_fields = reg["tr_fields"]
        ar_rows = reg["ar_rows"]
        tr_map = reg["tr_map"]
        
        for hn, text in trans_results.items():
            if hn in tr_map:
                tr_map[hn]["text"] = text
            else:
                new_row = {"hadithnumber": hn, "text": text}
                for f in tr_fields:
                    if f not in new_row:
                        new_row[f] = ""
                tr_map[hn] = new_row
                
        # Re-build sorted rows conforming to the Arabic structure
        final_rows = []
        for ar_row in ar_rows:
            hn = ar_row.get("hadithnumber")
            if hn in tr_map:
                final_rows.append(tr_map[hn])
            else:
                new_row = {"hadithnumber": hn, "text": ""}
                for f in tr_fields:
                    if f not in new_row:
                        new_row[f] = ""
                final_rows.append(new_row)
                
        write_toon_file(trans_file_path, tr_name, tr_fields, final_rows)
        updated_files += 1
        
    # Also write files that had Arabic copied directly (no LLM call)
    for file_key, reg in file_registry.items():
        if file_key not in results_map:
            trans_file_path = reg["trans_file_path"]
            tr_name = reg["tr_name"]
            tr_fields = reg["tr_fields"]
            ar_rows = reg["ar_rows"]
            tr_map = reg["tr_map"]
            
            final_rows = []
            updated = False
            for ar_row in ar_rows:
                hn = ar_row.get("hadithnumber")
                if hn in tr_map:
                    final_rows.append(tr_map[hn])
                    if tr_map[hn].get("text"):
                        updated = True
                else:
                    new_row = {"hadithnumber": hn, "text": ""}
                    for f in tr_fields:
                        if f not in new_row:
                            new_row[f] = ""
                    final_rows.append(new_row)
            if updated and file_key[1] == "ar":
                write_toon_file(trans_file_path, tr_name, tr_fields, final_rows)
                updated_files += 1
                
    print(f"\nALL TRANSLATIONS COMPLETE! Successfully updated {updated_files} section files.")

if __name__ == "__main__":
    main()
