#!/usr/bin/env python3
"""Fill remaining 1634 [translation pending] rows. Robust parser: [N] format OR line-based fallback."""
import os, re, json, requests, concurrent.futures, time

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'databricks-glm/glm-5-2'
BATCH = 3
WORKERS = 10
LANGMAP = {'bn':'Bengali','fr':'French','hi':'Hindi','id':'Indonesian','tr':'Turkish','ta':'Tamil','ru':'Russian','roman-ur':'Romanized Urdu'}

pending = json.load(open('/tmp/pending.json'))
from collections import defaultdict
groups = defaultdict(list)
for p in pending:
    groups[(p['ed'], p['lang'], p['sec'])].append(p['hn'])
print(f'pending: {len(pending)}, groups: {len(groups)}', flush=True)

def get_ar_text(ed, sec, hn):
    p = f'{ED}/{ed}/sections/{sec}'
    if not os.path.exists(p): return None
    for ln in open(p, encoding='utf-8', errors='replace'):
        if ln.startswith('"'):
            parts = ln.rstrip('\n').split('","', 2)
            if len(parts) >= 2 and parts[0].strip('"') == hn:
                return parts[1]
    return None

def translate_batch(batch_ar, target_lang):
    lines = [f"[{i+1}] ARABIC: {ar}" for i, (hn, ar) in enumerate(batch_ar)]
    prompt = (f"Translate each Arabic hadith into {target_lang}. Faithful hadith register, no commentary, no preface. "
              f"Preserve proper-name transliteration. For each, output ONLY the translation preceded by [N] on its own line.\n\n" + "\n\n".join(lines))
    idx = {i+1: hn for i, (hn, _) in enumerate(batch_ar)}
    for attempt in range(8):
        try:
            r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=600)
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                out = {}
                # try [N] format
                chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
                for ch in chunks:
                    m = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
                    if m:
                        n = int(m.group(1)); txt = m.group(2).strip().strip('*"“”').strip()
                        if n in idx and len(txt) >= 5:
                            out[idx[n]] = '[AI-translation] ' + txt
                # FALLBACK: if [N] parsing got <len(batch)/2, try line-based
                if len(out) < len(batch_ar) / 2:
                    raw_lines = [l.strip().strip('*"“”').strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 10]
                    # strip leading number markers from each line
                    cleaned = []
                    for l in raw_lines:
                        l2 = re.sub(r'^\*{0,2}\[?\d+\]?[.)\]]\s*', '', l).strip().strip('*"“”').strip()
                        if len(l2) >= 5: cleaned.append(l2)
                    # assign sequentially
                    for i, (hn, _) in enumerate(batch_ar):
                        if i < len(cleaned) and hn not in out:
                            out[hn] = '[AI-translation] ' + cleaned[i]
                if out: return out
            elif r.status_code == 429: time.sleep(10)
            else: time.sleep(5)
        except Exception: time.sleep(5)
    return {}

def fix_group(args):
    ed, lang, sec, hns = args
    target = LANGMAP[lang]
    batch = []
    for hn in hns:
        ar = get_ar_text(ed, sec, hn)
        if ar: batch.append((hn, ar))
    if not batch: return ed, lang, sec, 0
    translations = {}
    for i in range(0, len(batch), BATCH):
        b = batch[i:i+BATCH]
        res = translate_batch(b, target)
        translations.update(res)
    tp = f'{ED}/{ed}/translations/{lang}/sections/{sec}'
    lines = open(tp, encoding='utf-8', errors='replace').read().split('\n')
    out = []; fixed = 0
    for ln in lines:
        if ln.startswith('"') and '[translation pending]' in ln:
            hn = ln.split('"')[1]
            if hn in translations:
                t = translations[hn].replace('"', '""')
                out.append(f'"{hn}","{t}"'); fixed += 1; continue
        out.append(ln)
    if fixed > 0: open(tp, 'w', encoding='utf-8').write('\n'.join(out))
    return ed, lang, sec, fixed

group_args = [(k[0], k[1], k[2], v) for k, v in groups.items()]
total = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(fix_group, a): a for a in group_args}
    for f in concurrent.futures.as_completed(futs):
        try:
            ed, lang, sec, fixed = f.result(); total += fixed
            print(f'  {ed}/{lang}/{sec}: {fixed} (total {total})', flush=True)
        except Exception as e: print(f'  ERR: {e}', flush=True)
print(f'DONE: {total}/{len(pending)}', flush=True)
