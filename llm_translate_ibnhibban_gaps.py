#!/usr/bin/env python3
"""LLM-translate ibnhibban's 45 'volume:page'-style keyed hadiths (section 0)
that have no existing English translation and no cross-reference number
available locally. Translates directly from Arabic.
"""
import os, requests, concurrent.futures, time, csv, io, json

ED = '/home/saboor/code/hadith-api-toon/editions/ibnhibban'
AR_DIR = f'{ED}/sections'
EN_DIR = f'{ED}/translations/en/sections'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 8
OUT_CACHE = '/home/saboor/code/hadith-api-toon/llm_translate_ibnhibban_gaps_cache.json'


def extract_text(msg_content):
    if isinstance(msg_content, str):
        return msg_content
    if isinstance(msg_content, list):
        parts = [b.get('text', '') for b in msg_content if isinstance(b, dict) and b.get('type') == 'text']
        return '\n'.join(parts)
    return ''


def glm_call(prompt, retries=5):
    for attempt in range(retries):
        try:
            r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=600)
            if r.status_code == 200:
                content = extract_text(r.json()['choices'][0]['message']['content']).strip()
                if len(content) >= 3:
                    return content
            elif r.status_code == 429:
                time.sleep(10)
        except Exception as e:
            print(f"  error: {e}", flush=True)
        time.sleep(3)
    return None


def build_prompt(arabic_text):
    return (
        "Translate this hadith from Sahih Ibn Hibban into English in the "
        "style of the standard sunnah.com translations (formal, clear, "
        "e.g. \"Narrated Abu Hurayra: The Messenger of Allah said...\"). "
        "Output ONLY the English translation text, no notes, no quotation "
        "marks wrapping the whole thing, no explanation.\n\n"
        f"Arabic:\n{arabic_text}"
    )


def load_missing():
    fn = '0.toon'
    with open(f"{AR_DIR}/{fn}", errors='replace') as f:
        ar_text = f.read()
    ar_r = csv.reader(io.StringIO(ar_text))
    next(ar_r)
    ar_rows = {row[0]: row[1] for row in ar_r if len(row) >= 2}

    en_path = f"{EN_DIR}/{fn}"
    en_rows = {}
    if os.path.exists(en_path):
        with open(en_path, errors='replace') as f:
            en_text = f.read()
        try:
            en_r = csv.reader(io.StringIO(en_text))
            next(en_r)
            en_rows = {row[0]: row[1] for row in en_r if len(row) >= 2}
        except Exception:
            pass

    missing = {}
    for hn, ar in ar_rows.items():
        if hn not in en_rows or not en_rows[hn].strip():
            missing[hn] = ar
    return missing


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def main():
    missing = load_missing()
    print(f"To translate: {len(missing)}", flush=True)

    cache = {}
    if os.path.exists(OUT_CACHE):
        with open(OUT_CACHE) as f:
            cache = json.load(f)
        print(f"Loaded cache with {len(cache)} done", flush=True)

    to_do = [hn for hn in missing if hn not in cache or not cache[hn].strip()]
    print(f"Remaining to translate: {len(to_do)}", flush=True)

    def translate_one(hn):
        ar = missing[hn]
        prompt = build_prompt(ar)
        result = glm_call(prompt)
        return hn, result or ''

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(translate_one, hn): hn for hn in to_do}
        for future in concurrent.futures.as_completed(futures):
            hn, text = future.result()
            cache[hn] = text
            done += 1
            print(f"  {done}/{len(to_do)} - H#{hn}", flush=True)
            with open(OUT_CACHE, 'w') as f:
                json.dump(cache, f, ensure_ascii=False)

    with open(OUT_CACHE, 'w') as f:
        json.dump(cache, f, ensure_ascii=False)

    empty = [hn for hn in missing if not cache.get(hn, '').strip()]
    print(f"\nDone. Empty/failed: {len(empty)}", flush=True)

    fn = '0.toon'
    en_path = f"{EN_DIR}/{fn}"
    with open(en_path, errors='replace') as f:
        en_text = f.read()
    r = csv.reader(io.StringIO(en_text))
    header = next(r)
    rows = list(r)
    existing_keys = {row[0] for row in rows if row}

    written = 0
    for hn in missing:
        if hn in existing_keys:
            continue
        text = cache.get(hn, '')
        if text.strip():
            rows.append([hn, text])
            written += 1

    with open(f"{AR_DIR}/{fn}", errors='replace') as f:
        ar_text = f.read()
    ar_r = csv.reader(io.StringIO(ar_text))
    next(ar_r)
    ar_count = sum(1 for row in ar_r if len(row) >= 2)

    lines = [f'"hadiths[{ar_count}]{{hadithnumber,text}}:"']
    for row in rows:
        lines.append(f"{row[0]},{escape_toon_field(row[1])}")
    with open(en_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Wrote {written} new entries", flush=True)


if __name__ == '__main__':
    main()
