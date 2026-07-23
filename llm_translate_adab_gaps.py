#!/usr/bin/env python3
"""LLM-translate the 149 aladab-almufrad hadiths that couldn't be matched
against sunnah.com (different edition/abbreviated narrator chains, or not
present on sunnah.com at all - see rescrape_adab_en_v4_unmatched.json).

Translates directly from OUR Arabic text (source of truth for what's shown
to users), batched per section file to reduce API calls.
"""
import os, re, requests, concurrent.futures, time, csv, io, json

ED = '/home/saboor/code/hadith-api-toon/editions/aladab-almufrad'
AR_DIR = f'{ED}/sections'
EN_DIR = f'{ED}/translations/en/sections'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 8
UNMATCHED_PATH = '/home/saboor/code/hadith-api-toon/rescrape_adab_en_v4_unmatched.json'
OUT_CACHE = '/home/saboor/code/hadith-api-toon/llm_translate_adab_gaps_cache.json'


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
        "Translate this hadith from Al-Adab Al-Mufrad into English in the style "
        "of the standard Aisha Bewley translation used on sunnah.com (formal, "
        "clear, third person past tense, e.g. \"Abu Hurayra reported that the "
        "Prophet, may Allah bless him and grant him peace, said...\"). "
        "Output ONLY the English translation text, no notes, no quotation "
        "marks wrapping the whole thing, no explanation.\n\n"
        f"Arabic:\n{arabic_text}"
    )


def load_our_hadiths():
    items = {}
    for fn in sorted(os.listdir(AR_DIR)):
        if not fn.endswith('.toon'):
            continue
        with open(f"{AR_DIR}/{fn}") as f:
            text = f.read()
        r = csv.reader(io.StringIO(text))
        next(r)
        for row in r:
            if len(row) >= 2:
                items[row[0]] = row[1]
    return items


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def main():
    with open(UNMATCHED_PATH) as f:
        unmatched = json.load(f)
    print(f"To translate: {len(unmatched)}", flush=True)

    hn_to_ar = load_our_hadiths()

    cache = {}
    if os.path.exists(OUT_CACHE):
        with open(OUT_CACHE) as f:
            cache = json.load(f)
        print(f"Loaded cache with {len(cache)} done", flush=True)

    to_do = [hn for hn in unmatched if hn not in cache or not cache[hn].strip()]
    print(f"Remaining to translate: {len(to_do)}", flush=True)

    def translate_one(hn):
        ar = hn_to_ar.get(hn, '')
        if not ar:
            return hn, ''
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
            if done % 10 == 0:
                print(f"  {done}/{len(to_do)}", flush=True)
                with open(OUT_CACHE, 'w') as f:
                    json.dump(cache, f, ensure_ascii=False)

    with open(OUT_CACHE, 'w') as f:
        json.dump(cache, f, ensure_ascii=False)

    empty = [hn for hn in unmatched if not cache.get(hn, '').strip()]
    print(f"\nDone. Empty/failed: {len(empty)}", flush=True)
    if empty:
        print(f"Failed numbers: {empty}", flush=True)


if __name__ == '__main__':
    main()
