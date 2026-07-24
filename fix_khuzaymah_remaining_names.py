#!/usr/bin/env python3
"""Fix the small number of remaining empty chapter-name cells in
sahih-ibn-khuzaymah left over after batch translation (a few items per
batch came back empty from the LLM, likely due to numbering drift in the
batch response). Translates each remaining item individually (not batched)
for reliability, skipping the 4 known chapters with genuinely no source
text (id=1163,1164,1170,1172 have empty Arabic/English titles in the
source data itself).
"""
import re, csv, io, os, json, time, requests, concurrent.futures

ED = "/home/saboor/code/hadith-api-toon/editions"
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 6
CACHE_PATH = "/home/saboor/code/hadith-api-toon/fix_khuzaymah_remaining_cache.json"
BOOK = 'sahih-ibn-khuzaymah'

LANG_NAMES = {
    'bn': 'Bengali', 'fr': 'French', 'id': 'Indonesian', 'ru': 'Russian',
    'tr': 'Turkish', 'ur': 'Urdu', 'hi': 'Hindi', 'ta': 'Tamil',
    'roman-ur': 'Roman Urdu (Urdu written in Latin script)',
    'de': 'German', 'es': 'Spanish', 'en': 'English',
}

SKIP_IDS = {'1163', '1164', '1170', '1172'}


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
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=300)
            if r.status_code == 200:
                content = extract_text(r.json()['choices'][0]['message']['content']).strip()
                if len(content) >= 2:
                    return content
            elif r.status_code == 429:
                time.sleep(10)
        except Exception as e:
            print(f"  error: {e}", flush=True)
        time.sleep(3)
    return None


def load_sections():
    info_path = f"{ED}/{BOOK}/info.toon"
    with open(info_path, errors='replace') as f:
        text = f.read()
    lines = text.split('\n')
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^sections\[\d+\]\{[^}]+\}:$', line.strip()):
            header_idx = i
            break
    header_line = lines[header_idx]
    m = re.match(r'^sections\[(\d+)\]\{([^}]+)\}:$', header_line.strip())
    count = int(m.group(1))
    fields = [f.strip() for f in m.group(2).split(',')]

    rows = []
    row_line_indices = []
    li = header_idx + 1
    while len(rows) < count and li < len(lines):
        line = lines[li]
        if not line.strip():
            li += 1
            continue
        row = list(csv.reader(io.StringIO(line)))[0]
        rows.append(row)
        row_line_indices.append(li)
        li += 1

    return lines, header_idx, fields, rows, row_line_indices


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def main():
    lines, header_idx, fields, rows, row_line_indices = load_sections()
    en_idx = fields.index('name_en')
    ar_idx = fields.index('name_ar')

    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)
        print(f"Loaded cache with {len(cache)} entries", flush=True)

    tasks = []
    for lang in ['bn', 'en', 'fr', 'id', 'ru', 'tr', 'ur', 'hi', 'ta', 'roman-ur', 'de', 'es']:
        field = f'name_{lang}'
        if field not in fields:
            continue
        lang_idx = fields.index(field)
        for row in rows:
            cid = row[0]
            if cid in SKIP_IDS:
                continue
            if row[lang_idx].strip():
                continue
            src = row[en_idx].strip() if row[en_idx].strip() else row[ar_idx].strip()
            if not src:
                continue
            key = f"{lang}||{cid}"
            if key not in cache or not cache[key].strip():
                tasks.append((key, lang, cid, src))

    print(f"Total individual tasks to translate: {len(tasks)}", flush=True)

    def translate_one(task):
        key, lang, cid, src = task
        lang_name = LANG_NAMES.get(lang, lang)
        prompt = (
            f"Translate this hadith book chapter title into {lang_name}. "
            f"It's a religious/Islamic chapter heading. Output ONLY the "
            f"translation, no notes, no explanation.\n\n{src}"
        )
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
                with open(CACHE_PATH, 'w') as f:
                    json.dump(cache, f, ensure_ascii=False)

    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, ensure_ascii=False)

    # Write back
    rows_by_id = {row[0]: row for row in rows}
    changed = False
    for key, translated in cache.items():
        if not translated.strip():
            continue
        lang, cid = key.split('||', 1)
        field = f'name_{lang}'
        if field not in fields or cid not in rows_by_id:
            continue
        lang_idx = fields.index(field)
        row = rows_by_id[cid]
        if not row[lang_idx].strip():
            row[lang_idx] = translated.strip()
            changed = True

    if changed:
        for row, line_idx in zip(rows, row_line_indices):
            escaped = [escape_toon_field(v) for v in row]
            lines[line_idx] = ','.join(escaped)
        new_text = '\n'.join(lines)
        with open(f"{ED}/{BOOK}/info.toon", 'w') as f:
            f.write(new_text)
        print(f"[{BOOK}] info.toon updated", flush=True)
    else:
        print("No changes made", flush=True)


if __name__ == '__main__':
    main()
