#!/usr/bin/env python3
"""LLM-translate remaining small gaps (empty/missing EN) across multiple
books: bukhari, muslim, tirmidhi, malik, sunan-darimi, sunan-al-daraqutni,
abudawud, nasai. These are residual isolated hadiths/narrator-chain notes
with no existing EN translation.
"""
import os, requests, concurrent.futures, time, csv, io, json

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 8
OUT_CACHE = '/home/saboor/code/hadith-api-toon/llm_translate_small_gaps_cache.json'

BOOKS = ['bukhari', 'muslim', 'tirmidhi', 'malik', 'sunan-darimi',
         'sunan-al-daraqutni', 'abudawud', 'nasai']

BOOK_STYLE = {
    'bukhari': "Sahih al-Bukhari (Muhsin Khan style: \"Narrated X: ...\")",
    'muslim': "Sahih Muslim (standard sunnah.com style)",
    'tirmidhi': "Jami at-Tirmidhi (standard sunnah.com style)",
    'malik': "Muwatta Malik (standard sunnah.com style)",
    'sunan-darimi': "Sunan ad-Darimi (standard sunnah.com style)",
    'sunan-al-daraqutni': "Sunan al-Daraqutni (standard sunnah.com style)",
    'abudawud': "Sunan Abi Dawud (standard sunnah.com style)",
    'nasai': "Sunan an-Nasai (standard sunnah.com style)",
}


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


def build_prompt(book, arabic_text):
    style = BOOK_STYLE.get(book, "standard sunnah.com style")
    return (
        f"Translate this hadith or hadith-continuation-note from {style} "
        "into English. If it starts with a connecting phrase like "
        "\"and that...\" or \"and X said...\" (continuing a previous "
        "narrator's report), translate it as such a continuation. "
        "Output ONLY the English translation text, no notes, no quotation "
        "marks wrapping the whole thing, no explanation.\n\n"
        f"Arabic:\n{arabic_text}"
    )


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def get_bad_entries(book):
    ar_dir = f'{ED}/{book}/sections'
    en_dir = f'{ED}/{book}/translations/en/sections'
    bad = []
    for fn in sorted(os.listdir(ar_dir)):
        if not fn.endswith('.toon'):
            continue
        sid = fn.replace('.toon', '')
        with open(f'{ar_dir}/{fn}', errors='replace') as f:
            ar_text = f.read()
        try:
            ar_r = csv.reader(io.StringIO(ar_text))
            next(ar_r)
            ar_rows = {row[0]: row[1] for row in ar_r if len(row) >= 2}
        except Exception:
            continue
        en_path = f'{en_dir}/{fn}'
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
                bad.append((sid, hn, ar))
    return bad


def main():
    all_bad = {}
    for book in BOOKS:
        bad = get_bad_entries(book)
        all_bad[book] = bad
        print(f"{book}: {len(bad)} bad entries", flush=True)

    cache = {}
    if os.path.exists(OUT_CACHE):
        with open(OUT_CACHE) as f:
            cache = json.load(f)
        print(f"Loaded cache with {len(cache)} done", flush=True)

    # Build task list: key = f"{book}||{hn}" to avoid cross-book collisions
    tasks = []
    for book, bad in all_bad.items():
        for sid, hn, ar in bad:
            key = f"{book}||{hn}"
            if key not in cache or not cache[key].strip():
                tasks.append((book, sid, hn, ar, key))

    print(f"\nTotal tasks to translate: {len(tasks)}", flush=True)

    def translate_one(task):
        book, sid, hn, ar, key = task
        prompt = build_prompt(book, ar)
        result = glm_call(prompt)
        return key, result or ''

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(translate_one, t): t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            key, text = future.result()
            cache[key] = text
            done += 1
            if done % 10 == 0 or done == len(tasks):
                print(f"  {done}/{len(tasks)}", flush=True)
                with open(OUT_CACHE, 'w') as f:
                    json.dump(cache, f, ensure_ascii=False)

    with open(OUT_CACHE, 'w') as f:
        json.dump(cache, f, ensure_ascii=False)

    failed = [t for t in tasks if not cache.get(t[4], '').strip()]
    print(f"\nDone. Failed: {len(failed)}", flush=True)

    # Write back per book/section
    for book, bad in all_bad.items():
        by_section = {}
        for sid, hn, ar in bad:
            by_section.setdefault(sid, []).append(hn)

        ar_dir = f'{ED}/{book}/sections'
        en_dir = f'{ED}/{book}/translations/en/sections'
        written = 0
        for sid, hns in by_section.items():
            fn = f"{sid}.toon"
            en_path = f"{en_dir}/{fn}"
            existing_rows = []
            existing_keys = set()
            if os.path.exists(en_path):
                with open(en_path, errors='replace') as f:
                    en_text = f.read()
                try:
                    r = csv.reader(io.StringIO(en_text))
                    next(r)
                    existing_rows = list(r)
                    existing_keys = {row[0] for row in existing_rows if row}
                except Exception:
                    pass

            new_rows = []
            for row in existing_rows:
                hn = row[0]
                key = f"{book}||{hn}"
                if hn in hns and key in cache and cache[key].strip():
                    new_rows.append([hn, cache[key]])
                    written += 1
                else:
                    new_rows.append(row)

            for hn in hns:
                if hn not in existing_keys:
                    key = f"{book}||{hn}"
                    if key in cache and cache[key].strip():
                        new_rows.append([hn, cache[key]])
                        written += 1

            with open(f"{ar_dir}/{fn}", errors='replace') as f:
                ar_text = f.read()
            ar_r = csv.reader(io.StringIO(ar_text))
            next(ar_r)
            ar_count = sum(1 for row in ar_r if len(row) >= 2)

            lines = [f'"hadiths[{ar_count}]{{hadithnumber,text}}:"']
            for row in new_rows:
                key_field = escape_toon_field(row[0]) if ',' in row[0] else row[0]
                lines.append(f"{key_field},{escape_toon_field(row[1])}")
            with open(en_path, 'w') as f:
                f.write('\n'.join(lines) + '\n')

        print(f"[{book}] wrote {written} entries", flush=True)


if __name__ == '__main__':
    main()
