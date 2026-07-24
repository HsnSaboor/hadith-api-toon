#!/usr/bin/env python3
"""Fill missing chapter-name (name_<lang>) translations across all books'
info.toon sections[] blocks. Batches multiple chapter names per LLM call
for efficiency. Uses name_en as translation source when available,
otherwise falls back to the Arabic `name`/`name_ar` field.

Scope (from audit):
  - sahih-ibn-khuzaymah: 1073 chapters x 10 langs (bn,fr,id,ru,tr,hi,ta,
    roman-ur,de,es) - no name_en source, must translate FROM ARABIC and
    also fill name_en itself.
  - musnad-ahmad: ~800-975 chapters x 5 langs (hi,ta,roman-ur,de,es) -
    name_en exists, translate from it.
  - fath-al-rabbani: 3 chapters x 5 langs (bn,fr,id,ru,tr)
  - lulu-wal-marjan: 55 chapters x 5 langs (bn,fr,id,ru,tr)
  - mishkat: 7 chapters x 5 langs (bn,fr,id,ru,tr)
  - bukhari: 6 chapters x 5 langs (bn,fr,id,ru,tr)
  - malik: 1 chapter x 5 langs (bn,fr,id,ru,tr)
"""
import re, csv, io, os, json, time, requests, concurrent.futures

ED = "/home/saboor/code/hadith-api-toon/editions"
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 6
CACHE_PATH = "/home/saboor/code/hadith-api-toon/fill_chapter_name_gaps_cache.json"
BATCH_SIZE = 40

LANG_NAMES = {
    'bn': 'Bengali', 'fr': 'French', 'id': 'Indonesian', 'ru': 'Russian',
    'tr': 'Turkish', 'ur': 'Urdu', 'hi': 'Hindi', 'ta': 'Tamil',
    'roman-ur': 'Roman Urdu (Urdu written in Latin script)',
    'de': 'German', 'es': 'Spanish', 'en': 'English',
}

# (book, [(chapter_id, source_text, list_of_missing_langs), ...])
JOBS = {
    'sahih-ibn-khuzaymah': ['bn', 'fr', 'id', 'ru', 'tr', 'hi', 'ta', 'roman-ur', 'de', 'es', 'en', 'ur'],
    'musnad-ahmad': ['hi', 'ta', 'roman-ur', 'de', 'es'],
    'fath-al-rabbani': ['bn', 'fr', 'id', 'ru', 'tr'],
    'lulu-wal-marjan': ['bn', 'fr', 'id', 'ru', 'tr'],
    'mishkat': ['bn', 'fr', 'id', 'ru', 'tr', 'ur'],
    'bukhari': ['bn', 'fr', 'id', 'ru', 'tr', 'ur'],
    'malik': ['bn', 'fr', 'id', 'ru', 'tr', 'ur'],
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
                if len(content) >= 2:
                    return content
            elif r.status_code == 429:
                time.sleep(10)
        except Exception as e:
            print(f"  error: {e}", flush=True)
        time.sleep(3)
    return None


def load_sections(book):
    """Returns (lines, header_line_idx, fields, rows, row_line_indices).
    Rows are guaranteed single-line (verified: no embedded newlines in any
    section field across all affected books)."""
    info_path = f"{ED}/{book}/info.toon"
    with open(info_path, errors='replace') as f:
        text = f.read()
    lines = text.split('\n')
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^sections\[\d+\]\{[^}]+\}:$', line.strip()):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"No sections header found in {book}")
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
        if len(row) < len(fields):
            raise ValueError(f"{book}: malformed row at line {li}: {line[:100]}")
        rows.append(row)
        row_line_indices.append(li)
        li += 1

    if len(rows) != count:
        raise ValueError(f"{book}: expected {count} rows, got {len(rows)}")

    return lines, header_idx, fields, rows, row_line_indices


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def build_batch_prompt(lang, items):
    lang_name = LANG_NAMES.get(lang, lang)
    lines = []
    for idx, (cid, src) in enumerate(items):
        lines.append(f"{idx+1}. {src}")
    joined = '\n'.join(lines)
    return (
        f"Translate the following numbered list of hadith book chapter titles "
        f"into {lang_name}. These are religious/Islamic chapter headings "
        f"(often starting with 'Chapter:' or being full descriptive sentences "
        f"in Arabic like 'Bab dhikr...'). Preserve the numbering exactly. "
        f"Output ONLY the numbered translated list, one per line, no extra "
        f"commentary, no explanations.\n\n{joined}"
    )


