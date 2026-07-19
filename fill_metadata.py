#!/usr/bin/env python3
"""Fill missing intros + chapter names for all books x all langs via glm-5-2.
- Intros: translate existing intro_en (or generate from book_name if none) to each missing lang.
- Chapter names: translate existing name_en to each missing name_<lang>, add the field if absent.
Max work per req: all items of a book in one language per call. 3 parallel."""
import os, re, json, requests, concurrent.futures, time

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'databricks-glm/glm-5-2'
WORKERS = 3
LANGS = ['en','ur','bn','fr','hi','id','tr','ta','ru','roman-ur','de','es']
LANGMAP = {'en':'English','ur':'Urdu','bn':'Bengali','fr':'French','hi':'Hindi','id':'Indonesian',
           'tr':'Turkish','ta':'Tamil','ru':'Russian','roman-ur':'Romanized Urdu','de':'German','es':'Spanish'}

def glm_batch(items, target_lang, is_names=False):
    """items: list of (id, source_text). Returns {id: translated}."""
    if not items: return {}
    lines = [f"[{i+1}] {txt}" for i, (idx, txt) in enumerate(items)]
    if is_names:
        prompt = (f"Translate each chapter title into {target_lang}. Faithful, concise. "
                  f"For each, output ONLY the translated title preceded by [N] on its own line.\n\n" + "\n\n".join(lines))
    else:
        prompt = (f"Translate each book introduction into {target_lang}. Faithful scholarly register, no commentary. "
                  f"For each, output ONLY the translation preceded by [N] on its own line.\n\n" + "\n\n".join(lines))
    idx = {i+1: id_ for i, (id_, _) in enumerate(items)}
    for attempt in range(6):
        try:
            r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=600)
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                out = {}
                chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
                for ch in chunks:
                    m = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
                    if m:
                        n = int(m.group(1)); txt = m.group(2).strip().strip('*"“”').strip()
                        if n in idx and len(txt) >= 3:
                            out[idx[n]] = txt
                # fallback line-based if <half
                if len(out) < len(items) / 2:
                    raw = [l.strip().strip('*"“”').strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 3]
                    cleaned = []
                    for l in raw:
                        l2 = re.sub(r'^\*{0,2}\[?\d+\]?[.)\]]\s*', '', l).strip().strip('*"“”').strip()
                        if len(l2) >= 3: cleaned.append(l2)
                    for i, (id_, _) in enumerate(items):
                        if i < len(cleaned) and id_ not in out:
                            out[id_] = cleaned[i]
                if out: return out
            elif r.status_code == 429: time.sleep(10)
            else: time.sleep(5)
        except Exception: time.sleep(5)
    return {}

def get_intro_source(ed):
    t = open(f'{ED}/{ed}/info.toon', encoding='utf-8', errors='replace').read()
    for f in ['intro_en', 'intro']:
        m = re.search(rf'{f}:\s*"(.*?)"', t, re.S)
        if m and len(m.group(1).strip()) > 20:
            return m.group(1)
    # no intro at all — generate from book_name
    bn = re.search(r'book_name:\s*"?([^"\n]+)"?', t)
    if bn:
        return bn.group(1)  # LLM will expand this
    return None

def fill_intros(ed):
    """Fill all missing intro_<lang> for a book."""
    ip = f'{ED}/{ed}/info.toon'
    t = open(ip, encoding='utf-8', errors='replace').read()
    src = get_intro_source(ed)
    if not src: return f'{ed}: no intro source'
    jobs = []
    for l in LANGS:
        field = f'intro_{l}'
        m = re.search(rf'{field}:\s*"(.*?)"', t, re.S)
        if not m or len(m.group(1).strip()) < 20:
            jobs.append((l, field))
    if not jobs: return f'{ed}: intros complete'
    # if source is just book_name (short), ask LLM to expand first
    if len(src) < 50:
        src = glm_batch([(1, f"Write a brief scholarly introduction (2-3 sentences) for the Islamic book: {src}")], 'English')
        src = src.get(1, src) if src else src
    # batch all langs in one call per book? No — different langs. One call per lang.
    # Actually: max work per req = all langs in one call? No, each lang is different output.
    # Better: one call per lang, batch=1 (single intro per call). But user wants max work per req.
    # We'll do one call per lang (each intro is long text), 3 parallel via the outer executor.
    results = {}
    for l, field in jobs:
        r = glm_batch([(field, src)], LANGMAP[l])
        if r:
            val = r[field]
            if not val.startswith('[AI-translation]'):
                val = '[AI-translation] ' + val
            results[field] = val
    # write
    for field, val in results.items():
        val_esc = val.replace('"', '""')
        # if field exists (short), replace; else add after intro or metadata block
        if re.search(rf'{field}:\s*".*?"', t, re.S):
            t = re.sub(rf'{field}:\s*".*?"', f'{field}: "{val_esc}"', t, count=1, flags=re.S)
        else:
            # add after the last intro_ field or after intro:
            t = re.sub(r'(intro(?:_\w+)?:\s*".*?")', r'\1\n' + f'{field}: "{val_esc}"', t, count=1, flags=re.S)
    open(ip, 'w', encoding='utf-8').write(t)
    return f'{ed}: filled {len(results)} intros'

