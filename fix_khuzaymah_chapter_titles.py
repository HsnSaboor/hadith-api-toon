#!/usr/bin/env python3
"""Fix sahih-ibn-khuzaymah's corrupted/missing chapter titles for the
neighborhood around hadith 1727-2663:

1. 13 chapters (ids 1156-1171, excluding 1164/1170 already empty) have
   Urdu text with a number-prefix incorrectly stored in name/name_ar
   (and even name_en is a translation of the Urdu, not a real title).
   Fix: derive a proper Ibn-Khuzaymah-style Arabic chapter title from the
   full Arabic hadith text of that chapter via LLM, then translate into
   all 12 other languages.

2. 2 chapters (ids 1164, 1170) are completely blank (single orphaned
   hadiths with no title at all). Same fix as above.

3. Chapter id=1172 (916 hadiths, hadith 1748-2663) is a massive collapsed
   range with no title, confirmed via hadithunlocked.com to hide ~127 real
   Ibn Khuzaymah sub-chapters covering the end of Fasting, all of Zakah,
   and all of Hajj. This is handled separately in a follow-up script
   (requires restructuring sections[], not just filling a title).
"""
import re, csv, io, os, json, time, requests, concurrent.futures

ED = "/home/saboor/code/hadith-api-toon/editions/sahih-ibn-khuzaymah"
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 6
CACHE_PATH = "/home/saboor/code/hadith-api-toon/fix_khuzaymah_chapter_titles_cache.json"

LANG_NAMES = {
    'bn': 'Bengali', 'fr': 'French', 'id': 'Indonesian', 'ru': 'Russian',
    'tr': 'Turkish', 'ur': 'Urdu', 'hi': 'Hindi', 'ta': 'Tamil',
    'roman-ur': 'Roman Urdu (Urdu written in Latin script)',
    'de': 'German', 'es': 'Spanish', 'en': 'English',
}

# Chapters needing a fresh Arabic title derived from their hadith content
# (13 corrupted-Urdu + 2 blank = 15 total; excludes 1172 which is handled
# separately due to its scale).
TARGET_CHAPTER_IDS = ['1156', '1157', '1158', '1159', '1160', '1161', '1162',
                       '1163', '1164', '1165', '1167', '1168', '1169', '1170', '1171']


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


def load_chapter_hadiths(chapter_id):
    path = f"{ED}/sections/{chapter_id}.toon"
    with open(path, errors='replace') as f:
        text = f.read()
    r = csv.reader(io.StringIO(text))
    next(r)
    rows = list(r)
    return [row[1] for row in rows if len(row) >= 2]


def derive_arabic_title(chapter_id, hadith_texts):
    joined = '\n\n---\n\n'.join(hadith_texts)
    prompt = (
        "This is one or more hadiths from a chapter of Sahih Ibn Khuzaymah "
        "(a classical hadith collection known for long, descriptive Arabic "
        "chapter titles starting with 'بَابُ' or 'جُمَّاعُ أَبْوَابِ', "
        "e.g. 'بَابُ ذِكْرِ فَضْلِ الْوُضُوءِ...' or 'بَابُ اسْتِحْبَابِ...'). "
        "Based on the content of the hadith(s) below, write an appropriate "
        "classical Arabic chapter title (bab heading) in the same "
        "distinctive style Ibn Khuzaymah uses elsewhere in his book "
        "(starting with بَابُ or جُمَّاعُ أَبْوَابِ, describing the specific "
        "legal/religious point the hadith establishes). "
        "Output ONLY the Arabic chapter title, nothing else, no notes, no "
        "translation.\n\n"
        f"Hadith(s):\n{joined}"
    )
    return glm_call(prompt)


def translate_title(arabic_title, lang):
    lang_name = LANG_NAMES.get(lang, lang)
    prompt = (
        f"Translate this classical Islamic hadith book chapter title "
        f"(a 'bab' heading from Sahih Ibn Khuzaymah) into {lang_name}. "
        "Output ONLY the translation, no notes, no explanation.\n\n"
        f"Arabic:\n{arabic_title}"
    )
    return glm_call(prompt)


def load_sections():
    info_path = f"{ED}/info.toon"
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
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)
        print(f"Loaded cache with {len(cache)} entries", flush=True)

    # Step 1: derive Arabic titles for each target chapter
    ar_tasks = []
    for cid in TARGET_CHAPTER_IDS:
        key = f"ar||{cid}"
        if key not in cache or not cache[key].strip():
            ar_tasks.append(cid)

    print(f"Arabic title derivation tasks: {len(ar_tasks)}", flush=True)

    def do_ar_task(cid):
        hadiths = load_chapter_hadiths(cid)
        title = derive_arabic_title(cid, hadiths)
        return cid, title or ''

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(do_ar_task, cid): cid for cid in ar_tasks}
        for future in concurrent.futures.as_completed(futures):
            cid, title = future.result()
            cache[f"ar||{cid}"] = title
            print(f"  AR title for {cid}: {title[:60]}", flush=True)
            with open(CACHE_PATH, 'w') as f:
                json.dump(cache, f, ensure_ascii=False)

    # Step 2: translate each derived Arabic title into all languages
    trans_tasks = []
    for cid in TARGET_CHAPTER_IDS:
        ar_title = cache.get(f"ar||{cid}", '')
        if not ar_title.strip():
            continue
        for lang in LANG_NAMES:
            key = f"{lang}||{cid}"
            if key not in cache or not cache[key].strip():
                trans_tasks.append((cid, lang, ar_title))

    print(f"\nTranslation tasks: {len(trans_tasks)}", flush=True)

    def do_trans_task(task):
        cid, lang, ar_title = task
        result = translate_title(ar_title, lang)
        return f"{lang}||{cid}", result or ''

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(do_trans_task, t): t for t in trans_tasks}
        for future in concurrent.futures.as_completed(futures):
            key, result = future.result()
            cache[key] = result
            done += 1
            if done % 10 == 0 or done == len(trans_tasks):
                print(f"  {done}/{len(trans_tasks)}", flush=True)
                with open(CACHE_PATH, 'w') as f:
                    json.dump(cache, f, ensure_ascii=False)

    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, ensure_ascii=False)

    # Step 3: write back into info.toon
    lines, header_idx, fields, rows, row_line_indices = load_sections()
    rows_by_id = {row[0]: row for row in rows}

    name_idx = fields.index('name')
    ar_idx = fields.index('name_ar')

    changed = False
    for cid in TARGET_CHAPTER_IDS:
        row = rows_by_id.get(cid)
        if not row:
            print(f"  WARNING: chapter id {cid} not found in sections[]")
            continue
        ar_title = cache.get(f"ar||{cid}", '')
        if not ar_title.strip():
            continue
        row[name_idx] = ar_title
        row[ar_idx] = ar_title
        changed = True
        for lang in LANG_NAMES:
            if lang == 'en':
                field = 'name_en'
            else:
                field = f'name_{lang}'
            if field not in fields:
                continue
            lang_idx = fields.index(field)
            translated = cache.get(f"{lang}||{cid}", '')
            if translated.strip():
                row[lang_idx] = translated.strip()

    if changed:
        for row, line_idx in zip(rows, row_line_indices):
            escaped = [escape_toon_field(v) for v in row]
            lines[line_idx] = ','.join(escaped)
        new_text = '\n'.join(lines)
        with open(f"{ED}/info.toon", 'w') as f:
            f.write(new_text)
        print(f"\n[sahih-ibn-khuzaymah] info.toon updated", flush=True)
    else:
        print("No changes made", flush=True)


if __name__ == '__main__':
    main()
