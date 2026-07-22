#!/usr/bin/env python3
"""Fill missing full hadith-text translations for de/es (small books) mirroring the en/sections
file structure exactly (same filenames, same hadithnumbers per file).
Same escaping lessons as fill_metadata3.py: always escape via escape_for_toon(), verify every
row with csv.reader before trusting it, never write a malformed row.
"""
import os, re, requests, concurrent.futures, time, csv, io

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 10
LANGMAP = {'de': 'German', 'es': 'Spanish'}

JOBS = [
    ('virtues', ['de', 'es']),
    ('nawawi', ['de', 'es']),
    ('dehlawi', ['de', 'es']),
    ('fath-al-rabbani', ['de', 'es']),
]


def extract_text(msg_content):
    if isinstance(msg_content, str):
        return msg_content
    if isinstance(msg_content, list):
        parts = [b.get('text', '') for b in msg_content if isinstance(b, dict) and b.get('type') == 'text']
        return '\n'.join(parts)
    return ''


def escape_for_toon(s):
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = s.replace('"', '""')
    s = s.replace('\n', '\\n')
    return s


def verify_line(ln, expected_fields=2):
    try:
        rows = list(csv.reader(io.StringIO(ln)))
        if not rows:
            return False
        return len(rows[0]) == expected_fields
    except Exception:
        return False


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
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    return None


def parse_en_file(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    lines = text.split('\n')
    hdr = lines[0] if lines else ''
    m = re.match(r'hadiths\[(\d+)\]', hdr)
    count = int(m.group(1)) if m else 0
    rows = []
    for ln in lines[1:]:
        if not ln.startswith('"'):
            continue
        try:
            parsed = list(csv.reader(io.StringIO(ln)))[0]
        except Exception:
            continue
        if len(parsed) >= 2:
            rows.append((parsed[0], parsed[1]))
    return count, rows


def translate_file(ed, lang, fn):
    en_path = f'{ED}/{ed}/translations/en/sections/{fn}'
    count, rows = parse_en_file(en_path)
    if not rows:
        return f'{ed}/{lang}/{fn}: NO ROWS'
    target = LANGMAP[lang]
    batch_lines = [f"[{i + 1}] {text}" for i, (hn, text) in enumerate(rows)]
    prompt = (
        f"Translate each hadith into {target}. Faithful hadith register, no commentary, no preface. "
        f"Preserve proper-name transliteration. Use typographic curly quotes (“ ”) for quoted "
        f"speech, never straight double-quotes (\"). Output ONLY the translation for each item, preceded "
        f"by [N] on its own line, no extra commentary.\n\n" + "\n\n".join(batch_lines)
    )
    content = glm_call(prompt)
    if not content:
        return f'{ed}/{lang}/{fn}: TRANSLATE FAILED'

    idx = {i + 1: hn for i, (hn, _) in enumerate(rows)}
    result_map = {}
    chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
    for ch in chunks:
        mm = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
        if mm:
            n = int(mm.group(1))
            txt = mm.group(2).strip()
            if n in idx and len(txt) >= 1:
                result_map[idx[n]] = txt

    out_lines = [f'hadiths[{count}]{{hadithnumber,text}}:']
    ok = 0
    for hn, _orig_text in rows:
        raw_val = result_map.get(hn, '')
        if raw_val:
            val = raw_val if raw_val.startswith('[AI-translation]') else '[AI-translation] ' + raw_val
            val_esc = escape_for_toon(val)
            hn_esc = escape_for_toon(hn)
            line = f'"{hn_esc}","{val_esc}"'
            if verify_line(line, expected_fields=2) and '\n' in val_esc.replace('\\n', ''):
                line = f'"{hn_esc}","[translation pending]"'
            elif verify_line(line, expected_fields=2):
                ok += 1
            else:
                line = f'"{hn_esc}","[translation pending]"'
        else:
            hn_esc = escape_for_toon(hn)
            line = f'"{hn_esc}","[translation pending]"'
        out_lines.append(line)

    out_dir = f'{ED}/{ed}/translations/{lang}/sections'
    os.makedirs(out_dir, exist_ok=True)
    open(f'{out_dir}/{fn}', 'w', encoding='utf-8').write('\n'.join(out_lines) + '\n')
    return f'{ed}/{lang}/{fn}: {ok}/{len(rows)} filled'


def update_translations_index(ed, langs_added):
    """Rebuild the translations[N]{language,sections,path} block from scratch based on
    what's actually on disk under editions/<ed>/translations/*, so the declared count is
    always correct regardless of what was there before."""
    ip = f'{ED}/{ed}/info.toon'
    t = open(ip, encoding='utf-8', errors='replace').read()
    tr_dir = f'{ED}/{ed}/translations'
    present_langs = sorted(os.listdir(tr_dir))

    rows = []
    for lang in present_langs:
        sec_dir = f'{tr_dir}/{lang}/sections'
        n_files = len([f for f in os.listdir(sec_dir) if f.endswith('.toon')]) if os.path.isdir(sec_dir) else 0
        rows.append(f'"{lang}","{n_files}","translations/{lang}"')

    new_block = f'translations[{len(rows)}]{{language,sections,path}}:\n' + '\n'.join(rows) + '\n'
    t2 = re.sub(
        r'translations\[\d+\]\{[^}]+\}:\n(?:"[^\n]*\n)*',
        new_block,
        t,
        count=1,
    )
    open(ip, 'w', encoding='utf-8').write(t2)


all_file_jobs = []
for ed, langs in JOBS:
    en_dir = f'{ED}/{ed}/translations/en/sections'
    fns = sorted(os.listdir(en_dir))
    for lang in langs:
        for fn in fns:
            all_file_jobs.append((ed, lang, fn))

print(f'file-level jobs: {len(all_file_jobs)}', flush=True)

done = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(translate_file, ed, lang, fn): (ed, lang, fn) for ed, lang, fn in all_file_jobs}
    for f in concurrent.futures.as_completed(futs):
        done += 1
        ed, lang, fn = futs[f]
        try:
            r = f.result()
            print(f'  [{done}/{len(all_file_jobs)}] {r}', flush=True)
        except Exception as e:
            print(f'  [{done}/{len(all_file_jobs)}] {ed}/{lang}/{fn}: ERR {e}', flush=True)

for ed, langs in JOBS:
    update_translations_index(ed, langs)
    print(f'{ed}: translations[] index rebuilt', flush=True)

print('ALL DONE', flush=True)
