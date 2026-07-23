#!/usr/bin/env python3
"""LLM-translate the final 2 confirmed content-mismatch hadiths:
- bayhaqi H#3845 (EN was a duplicate of H#3846's content)
- bulugh-al-maram H#774 (EN was completely unrelated content - Ibn Umar's
  wage hadith had 'Aisha's Tawaf translation instead)

Also apply the confirmed nasai H#302/H#303 swap.
"""
import os, requests, time, csv, io, json

GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
ED = "/home/saboor/code/hadith-api-toon/editions"


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


def escape_toon_field(val):
    val = val.replace('"', '""')
    return f'"{val}"'


def get_ar(book, sid, hn):
    with open(f"{ED}/{book}/sections/{sid}.toon", errors='replace') as f:
        text = f.read()
    r = csv.reader(io.StringIO(text))
    next(r)
    rows = {row[0]: row[1] for row in r if len(row) >= 2}
    return rows.get(hn, '')


def set_en(book, sid, hn, new_text):
    en_path = f"{ED}/{book}/translations/en/sections/{sid}.toon"
    with open(en_path, errors='replace') as f:
        text = f.read()
    r = csv.reader(io.StringIO(text))
    header = next(r)
    rows = list(r)
    found = False
    for row in rows:
        if row[0] == hn:
            row[1] = new_text
            found = True
            break
    if not found:
        rows.append([hn, new_text])

    with open(f"{ED}/{book}/sections/{sid}.toon", errors='replace') as f:
        ar_text = f.read()
    ar_r = csv.reader(io.StringIO(ar_text))
    next(ar_r)
    ar_count = sum(1 for row in ar_r if len(row) >= 2)

    lines = [f'"hadiths[{ar_count}]{{hadithnumber,text}}:"']
    for row in rows:
        key_field = escape_toon_field(row[0]) if ',' in row[0] else row[0]
        lines.append(f"{key_field},{escape_toon_field(row[1])}")
    with open(en_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"  Updated {book}/{sid} H#{hn}")


def swap_en(book, sid, hn_a, hn_b):
    en_path = f"{ED}/{book}/translations/en/sections/{sid}.toon"
    with open(en_path, errors='replace') as f:
        text = f.read()
    r = csv.reader(io.StringIO(text))
    header = next(r)
    rows = list(r)
    idx_a = idx_b = None
    for i, row in enumerate(rows):
        if row[0] == hn_a:
            idx_a = i
        elif row[0] == hn_b:
            idx_b = i
    if idx_a is None or idx_b is None:
        print(f"  FAILED swap {book}/{sid}: {hn_a} idx={idx_a}, {hn_b} idx={idx_b}")
        return
    rows[idx_a][1], rows[idx_b][1] = rows[idx_b][1], rows[idx_a][1]

    with open(f"{ED}/{book}/sections/{sid}.toon", errors='replace') as f:
        ar_text = f.read()
    ar_r = csv.reader(io.StringIO(ar_text))
    next(ar_r)
    ar_count = sum(1 for row in ar_r if len(row) >= 2)

    lines = [f'"hadiths[{ar_count}]{{hadithnumber,text}}:"']
    for row in rows:
        key_field = escape_toon_field(row[0]) if ',' in row[0] else row[0]
        lines.append(f"{key_field},{escape_toon_field(row[1])}")
    with open(en_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"  Swapped {book}/{sid} H#{hn_a} <-> H#{hn_b}")


def main():
    # 1. nasai swap
    swap_en('nasai', '1', '302', '303')

    # 2. bayhaqi H#3845 - LLM translate from its own Arabic
    ar = get_ar('bayhaqi', '4', '3845')
    prompt = (
        "Translate this hadith from As-Sunan al-Kubra by al-Bayhaqi into "
        "English in a formal academic style (narrator chain followed by "
        "the hadith text), matching the style: \"X informed us: Y narrated "
        "to us...\" Output ONLY the English translation, no notes.\n\n"
        f"Arabic:\n{ar}"
    )
    result = glm_call(prompt)
    if result:
        set_en('bayhaqi', '4', '3845', result)
    else:
        print("  FAILED to translate bayhaqi 3845")

    # 3. bulugh-al-maram H#774 - LLM translate from its own Arabic
    ar = get_ar('bulugh-al-maram', '7', '774')
    prompt = (
        "Translate this hadith from Bulugh al-Maram into English in the "
        "standard translation style (e.g. \"Ibn 'Umar (RAA) narrated that "
        "the Messenger of Allah (ﷺ) said...\"). Include the narrator "
        "attribution at the end (e.g. 'Related by Ibn Majah') if present "
        "in the Arabic. Output ONLY the English translation, no notes.\n\n"
        f"Arabic:\n{ar}"
    )
    result = glm_call(prompt)
    if result:
        set_en('bulugh-al-maram', '7', '774', result)
    else:
        print("  FAILED to translate bulugh-al-maram 774")


if __name__ == '__main__':
    main()
