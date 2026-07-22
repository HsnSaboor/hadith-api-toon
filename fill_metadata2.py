#!/usr/bin/env python3
"""Fill the remaining 84 intro gaps + 41 chapter-name-field gaps.
Fix vs fill_metadata.py: (1) anchor intro insertion on available_languages: line
(always present, unlike intro fields for zero-intro books), (2) retry each single
lang call up to 3x before giving up (some ru/de/es/roman-ur silently failed once)."""
import os, re, json, requests, concurrent.futures, time

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 3
LANGMAP = {'en':'English','ur':'Urdu','bn':'Bengali','fr':'French','hi':'Hindi','id':'Indonesian',
           'tr':'Turkish','ta':'Tamil','ru':'Russian','roman-ur':'Romanized Urdu','de':'German','es':'Spanish'}

gaps = json.load(open('/tmp/metadata_gaps2.json'))

def extract_text(msg_content):
    """Handle both flat-string (glm) and list-of-blocks (claude: reasoning+text) content formats."""
    if isinstance(msg_content, str):
        return msg_content
    if isinstance(msg_content, list):
        parts = [b.get('text', '') for b in msg_content if isinstance(b, dict) and b.get('type') == 'text']
        return '\n'.join(parts)
    return ''

def glm_call(prompt, retries=4):
    for attempt in range(retries):
        try:
            r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=300)
            if r.status_code == 200:
                content = extract_text(r.json()['choices'][0]['message']['content']).strip()
                content = re.sub(r'^\[?\d+\]?[.)\]]\s*', '', content).strip().strip('*"“”').strip()
                if len(content) >= 3:
                    return content
            elif r.status_code == 429:
                time.sleep(10)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    return None

def get_intro_source(ed):
    t = open(f'{ED}/{ed}/info.toon', encoding='utf-8', errors='replace').read()
    for f in ['intro_en', 'intro']:
        m = re.search(rf'{f}:\s*"(.*?)"', t, re.S)
        if m and len(m.group(1).strip()) > 20:
            return m.group(1)
    bn = re.search(r'book_name:\s*"?([^"\n]+)"?', t)
    if bn:
        return bn.group(1)
    return None

def fill_one_intro(ed, field):
    ip = f'{ED}/{ed}/info.toon'
    t = open(ip, encoding='utf-8', errors='replace').read()
    # re-check still missing (idempotent on resume)
    m = re.search(rf'{field}:\s*"(.*?)"', t, re.S)
    if m and len(m.group(1).strip()) >= 20:
        return f'{ed} {field}: already filled'
    src = get_intro_source(ed)
    if not src:
        return f'{ed} {field}: NO SOURCE'
    lang_code = field.replace('intro_', '') if field != 'intro' else 'en'
    target = LANGMAP.get(lang_code, 'English')
    if len(src) < 50:
        expanded = glm_call(f"Write a brief scholarly introduction (2-3 sentences) in English for the Islamic hadith book titled: {src}")
        if expanded:
            src = expanded
    translated = glm_call(f"Translate this book introduction into {target}. Faithful scholarly register, no commentary, output ONLY the translation:\n\n{src}")
    if not translated:
        return f'{ed} {field}: TRANSLATE FAILED'
    val = translated if translated.startswith('[AI-translation]') else '[AI-translation] ' + translated
    val_esc = val.replace('"', '""')
    t = open(ip, encoding='utf-8', errors='replace').read()
    if re.search(rf'{field}:\s*".*?"', t, re.S):
        t2 = re.sub(rf'{field}:\s*".*?"', f'{field}: "{val_esc}"', t, count=1, flags=re.S)
    else:
        # anchor on available_languages line — always present
        t2 = re.sub(r'(available_languages:\s*"[^"]*")', r'\1\n  ' + f'{field}: "{val_esc}"', t, count=1)
        if t2 == t:
            return f'{ed} {field}: NO ANCHOR FOUND'
    open(ip, 'w', encoding='utf-8').write(t2)
    return f'{ed} {field}: filled'

