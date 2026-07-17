#!/usr/bin/env python3
"""Translate Arabic hadiths -> EN via local glm-5-2 gateway. 30/call, 5 parallel, no max_tokens.
Handles: lulu-wal-marjan (insert missing rows) + silsila-sahih (fill empty rows). Resumable.
"""
import json, os, re, time, requests, sys, concurrent.futures

GW='http://localhost:8317/v1/chat/completions'
KEY='sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL='databricks-glm/glm-5-2'
BATCH=10
WORKERS=3

def translate_batch(batch):
    """batch: list of (hn, arabic). returns {hn: '[AI-translation] en'}"""
    lines = [f"[{i+1}] ARABIC: {ar}" for i,(hn,ar) in enumerate(batch)]
    prompt = ("Translate each Arabic hadith into English. Faithful hadith register, no commentary, no preface. "
              "Preserve proper-name transliteration. For each, output ONLY the English translation preceded by [N] on its own line.\n\n"
              + "\n\n".join(lines))
    idx_map = {i+1: hn for i,(hn,_) in enumerate(batch)}
    for attempt in range(8):
        try:
            r = requests.post(GW, headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'},
                json={'model':MODEL,'messages':[{'role':'user','content':prompt}]}, timeout=300)
            if r.status_code == 200:
                content = r.json().get('choices',[{}])[0].get('message',{}).get('content','')
                out = {}
                # primary [N] ... ; also handle N. ... and N) ...
                chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
                for ch in chunks:
                    mm = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
                    if not mm: continue
                    n=int(mm.group(1)); rest=mm.group(2).strip()
                    if n not in idx_map or not rest: continue
                    # strip arabic-echo wrapper: **arabic** – "en"  or  arabic – en
                    m2 = re.match(r'\*{0,2}[^\n–:]{3,}?\*{0,2}\s*[–—-]\s*["“]?(.*?)["”]?\s*$', rest, re.S)
                    txt = m2.group(1).strip() if m2 else rest
                    txt = txt.strip('* "“”"').strip()
                    if len(txt) >= 5:
                        out[idx_map[n]] = "[AI-translation] " + txt
                if out: return out
            elif r.status_code == 429:
                time.sleep(10)
            else:
                time.sleep(4)
        except Exception:
            time.sleep(5)
    return {}

def load_ar_map(edition):
    base=f'/home/saboor/code/hadith-api-toon/editions/{edition}/sections'
    m={}
    for f in sorted(os.listdir(base)):
        if not f.endswith('.toon'): continue
        for ln in open(os.path.join(base,f),encoding='utf-8',errors='replace'):
            if not ln.startswith('"'): continue
            parts=ln.rstrip('\n').split('","')
            if len(parts)>=2:
                hn=parts[0].strip('"'); ar=parts[1]
                if hn.isdigit() and ar.strip(): m[int(hn)]=ar
    return m

def existing_en_hns(edition):
    base=f'/home/saboor/code/hadith-api-toon/editions/{edition}/translations/en/sections'
    if not os.path.isdir(base): return set()
    s=set()
    for f in sorted(os.listdir(base)):
        if not f.endswith('.toon'): continue
        for ln in open(os.path.join(base,f),encoding='utf-8',errors='replace'):
            if ln.startswith('"'):
                hn=ln.split('","')[0].strip('"')
                if hn.isdigit(): s.add(int(hn))
    return s

def empty_en_hns(edition):
    base=f'/home/saboor/code/hadith-api-toon/editions/{edition}/translations/en/sections'
    e=[]
    for f in sorted(os.listdir(base)):
        if not f.endswith('.toon'): continue
        for ln in open(os.path.join(base,f),encoding='utf-8',errors='replace'):
            if not ln.startswith('"'): continue
            p=ln.rstrip('\n').split('","')
            if len(p)>=2:
                hn=p[0].strip('"'); t=p[1].rstrip('"')
                if hn.isdigit() and len(t.strip())<10:
                    e.append(int(hn))
    return e

