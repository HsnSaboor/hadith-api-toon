#!/usr/bin/env python3
"""Retry [translation pending] rows left over from fill_hadith_lang.py, using a
smaller batch size per request (helps the model return well-formed [N] output
for the full ID range instead of truncating)."""
import os, re, requests, time, csv, io

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
LANGMAP = {'de': 'German', 'es': 'Spanish'}

TARGETS = [
    ('nawawi', 'de', '1.toon'),
    ('nawawi', 'es', '1.toon'),
    ('fath-al-rabbani', 'de', '2.toon'),
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


def glm_call(prompt, retries=5):
    for attempt in range(retries):
        try:
            r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=300)
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


def translate_single(text, target):
    prompt = (
        f"Translate this single hadith into {target}. Faithful hadith register, no commentary, "
        f"no preface. Preserve proper-name transliteration. Use typographic curly quotes for quoted "
        f"speech, never straight double-quotes. Output ONLY the translation, nothing else.\n\n{text}"
    )
    return glm_call(prompt)


for ed, lang, fn in TARGETS:
    en_path = f'{ED}/{ed}/translations/en/sections/{fn}'
    out_path = f'{ED}/{ed}/translations/{lang}/sections/{fn}'

    en_text = open(en_path, encoding='utf-8', errors='replace').read()
    en_rows = {}
    for ln in en_text.split('\n')[1:]:
        if not ln.startswith('"'):
            continue
        try:
            parsed = list(csv.reader(io.StringIO(ln)))[0]
        except Exception:
            continue
        if len(parsed) >= 2:
            en_rows[parsed[0]] = parsed[1]

    out_text = open(out_path, encoding='utf-8', errors='replace').read()
    out_lines = out_text.split('\n')
    hdr = out_lines[0]

    fixed = 0
    total_pending = 0
    for i, ln in enumerate(out_lines[1:], start=1):
        if not ln.startswith('"'):
            continue
        try:
            parsed = list(csv.reader(io.StringIO(ln)))[0]
        except Exception:
            continue
        if len(parsed) < 2:
            continue
        hn, val = parsed[0], parsed[1]
        if '[translation pending]' not in val:
            continue
        total_pending += 1
        src = en_rows.get(hn)
        if not src:
            continue
        translated = translate_single(src, LANGMAP[lang])
        if not translated:
            continue
        val_full = translated if translated.startswith('[AI-translation]') else '[AI-translation] ' + translated
        val_esc = escape_for_toon(val_full)
        if '\n' in val_esc.replace('\\n', ''):
            continue
        new_line = f'"{escape_for_toon(hn)}","{val_esc}"'
        try:
            parsed_check = list(csv.reader(io.StringIO(new_line)))[0]
            if len(parsed_check) != 2:
                continue
        except Exception:
            continue
        out_lines[i] = new_line
        fixed += 1

    open(out_path, 'w', encoding='utf-8').write('\n'.join(out_lines))
    print(f'{ed}/{lang}/{fn}: fixed {fixed}/{total_pending} pending', flush=True)

print('RETRY DONE', flush=True)
