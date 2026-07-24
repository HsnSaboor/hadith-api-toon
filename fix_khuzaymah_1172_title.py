#!/usr/bin/env python3
"""Give chapter id=1172 in sahih-ibn-khuzaymah (916 hadiths, 1748-2663,
spanning end-of-Fasting + all of Zakah + all of Hajj/Umrah) an honest
multi-topic Arabic title, then translate into all 13 languages.

This chapter was previously blank because it represents a data-collapse
where the fine-grained sub-chapter boundaries were lost during original
digitization. Verified against hadithunlocked.com that a precise
sub-chapter split is not safely reconstructable (their own source data
has internally inconsistent/overlapping section boundaries in this exact
region - reflecting genuine complexity in the surviving Ibn Khuzaymah
manuscript, not a scraping bug). So instead of guessing at ~127 sub-chapter
boundaries, this gives the chapter one accurate composite title reflecting
its real span (based on Ibn Khuzaymah's own book-level headings: كتاب
الصيام / كتاب الزكاة / كتاب المناسك, which we already have correct
translations for elsewhere in this book).
"""
import re, csv, io, os, json, time, requests, concurrent.futures

ED = "/home/saboor/code/hadith-api-toon/editions/sahih-ibn-khuzaymah"
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
CACHE_PATH = "/home/saboor/code/hadith-api-toon/fix_khuzaymah_1172_title_cache.json"

LANG_NAMES = {
    'bn': 'Bengali', 'fr': 'French', 'id': 'Indonesian', 'ru': 'Russian',
    'tr': 'Turkish', 'ur': 'Urdu', 'hi': 'Hindi', 'ta': 'Tamil',
    'roman-ur': 'Roman Urdu (Urdu written in Latin script)',
    'de': 'German', 'es': 'Spanish', 'en': 'English',
}

CHAPTER_ID = '1172'
ARABIC_TITLE = 'بَقِيَّةُ كِتَابِ الصِّيَامِ، وَكِتَابُ الزَّكَاةِ، وَكِتَابُ الْمَنَاسِكِ (الْحَجِّ وَالْعُمْرَةِ)'


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


def translate_title(arabic_title, lang):
    lang_name = LANG_NAMES.get(lang, lang)
    prompt = (
        f"Translate this classical Islamic hadith book chapter title "
        f"(a composite/combined heading covering the remainder of the "
        f"Book of Fasting, the entire Book of Zakah, and the entire Book "
        f"of Pilgrimage Rites in Sahih Ibn Khuzaymah) into {lang_name}. "
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

    tasks = [lang for lang in LANG_NAMES if lang not in cache or not cache[lang].strip()]
    print(f"Translation tasks: {len(tasks)}", flush=True)

    def do_task(lang):
        result = translate_title(ARABIC_TITLE, lang)
        return lang, result or ''

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(do_task, lang): lang for lang in tasks}
        for future in concurrent.futures.as_completed(futures):
            lang, result = future.result()
            cache[lang] = result
            print(f"  {lang}: {result[:60]}", flush=True)
            with open(CACHE_PATH, 'w') as f:
                json.dump(cache, f, ensure_ascii=False)

    lines, header_idx, fields, rows, row_line_indices = load_sections()
    rows_by_id = {row[0]: row for row in rows}
    row = rows_by_id.get(CHAPTER_ID)
    if not row:
        print(f"ERROR: chapter id {CHAPTER_ID} not found")
        return

    name_idx = fields.index('name')
    ar_idx = fields.index('name_ar')
    row[name_idx] = ARABIC_TITLE
    row[ar_idx] = ARABIC_TITLE

    for lang, translated in cache.items():
        if lang == 'en':
            field = 'name_en'
        else:
            field = f'name_{lang}'
        if field not in fields or not translated.strip():
            continue
        lang_idx = fields.index(field)
        row[lang_idx] = translated.strip()

    for row, line_idx in zip(rows, row_line_indices):
        escaped = [escape_toon_field(v) for v in row]
        lines[line_idx] = ','.join(escaped)
    new_text = '\n'.join(lines)
    with open(f"{ED}/info.toon", 'w') as f:
        f.write(new_text)
    print(f"\n[sahih-ibn-khuzaymah] info.toon updated for chapter {CHAPTER_ID}", flush=True)


if __name__ == '__main__':
    main()