def write_insert(edition, hn_to_text):
    """Insert missing HN rows (lulu): add row to the section file that owns that HN in AR."""
    arbase=f'/home/saboor/code/hadith-api-toon/editions/{edition}/sections'
    tbase=f'/home/saboor/code/hadith-api-toon/editions/{edition}/translations/en/sections'
    file_rows={}
    hnset={str(k) for k in hn_to_text}
    for f in sorted(os.listdir(arbase)):
        if not f.endswith('.toon'): continue
        for ln in open(os.path.join(arbase,f),encoding='utf-8',errors='replace'):
            if not ln.startswith('"'): continue
            hn=ln.split('","')[0].strip('"')
            if hn in hnset:
                file_rows.setdefault(f,[]).append(int(hn))
    written=0
    for fname, hns in file_rows.items():
        path=os.path.join(tbase,fname)
        existing={}; order=[]
        for ln in open(path,encoding='utf-8',errors='replace'):
            if ln.startswith('"'):
                p=ln.rstrip('\n').split('","')
                if len(p)>=2:
                    hn=p[0].strip('"'); existing[hn]=p[1]; order.append(hn)
        for hn in hns:
            if str(hn) not in existing:
                existing[str(hn)]=hn_to_text[hn].replace('"','""'); order.append(str(hn))
        order.sort(key=lambda x:int(x) if x.isdigit() else 999999)
        with open(path,'w',encoding='utf-8') as o:
            o.write(f'hadiths[{len(order)}]{{hadithnumber,text}}:\n')
            for hn in order: o.write(f'"{hn}","{existing[hn]}"\n')
        written+=sum(1 for h in hns if str(h) in existing)
    return written

def fill_empty(edition, hn_to_text):
    """Fill empty EN rows in place (silsila)."""
    base=f'/home/saboor/code/hadith-api-toon/editions/{edition}/translations/en/sections'
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
                    if hn.isdigit() and int(hn) in hn_to_text and len(p[1].rstrip('"').strip())<10:
                        out.append(f'"{hn}","{hn_to_text[int(hn)].replace(chr(34),chr(34)+chr(34))}"')
                        filled+=1; continue
            out.append(ln)
        open(path,'w',encoding='utf-8').write('\n'.join(out))
    return filled

def run(edition, mode):
    ar=load_ar_map(edition)
    if mode=='insert':
        missing=sorted(set(ar)-existing_en_hns(edition))
    else:
        missing=empty_en_hns(edition)
    cache=f'/tmp/{edition}_en_cache.json'
    done={}
    if os.path.exists(cache):
        try: done=json.load(open(cache))
        except: pass
    todo=[(hn,ar[hn]) for hn in missing if str(hn) not in done and hn in ar]
    print(f'{edition}: total_missing={len(missing)} cached={len(done)} todo={len(todo)}', flush=True)
    if not todo:
        pass
    batches=[todo[i:i+BATCH] for i in range(0,len(todo),BATCH)]
    def runb(i): return translate_batch(batches[i])
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs={ex.submit(runb,i):i for i in range(len(batches))}
        done_count=len(done)
        for fut in concurrent.futures.as_completed(futs):
            res=fut.result()
            done.update({str(k):v for k,v in res.items()})
            json.dump(done,open(cache,'w'))
            if len(done)!=done_count:
                done_count=len(done); print(f'  {edition} done={done_count}/{len(missing)}', flush=True)
    json.dump(done,open(cache,'w'))
    hn_to_text={int(k):v for k,v in done.items()}
    if mode=='insert': w=write_insert(edition,hn_to_text)
    else: w=fill_empty(edition,hn_to_text)
    print(f'{edition}: wrote {w} rows. cache={len(done)}/{len(missing)}', flush=True)

if __name__=='__main__':
    edition=sys.argv[1]; mode=sys.argv[2]  # mode: insert (lulu) or fill (silsila)
    run(edition,mode)