def parse_batch_response(response, expected_count):
    lines = [l.strip() for l in response.split('\n') if l.strip()]
    results = {}
    for line in lines:
        m = re.match(r'^(\d+)[\.\)]\s*(.+)$', line)
        if m:
            idx = int(m.group(1))
            results[idx] = m.group(2).strip()
    return results


def main():
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)
        print(f"Loaded cache with {len(cache)} entries", flush=True)

    all_tasks = []  # (cache_key, book, lang, batch_items)

    for book, langs in JOBS.items():
        lines, header_idx, fields, rows, row_line_indices = load_sections(book)
        en_idx = fields.index('name_en') if 'name_en' in fields else -1
        ar_idx = fields.index('name_ar') if 'name_ar' in fields else (fields.index('name') if 'name' in fields else -1)

        for lang in langs:
            field = f'name_{lang}'
            if field not in fields:
                continue
            lang_idx = fields.index(field)

            missing_items = []
            for row in rows:
                if not row[lang_idx].strip():
                    src = row[en_idx].strip() if en_idx >= 0 and row[en_idx].strip() else row[ar_idx].strip()
                    if src:
                        missing_items.append((row[0], src))

            # batch
            for i in range(0, len(missing_items), BATCH_SIZE):
                batch = missing_items[i:i + BATCH_SIZE]
                cache_key = f"{book}||{lang}||{i}"
                all_tasks.append((cache_key, book, lang, batch))

    print(f"Total batches to process: {len(all_tasks)}", flush=True)

    to_do = [t for t in all_tasks if t[0] not in cache]
    print(f"Remaining batches: {len(to_do)}", flush=True)

    def process_batch(task):
        cache_key, book, lang, batch = task
        prompt = build_batch_prompt(lang, batch)
        response = glm_call(prompt)
        if not response:
            return cache_key, None
        parsed = parse_batch_response(response, len(batch))
        result = {}
        for idx, (cid, src) in enumerate(batch):
            translated = parsed.get(idx + 1, '')
            result[cid] = translated
        return cache_key, result

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(process_batch, t): t for t in to_do}
        for future in concurrent.futures.as_completed(futures):
            cache_key, result = future.result()
            if result is not None:
                cache[cache_key] = result
            done += 1
            print(f"  {done}/{len(to_do)} - {cache_key}", flush=True)
            with open(CACHE_PATH, 'w') as f:
                json.dump(cache, f, ensure_ascii=False)

    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, ensure_ascii=False)

    # Now write back into info.toon files
    for book, langs in JOBS.items():
        lines, header_idx, fields, rows, row_line_indices = load_sections(book)
        rows_by_id = {row[0]: row for row in rows}

        changed = False
        for lang in langs:
            field = f'name_{lang}'
            if field not in fields:
                continue
            lang_idx = fields.index(field)
            for cache_key, result in cache.items():
                if result is None:
                    continue
                parts = cache_key.split('||')
                if len(parts) != 3 or parts[0] != book or parts[1] != lang:
                    continue
                for cid, translated in result.items():
                    if cid in rows_by_id and translated.strip():
                        row = rows_by_id[cid]
                        if not row[lang_idx].strip():
                            row[lang_idx] = translated.strip()
                            changed = True

        if not changed:
            print(f"[{book}] no changes needed", flush=True)
            continue

        # Rewrite only the specific row lines that changed, preserving all
        # other lines in the file exactly as-is.
        for row, line_idx in zip(rows, row_line_indices):
            escaped = [escape_toon_field(v) for v in row]
            lines[line_idx] = ','.join(escaped)

        new_text = '\n'.join(lines)
        with open(f"{ED}/{book}/info.toon", 'w') as f:
            f.write(new_text)
        print(f"[{book}] info.toon updated", flush=True)


if __name__ == '__main__':
    main()
