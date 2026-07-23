#!/usr/bin/env python3
"""LLM-translate the 131 missing lulu-wal-marjan EN hadiths directly from
our own Arabic text. Al-Lulu wal-Marjan is a compilation of hadiths agreed
upon by Bukhari & Muslim, but no reliable cross-reference to hadith numbers
was available locally, so direct translation is used (consistent with the
successful approach for aladab-almufrad's edition-mismatched hadiths).
"""
import os, requests, concurrent.futures, time, csv, io, json

ED = '/home/saboor/code/hadith-api-toon/editions/lulu-wal-marjan'
AR_DIR = f'{ED}/sections'
EN_DIR = f'{ED}/translations/en/sections'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 8
OUT_CACHE = '/home/saboor/code/hadith-api-toon/llm_translate_lulu_gaps_cache.json'


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
        "Translate this hadith from Al-Lulu wal-Marjan (a compilation of "
        "hadiths agreed upon by Sahih al-Bukhari and Sahih Muslim) into "
        "English in the style of the standard Muhsin Khan / sunnah.com "
        "translations (formal, clear, e.g. \"Narrated Abu Sa'id al-Khudri: "
        "The Prophet (ﷺ) forbade...\"). "
        "Output ONLY the English translation text, no notes, no quotation "
        "marks wrapping the whole thing, no explanation.\n\n"
        f"Arabic:\n{arabic_text}"
    )


def load_missing_hadiths():
    items = {}
    for fn in sorted(os.listdir(AR_DIR)):
        if not fn.endswith('.toon'):
            continue
        sid = fn.replace('.toon', '')
        en_path = f"{EN_DIR}/{fn}"
        with open(f"{AR_DIR}/{fn}", errors='replace') as f:
            ar_text = f.read()
        ar_r = csv.reader(io.StringIO(ar_text))
        next(ar_r)
        ar_rows = {row[0]: row[1] for row in ar_r if len(row) >= 2}

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

        for hn, ar in ar_rows.items():
            if hn not in en_rows or not en_rows[hn].strip():
                items[hn] = (sid, ar)
    return items


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def main():
    missing = load_missing_hadiths()
    print(f"To translate: {len(missing)}", flush=True)

    cache = {}
    if os.path.exists(OUT_CACHE):
        with open(OUT_CACHE) as f:
            cache = json.load(f)
        print(f"Loaded cache with {len(cache)} done", flush=True)

    to_do = [hn for hn in missing if hn not in cache or not cache[hn].strip()]
    print(f"Remaining to translate: {len(to_do)}", flush=True)

    def translate_one(hn):
        sid, ar = missing[hn]
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

    empty = [hn for hn in missing if not cache.get(hn, '').strip()]
    print(f"\nDone. Empty/failed: {len(empty)}", flush=True)
    if empty:
        print(f"Failed numbers: {empty}", flush=True)

    # Now write back into section files
    written = 0
    for fn in sorted(os.listdir(AR_DIR)):
        if not fn.endswith('.toon'):
            continue
        sid = fn.replace('.toon', '')
        with open(f"{AR_DIR}/{fn}", errors='replace') as f:
            ar_text = f.read()
        ar_r = csv.reader(io.StringIO(ar_text))
        next(ar_r)
        nums = [row[0] for row in ar_r if len(row) >= 2]

        en_path = f"{EN_DIR}/{fn}"
        existing_en = {}
        if os.path.exists(en_path):
            with open(en_path, errors='replace') as f:
                en_text = f.read()
            try:
                en_r = csv.reader(io.StringIO(en_text))
                next(en_r)
                existing_en = {row[0]: row[1] for row in en_r if len(row) >= 2}
            except Exception:
                pass

        lines = [f'"hadiths[{len(nums)}]{{hadithnumber,text}}:"']
        for n in nums:
            text = existing_en.get(n, '').strip()
            if not text and n in cache:
                text = cache[n]
            lines.append(f"{n},{escape_toon_field(text)}")
        with open(en_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        written += 1

    print(f"Wrote {written} section files", flush=True)


if __name__ == '__main__':
    main()
