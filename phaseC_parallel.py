#!/usr/bin/env python3
"""Phase C — re-translate corrupt intros via glm-5-2, ALL intros per lang in ONE batch request (max work/req),
3 langs in parallel (3 requests total)."""
import re, json, requests, concurrent.futures

JOBS = json.load(open('/tmp/phaseC_jobs.json'))
GW='http://localhost:8317/v1/chat/completions'
KEY='sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
LANGMAP={'ur':'Urdu','bn':'Bengali','hi':'Hindi'}

def fi(t,f):
    m=re.search(rf'{f}:\s*"(.*?)"',t,re.S); return m.group(1) if m else None

def set_intro(t,field,val):
    return re.sub(rf'{field}:\s*".*?"', f'{field}: "{val.replace(chr(34),chr(34)+chr(34))}"', t, count=1, flags=re.S)

def translate_lang(lang):
    lst = JOBS[lang]
    target = LANGMAP[lang]
    # batch: number each intro [N], send all in one prompt
    lines = [f"[{i+1}] ENGLISH:\n{src}" for i,(ed,field,src) in enumerate(lst)]
    prompt = (f"Translate each English hadith-collection intro into {target}. Faithful scholarly register. "
              f"For each, output ONLY the {target} translation preceded by [N] on its own line.\n\n"
              + "\n\n".join(lines))
    r = requests.post(GW, headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'},
        json={'model':'databricks-glm/glm-5-2','messages':[{'role':'user','content':prompt}]}, timeout=600)
    content = r.json()['choices'][0]['message']['content']
    # parse [N] ... blocks
    out = {}
    chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
    for ch in chunks:
        m = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
        if m:
            n=int(m.group(1)); txt=m.group(2).strip().strip('*"“”').strip()
            if 1<=n<=len(lst) and len(txt)>10:
                out[n-1]='[AI-translation] '+txt
    # apply to files
    applied=0
    files_edited=set()
    for i,(ed,field,src) in enumerate(lst):
        if i not in out: continue
        p=f'/home/saboor/code/hadith-api-toon/editions/{ed}/info.toon'
        t=open(p,encoding='utf-8',errors='replace').read()
        t=set_intro(t,field,out[i])
        open(p,'w',encoding='utf-8').write(t)
        applied+=1; files_edited.add(ed)
    return lang, applied, len(lst), files_edited

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    futs={ex.submit(translate_lang,lang):lang for lang in ('ur','bn','hi')}
    for f in concurrent.futures.as_completed(futs):
        lang,applied,total,files=f.result()
        print(f'{lang}: translated {applied}/{total}, files: {sorted(files)}', flush=True)
print('DONE')