def fill_one_chapter_lang(ed, lang):
    ip = f'{ED}/{ed}/info.toon'
    t = open(ip, encoding='utf-8', errors='replace').read()
    m = re.search(r'sections\[(\d+)\]\{([^}]+)\}', t)
    if not m:
        return f'{ed} name_{lang}: no sections[] index'
    count = int(m.group(1))
    fields = [f.strip() for f in m.group(2).split(',')]
    new_field = f'name_{lang}'
    if new_field in fields:
        return f'{ed} name_{lang}: already present'
    if 'name_en' not in fields:
        return f'{ed} name_{lang}: no name_en source'
    lines = t.split('\n')
    hdr_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith('sections['):
            hdr_idx = i; break
    if hdr_idx is None:
        return f'{ed} name_{lang}: no header line'
    sections = []
    row_line_idx = []
    for i in range(hdr_idx + 1, len(lines)):
        ln = lines[i].strip()
        if not ln.startswith('"'):
            break
        parts = ln.split('","')
        if len(parts) < len(fields):
            continue
        row = dict(zip(fields, [p.strip('"') for p in parts]))
        if row.get('name_en', '').strip():
            sections.append((row.get('id', ''), row['name_en']))
        row_line_idx.append(i)
    if not sections:
        return f'{ed} name_{lang}: no name_en data'
    target = LANGMAP[lang]
    # batch translate: one call, all sections, [N] format, with retry
    results = {}
    for attempt in range(3):
        batch_lines = [f"[{i+1}] {name}" for i, (sid, name) in enumerate(sections)]
        prompt = (f"Translate each chapter title into {target}. Faithful, concise. "
                  f"For each, output ONLY the translated title preceded by [N] on its own line.\n\n" + "\n\n".join(batch_lines))
        content = None
        for a in range(4):
            try:
                r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                    json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=600)
                if r.status_code == 200:
                    content = extract_text(r.json()['choices'][0]['message']['content'])
                    break
                elif r.status_code == 429:
                    time.sleep(10)
                else:
                    time.sleep(5)
            except Exception:
                time.sleep(5)
        if not content:
            continue
        idx = {i+1: sid for i, (sid, _) in enumerate(sections)}
        chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
        for ch in chunks:
            mm = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
            if mm:
                n = int(mm.group(1)); txt = mm.group(2).strip().strip('*"“”').strip()
                if n in idx and len(txt) >= 1:
                    results[idx[n]] = txt
        if len(results) < len(sections) / 2:
            raw = [l.strip().strip('*"“”').strip() for l in content.split('\n') if l.strip()]
            cleaned = []
            for l in raw:
                l2 = re.sub(r'^\*{0,2}\[?\d+\]?[.)\]]\s*', '', l).strip().strip('*"“”').strip()
                if len(l2) >= 1: cleaned.append(l2)
            for i, (sid, _) in enumerate(sections):
                if i < len(cleaned) and sid not in results:
                    results[sid] = cleaned[i]
        if len(results) >= len(sections) * 0.8:
            break
    if not results:
        return f'{ed} name_{lang}: TRANSLATE FAILED'
    # re-read fresh, apply
    t = open(ip, encoding='utf-8', errors='replace').read()
    lines = t.split('\n')
    m = re.search(r'sections\[(\d+)\]\{([^}]+)\}', t)
    fields = [f.strip() for f in m.group(2).split(',')]
    if new_field in fields:
        return f'{ed} name_{lang}: already present (race)'
    fields.append(new_field)
    for i, ln in enumerate(lines):
        if ln.startswith('sections['):
            lines[i] = f'sections[{count}]{{{",".join(fields)}}}:'
            hdr_idx = i
            break
    for i in range(hdr_idx + 1, len(lines)):
        ln = lines[i].strip()
        if not ln.startswith('"'):
            break
        parts = ln.split('","')
        if len(parts) >= len(fields) - 1:
            sid = parts[0].strip('"')
            val = results.get(sid, '')
            parts.append(val)
            lines[i] = '","'.join(parts)
    open(ip, 'w', encoding='utf-8').write('\n'.join(lines))
    return f'{ed} name_{lang}: filled ({len(results)}/{len(sections)})'

jobs = []
for j in gaps['intros']:
    jobs.append(('intro', j['ed'], j['field']))
for j in gaps['chapters']:
    jobs.append(('chap', j['ed'], j['lang']))

print(f'jobs: {len(jobs)} ({len(gaps["intros"])} intros + {len(gaps["chapters"])} chapter langs), workers={WORKERS}', flush=True)

def run(job):
    typ, ed, x = job
    if typ == 'intro':
        return fill_one_intro(ed, x)
    else:
        return fill_one_chapter_lang(ed, x)

# group chapter jobs by (ed) to avoid concurrent header-append races on same file
from collections import defaultdict
by_ed = defaultdict(list)
for j in jobs:
    by_ed[j[1]].append(j)

def run_ed_group(ed_jobs):
    out = []
    for j in ed_jobs:
        out.append(run(j))
    return out

done = 0
total_eds = len(by_ed)
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(run_ed_group, v): k for k, v in by_ed.items()}
    for f in concurrent.futures.as_completed(futs):
        done += 1
        ed = futs[f]
        try:
            results = f.result()
            for r in results:
                print(f'  [{done}/{total_eds}] {r}', flush=True)
        except Exception as e:
            print(f'  [{done}/{total_eds}] {ed}: ERR {e}', flush=True)
print('ALL DONE', flush=True)
