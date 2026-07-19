#!/usr/bin/env python3
"""Fill last 35 [translation pending] rows. Single-hadith calls (batch=1) to avoid parser miss."""
import os, re, json, requests, concurrent.futures, time

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'databricks-glm/glm-5-2'
WORKERS = 8
LANGMAP = {'bn':'Bengali','fr':'French','hi':'Hindi','id':'Indonesian','tr':'Turkish','ta':'Tamil','ru':'Russian','roman-ur':'Romanized Urdu'}

pending = json.load(open('/tmp/pending.json'))
print(f'pending: {len(pending)}', flush=True)

def get_ar_text(ed, sec, hn):
    p = f'{ED}/{ed}/sections/{sec}'
    if not os.path.exists(p): return None
    for ln in open(p, encoding='utf-8', errors='replace'):
        if ln.startswith('"'):
            parts = ln.rstrip('\n').split('","', 2)
            if len(parts) >= 2 and parts[0].strip('"') == hn:
                return parts[1]
    return None

def translate_one(ed, lang, sec, hn):
    ar = get_ar_text(ed, sec, hn)
    if not ar: return ed, lang, sec, hn, None
    target = LANGMAP[lang]
    prompt = f"Translate this Arabic hadith into {target}. Faithful hadith register, no commentary, no preface. Output ONLY the translation, nothing else.\n\n{ar}"
    for attempt in range(8):
        try:
            r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=120)
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content'].strip().strip('*"“”').strip()
                # strip any leading [1] or 1. prefix
                content = re.sub(r'^\*{0,2}\[?\d+\]?[.)\]]\s*', '', content).strip().strip('*"“”').strip()
                if len(content) >= 5:
                    return ed, lang, sec, hn, '[AI-translation] ' + content
            elif r.status_code == 429: time.sleep(8)
            else: time.sleep(4)
        except Exception: time.sleep(4)
    return ed, lang, sec, hn, None

def fix_one(args):
    ed, lang, sec, hn = args
    ed, lang, sec, hn, text = translate_one(ed, lang, sec, hn)
    if not text: return f'{ed}/{lang}/{sec} HN{hn}: FAIL'
    # patch file
    tp = f'{ED}/{ed}/translations/{lang}/sections/{sec}'
    lines = open(tp, encoding='utf-8', errors='replace').read().split('\n')
    out = []
    for ln in lines:
        if ln.startswith('"') and ln.split('"')[1] == hn and '[translation pending]' in ln:
            out.append(f'"{hn}","{text.replace(chr(34),chr(34)+chr(34))}"')
        else:
            out.append(ln)
    open(tp, 'w', encoding='utf-8').write('\n'.join(out))
    return f'{ed}/{lang}/{sec} HN{hn}: OK'

jobs = [(p['ed'], p['lang'], p['sec'], p['hn']) for p in pending]
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(fix_one, j): j for j in jobs}
    done = 0
    for f in concurrent.futures.as_completed(futs):
        r = f.result(); done += 1
        print(f'  [{done}/{len(jobs)}] {r}', flush=True)
print(f'DONE {done}', flush=True)
