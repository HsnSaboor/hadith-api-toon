#!/usr/bin/env python3
"""Fill empty/short EN rows in silsila-sahih from AR via openrouter LLM (free models).
In-place fill (rows already exist, just empty). Prefixed [AI-translation]."""
import json, os, re, time, requests, sys, concurrent.futures
exec(open('/home/saboor/code/hadith-api-toon/recover_llm_en.py').read().split('if __name__')[0])

EDITION='silsila-sahih'
LANG='en'
CACHE='/tmp/silsila-sahih_en_cache.json'

def empty_en_rows():
    base=f'/home/saboor/code/hadith-api-toon/editions/{EDITION}/translations/{LANG}/sections'
    empty=[]
    for f in sorted(os.listdir(base)):
        if not f.endswith('.toon'): continue
        for ln in open(os.path.join(base,f),encoding='utf-8',errors='replace'):
            if not ln.startswith('"'): continue
            p=ln.rstrip('\n').split('","')
            if len(p)>=2:
                hn=p[0].strip('"'); t=p[1].rstrip('"')
                if hn.isdigit() and len(t.strip())<10:
                    empty.append(int(hn))
    return empty

def fill_in_place(hn_to_text):
    base=f'/home/saboor/code/hadith-api-toon/editions/{EDITION}/translations/{LANG}/sections'
    filled=0
    for f in sorted(os.listdir(base)):
        if not f.endswith('.toon'): continue
        path=os.path.join(base,f)
        lines=open(path,encoding='utf-8',errors='replace').read().split('\n')
        out=[]
        for ln in lines:
            if ln.startswith('"'):
                p=ln.split('","')
                if len(p)>=2:
                    hn=p[0].strip('"')
                    t=p[1]
                    if hn.isdigit() and int(hn) in hn_to_text and len(t.rstrip('"').strip())<10:
                        new=hn_to_text[int(hn)].replace('"','""')
                        out.append(f'"{hn}","{new}"')
                        filled+=1
                        continue
            out.append(ln)
        open(path,'w',encoding='utf-8').write('\n'.join(out))
    return filled

if __name__=='__main__':
    ar=load_ar_map(EDITION)
    empty=empty_en_rows()
    print(f'silsala: AR={len(ar)} empty EN rows={len(empty)}')
    done={}
    if os.path.exists(CACHE): done=json.load(open(CACHE))
    todo=[(hn,ar[hn]) for hn in empty if str(hn) not in done and hn in ar]
    print(f'cached={len(done)} todo={len(todo)}')
    batches=[todo[i:i+BATCH] for i in range(0,len(todo),BATCH)]
    def run(bi): return translate_batch(batches[bi],'English')
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for res in ex.map(run,range(len(batches))):
            done.update({str(k):v for k,v in res.items()})
            json.dump(done,open(CACHE,'w'))
            print(f'  done={len(done)}/{len(empty)}')
    json.dump(done,open(CACHE,'w'))
    hn_to_text={int(k):v for k,v in done.items()}
    filled=fill_in_place(hn_to_text)
    print(f'filled {filled} empty EN rows in silsala')
