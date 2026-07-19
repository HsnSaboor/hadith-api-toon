#!/usr/bin/env python3
"""Fill missing translation langs via glm-5-2. 10 workers parallel, 10 hadiths/req (max work).
For each (edition,lang): read AR sections, translate each hadith, write translations/<lang>/sections/<N>.toon matching AR HN order.
Then update info.toon available_languages."""
import os, re, json, requests, concurrent.futures

ED='/home/saboor/code/hadith-api-toon/editions'
GW='http://localhost:8317/v1/chat/completions'
KEY='sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL='databricks-glm/glm-5-2'
BATCH=10
WORKERS=10
LANGMAP={'bn':'Bengali','fr':'French','hi':'Hindi','id':'Indonesian','tr':'Turkish','ta':'Tamil','ru':'Russian','roman-ur':'Romanized Urdu'}

jobs=json.load(open('/tmp/fill_jobs.json'))

def read_ar_sections(ed):
    """Return list of (section_file, [(hn, arabic), ...])"""
    sd=f'{ED}/{ed}/sections'
    out=[]
    for f in sorted(os.listdir(sd), key=lambda x:int(x[:-5]) if x[:-5].isdigit() else 9999):
        if not f.endswith('.toon'): continue
        rows=[]
        for ln in open(f'{sd}/{f}',encoding='utf-8',errors='replace'):
            if ln.startswith('"'):
                p=ln.rstrip('\n').split('","',2)
                if len(p)>=2:
                    hn=p[0].strip('"'); ar=p[1]
                    rows.append((hn,ar))
        out.append((f,rows))
    return out

def translate_batch(batch, target_lang):
    """batch: [(hn, arabic)]. returns {hn: '[AI-translation] en'}"""
    lines=[f"[{i+1}] ARABIC: {ar}" for i,(hn,ar) in enumerate(batch)]
    prompt=(f"Translate each Arabic hadith into {target_lang}. Faithful hadith register, no commentary, no preface. "
            f"Preserve proper-name transliteration. For each, output ONLY the translation preceded by [N] on its own line.\n\n"+"\n\n".join(lines))
    idx={i+1:hn for i,(hn,_) in enumerate(batch)}
    for attempt in range(6):
        try:
            r=requests.post(GW,headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'},
                json={'model':MODEL,'messages':[{'role':'user','content':prompt}]},timeout=600)
            if r.status_code==200:
                content=r.json()['choices'][0]['message']['content']
                out={}
                chunks=re.split(r'\n(?=\[?\d+\]?[.)\]]\s)',content)
                for ch in chunks:
                    m=re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)',ch,re.S)
                    if m:
                        n=int(m.group(1)); txt=m.group(2).strip().strip('*"“”').strip()
                        if n in idx and len(txt)>=5:
                            out[idx[n]]='[AI-translation] '+txt
                if out: return out
            elif r.status_code==429: import time; time.sleep(8)
            else: import time; time.sleep(4)
        except Exception: import time; time.sleep(5)
    return {}

def fill_one(job):
    ed,lang,ar_total,have=job['ed'],job['lang'],job['ar'],job['have']
    target=LANGMAP[lang]
    secs=read_ar_sections(ed)
    td=f'{ED}/{ed}/translations/{lang}/sections'
    os.makedirs(td,exist_ok=True)
    done=0
    for secf,rows in secs:
        if not rows:
            open(f'{td}/{secf}','w',encoding='utf-8').write(f'hadiths[0]{{hadithnumber,text}}:\n')
            continue
        hn_to_text={}
        for i in range(0,len(rows),BATCH):
            b=rows[i:i+BATCH]
            res=translate_batch(b,target)
            hn_to_text.update(res)
        # write section file: hadiths[N]{hadithnumber,text}: + rows in AR HN order
        out=[f'hadiths[{len(rows)}]{{hadithnumber,text}}:']
        for hn,ar in rows:
            t=hn_to_text.get(hn,'[AI-translation] [translation pending]')
            out.append(f'"{hn}","{t.replace(chr(34),chr(34)+chr(34))}"')
        open(f'{td}/{secf}','w',encoding='utf-8').write('\n'.join(out)+'\n')
        done+=len(hn_to_text)
    return ed,lang,done

def update_info_langs(ed,lang):
    p=f'{ED}/{ed}/info.toon'
    t=open(p,encoding='utf-8',errors='replace').read()
    m=re.search(r'available_languages:\s*"?([a-z,/-]+)"?',t)
    if m:
        langs=m.group(1).split(',')
        if lang not in langs:
            langs.append(lang); langs.sort()
            t=t.replace(m.group(0),f'available_languages: "{",".join(langs)}"')
            open(p,'w',encoding='utf-8').write(t)

print(f'filling {len(jobs)} jobs, {WORKERS} workers, {BATCH}/req', flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs={ex.submit(fill_one,j):j for j in jobs}
    for f in concurrent.futures.as_completed(futs):
        try:
            ed,lang,done=f.result()
            update_info_langs(ed,lang)
            print(f'  {ed}/{lang}: {done} translated', flush=True)
        except Exception as e:
            j=futs[f]; print(f'  {j["ed"]}/{j["lang"]}: ERR {e}', flush=True)
print('ALL DONE')
