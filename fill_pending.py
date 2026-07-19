#!/usr/bin/env python3
"""Fix the 2942 [translation pending] rows. Read AR text for each, translate via glm-5-2, patch in-place."""
import os, re, json, requests, concurrent.futures, time

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'databricks-glm/glm-5-2'
BATCH = 10
WORKERS = 10
LANGMAP = {'bn':'Bengali','fr':'French','hi':'Hindi','id':'Indonesian','tr':'Turkish','ta':'Tamil','ru':'Russian','roman-ur':'Romanized Urdu'}

pending = json.load(open('/tmp/pending.json'))
print(f'pending rows: {len(pending)}')

# group by (ed, lang, sec) to batch
from collections import defaultdict
groups = defaultdict(list)
for p in pending:
    groups[(p['ed'], p['lang'], p['sec'])].append(p['hn'])

# for each group, read AR text for each HN
def get_ar_text(ed, sec, hn):
    """Read AR source row for given HN."""
    p = f'{ED}/{ed}/sections/{sec}'
    if not os.path.exists(p):
        return None
    for ln in open(p, encoding='utf-8', errors='replace'):
        if ln.startswith('"'):
            parts = ln.rstrip('\n').split('","', 2)
            if len(parts) >= 2 and parts[0].strip('"') == hn:
                return parts[1]  # arabic field
    return None

def translate_batch(batch_ar, target_lang):
    """batch_ar: [(hn, arabic)]. returns {hn: '[AI-translation] text'}"""
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
                chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
                for ch in chunks:
                    m = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
                    if m:
                        n = int(m.group(1))
                        txt = m.group(2).strip().strip('*"“”').strip()
                        if n in idx and len(txt) >= 5:
                            out[idx[n]] = '[AI-translation] ' + txt
                if out:
                    return out
            elif r.status_code == 429:
                time.sleep(10)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    return {}

def fix_group(args):
    ed, lang, sec, hns = args
    target = LANGMAP[lang]
    # collect AR text for each pending HN
    batch = []
    for hn in hns:
        ar = get_ar_text(ed, sec, hn)
        if ar:
            batch.append((hn, ar))
    if not batch:
        return ed, lang, sec, 0
    # translate
    translations = {}
    for i in range(0, len(batch), BATCH):
        b = batch[i:i+BATCH]
        res = translate_batch(b, target)
        translations.update(res)
    # patch the toon file
    tp = f'{ED}/{ed}/translations/{lang}/sections/{sec}'
    lines = open(tp, encoding='utf-8', errors='replace').read().split('\n')
    out = []
    fixed = 0
    for ln in lines:
        if ln.startswith('"') and '[translation pending]' in ln:
            hn = ln.split('"')[1]
            if hn in translations:
                t = translations[hn].replace('"', '""')
                out.append(f'"{hn}","{t}"')
                fixed += 1
                continue
        out.append(ln)
    if fixed > 0:
        open(tp, 'w', encoding='utf-8').write('\n'.join(out))
    return ed, lang, sec, fixed

# build group args
group_args = [(k[0], k[1], k[2], v) for k, v in groups.items()]
print(f'groups: {len(group_args)}, workers: {WORKERS}', flush=True)

total_fixed = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(fix_group, a): a for a in group_args}
    for f in concurrent.futures.as_completed(futs):
        try:
            ed, lang, sec, fixed = f.result()
            total_fixed += fixed
            print(f'  {ed}/{lang}/{sec}: {fixed} fixed (total {total_fixed})', flush=True)
        except Exception as e:
            print(f'  ERR: {e}', flush=True)
print(f'ALL DONE. Fixed {total_fixed}/{len(pending)}')