def fill_chapter_names(ed):
    """Fill missing name_<lang> for all sections."""
    ip = f'{ED}/{ed}/info.toon'
    t = open(ip, encoding='utf-8', errors='replace').read()
    m = re.search(r'sections\[(\d+)\]\{([^}]+)\}', t)
    if not m: return f'{ed}: no sections[] index'
    count = int(m.group(1))
    fields = [f.strip() for f in m.group(2).split(',')]
    # get name_en source for each section
    name_en_idx = fields.index('name_en') if 'name_en' in fields else -1
    if name_en_idx < 0: return f'{ed}: no name_en source'
    lines = t.split('\n')
    hdr_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith('sections['): hdr_idx = i; break
    if hdr_idx is None: return f'{ed}: no sections header'
    # collect section rows: (sec_id, name_en)
    sections = []
    for i in range(hdr_idx + 1, len(lines)):
        ln = lines[i].strip()
        if not ln.startswith('"'): break
        parts = ln.split('","')
        if len(parts) < len(fields): continue
        row = dict(zip(fields, [p.strip('"') for p in parts]))
        if row.get('name_en', '').strip():
            sections.append((row.get('id', ''), row['name_en']))
    if not sections: return f'{ed}: no name_en data'
    # which langs are missing?
    existing = set(f.replace('name_', '') for f in fields if f.startswith('name_'))
    missing = [l for l in LANGS if l not in existing]
    # also langs that exist but have <count non-empty
    # (skip for simplicity — focus on missing fields)
    if not missing: return f'{ed}: chapter names complete'
    # for each missing lang: translate all section names in one batch
    for lang in missing:
        target = LANGMAP[lang]
        items = [(sec_id, name) for sec_id, name in sections]
        results = glm_batch(items, target, is_names=True)
        if not results: continue
        # add name_<lang> field to header + each row
        new_field = f'name_{lang}'
        if new_field not in fields:
            fields.append(new_field)
            # update header
            lines[hdr_idx] = f'sections[{count}]{{{",".join(fields)}}}:'
            # add to each data row
            for i in range(hdr_idx + 1, len(lines)):
                ln = lines[i].strip()
                if not ln.startswith('"'): break
                parts = ln.split('","')
                if len(parts) >= len(fields) - 1:
                    sec_id = parts[0].strip('"')
                    val = results.get(sec_id, '')
                    # append to row
                    parts.append(val)
                    lines[i] = '","'.join(parts)
    open(ip, 'w', encoding='utf-8').write('\n'.join(lines))
    return f'{ed}: filled chapter names for {len(missing)} langs'

# build jobs: (book, type) pairs
books = sorted([d for d in os.listdir(ED) if os.path.isdir(f'{ED}/{d}/sections')])
jobs = []
for ed in books:
    jobs.append(('intro', ed))
    jobs.append(('chap', ed))

print(f'jobs: {len(jobs)} ({len(books)} books x 2), workers={WORKERS}', flush=True)

def run(job):
    typ, ed = job
    if typ == 'intro':
        return fill_intros(ed)
    else:
        return fill_chapter_names(ed)

done = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(run, j): j for j in jobs}
    for f in concurrent.futures.as_completed(futs):
        done += 1
        try:
            r = f.result()
            print(f'  [{done}/{len(jobs)}] {r}', flush=True)
        except Exception as e:
            print(f'  [{done}/{len(jobs)}] ERR: {e}', flush=True)
print('ALL DONE', flush=True)
