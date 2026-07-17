#!/usr/bin/env python3
"""Translate missing Arabic hadiths -> English (lulu) and -> en (silsala) via openrouter free models.
Prefixed [AI-translation]. Resumable via cache. Keys: .env + 6 from translate_en_batch.py.
"""
import json, os, re, time, requests, sys, concurrent.futures

KEYS = [
    open('/home/saboor/code/hadith-api-toon/.env').read().split('OPENROUTER_API_KEY=')[1].split('\n')[0].strip().strip('"'),
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]
KEYS = [k for k in KEYS if k]
MODELS = ["openai/gpt-oss-20b:free","qwen/qwen3-next-80b-a3b-instruct:free","google/gemma-4-31b-it:free","nvidia/nemotron-3-super-120b-a12b:free"]
BATCH = 8
WORKERS = 2

def translate_batch(batch, target_lang_hint="English"):
    """batch: list of (hn, arabic). returns {hn: translated_text}."""
    lines = [f"[{i+1}] ARABIC: {ar}" for i,(hn,ar) in enumerate(batch)]
    prompt = (f"Translate each Arabic hadith into {target_lang_hint}. Faithful hadith register, no commentary, no preface. "
              f"Preserve proper-name transliteration. Output ONLY the translation for each, preceded by [N] on its own line.\n\n"
              + "\n\n".join(lines))
    idx_map = {i+1: hn for i,(hn,_) in enumerate(batch)}
    for attempt in range(12):
        key = KEYS[attempt % len(KEYS)]
        model = MODELS[attempt % len(MODELS)]
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
                json={"model": model, "messages":[{"role":"user","content":prompt}], "temperature":0, "max_tokens":16384},
                timeout=180)
            if r.status_code == 200:
                content = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                out = {}
                # Robust: handle many formats the model emits.
                # 1) [N] text   2) N. **arabic** – "english"   3) N. arabic – english   4) N) text
                # Split into numbered chunks first.
                # Try [N] ...  then  N. ...  then N) ...
                import re as _re
                # universal split on a leading number marker at line start
                chunks = _re.split(r'\n(?=\[?\d+\]?[.)]\s)', content)
                for ch in chunks:
                    mm = _re.match(r'\s*\[?(\d+)\]?[.)]\s*(.*)', ch, _re.S)
                    if not mm: continue
                    n = int(mm.group(1)); rest = mm.group(2).strip()
                    if n not in idx_map or not rest: continue
                    # strip a leading "**arabic** – " or "arabic – " wrapper if the model echoed arabic
                    # patterns: **<arabic>** – "<english>"  or  <arabic> – <english>
                    m2 = _re.match(r'\*{0,2}[^\n–:]{3,}?\*{0,2}\s*[–—-]\s*["“]?(.*?)["”]?\s*$', rest, _re.S)
                    txt = m2.group(1).strip() if m2 else rest
                    # remove surrounding quotes/asterisks
                    txt = txt.strip('* "“”"').strip()
                    if len(txt) >= 5:
                        out[idx_map[n]] = "[AI-translation] " + txt
                if out: return out
            elif r.status_code == 429:
                time.sleep(15)
            else:
                time.sleep(6)
        except Exception:
            time.sleep(6)
    return {}

def load_ar_map(edition, secdir="sections", field="arabic"):
    """Read AR section .toon, return {hn: arabic_text}."""
    import os as _os
    base = f"/home/saboor/code/hadith-api-toon/editions/{edition}/{secdir}"
    m = {}
    for f in sorted(_os.listdir(base)):
        if not f.endswith(".toon"): continue
        for ln in open(_os.path.join(base,f), encoding="utf-8", errors="replace"):
            if not ln.startswith('"'): continue
            parts = ln.rstrip("\n").split('","')
            if len(parts) >= 2:
                hn = parts[0].strip('"')
                ar = parts[1].rstrip('"') if field=="text" else parts[1]
                if hn.isdigit() and ar.strip(): m[int(hn)] = ar
    return m

def load_existing_hns(edition, lang, secdir):
    import os as _os
    base = f"/home/saboor/code/hadith-api-toon/editions/{edition}/translations/{lang}/{secdir}"
    if not _os.path.isdir(base): return set()
    s = set()
    for f in sorted(_os.listdir(base)):
        if not f.endswith(".toon"): continue
        for ln in open(_os.path.join(base,f), encoding="utf-8", errors="replace"):
            if ln.startswith('"'):
                hn = ln.split('","')[0].strip('"')
                if hn.isdigit(): s.add(int(hn))
    return s

def write_rows_to_files(edition, lang, hn_to_text, ar_hn_order):
    """Insert [hn->text] rows into translation section files, splitting by section.
    For lulu/silsala: AR sections/<N>.toon defines which HN belongs to which file.
    We write each missing HN into the section file that contains it in AR."""
    import os as _os
    tbase = f"/home/saboor/code/hadith-api-toon/editions/{edition}/translations/{lang}/sections"
    # build file -> list of (hn,text) from AR section assignment
    arbase = f"/home/saboor/code/hadith-api-toon/editions/{edition}/sections"
    file_rows = {}
    for f in sorted(_os.listdir(arbase)):
        if not f.endswith(".toon"): continue
        for ln in open(_os.path.join(arbase,f), encoding="utf-8", errors="replace"):
            if not ln.startswith('"'): continue
            hn = ln.split('","')[0].strip('"')
            if hn in (str(h) for h in hn_to_text):
                hni = int(hn)
                if hni in hn_to_text:
                    file_rows.setdefault(f, []).append((hni, hn_to_text[hni]))
    written = 0
    for fname, rows in file_rows.items():
        path = _os.path.join(tbase, fname)
        # read existing EN rows
        existing = {}
        order = []
        for ln in open(path, encoding="utf-8", errors="replace"):
            if ln.startswith('"'):
                p = ln.rstrip("\n").split('","')
                if len(p) >= 2:
                    hn = p[0].strip('"'); t = p[1]
                    existing[hn] = t
                    order.append(hn)
        # merge
        for hn, txt in rows:
            existing[str(hn)] = txt
            if str(hn) not in order: order.append(str(hn))
        # sort by hn numeric
        order.sort(key=lambda x: int(x) if x.isdigit() else 999999)
        with open(path, "w", encoding="utf-8") as out:
            out.write(f'hadiths[{len(order)}]{{hadithnumber,text}}:\n')
            for hn in order:
                t = existing[hn]
                t = t.replace('"','""')
                out.write(f'"{hn}","{t}"\n')
        written += len(rows)
    return written

if __name__ == "__main__":
    edition = sys.argv[1]  # lulu-wal-marjan or silsila-sahih
    lang = "en"
    cache = f"/tmp/{edition}_en_cache.json"
    ar_map = load_ar_map(edition)
    existing = load_existing_hns(edition, lang, "sections")
    missing = sorted(set(ar_map) - existing)
    print(f"{edition}: AR={len(ar_map)} EN-existing={len(existing)} missing={len(missing)}")
    done = {}
    if os.path.exists(cache):
        done = json.load(open(cache))
    todo = [(hn, ar_map[hn]) for hn in missing if str(hn) not in done]
    print(f"already done: {len(done)}, todo: {len(todo)}")
    # translate in parallel batches
    batches = [todo[i:i+BATCH] for i in range(0,len(todo),BATCH)]
    def run(bi):
        b = batches[bi]
        return translate_batch(b, "English")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for res in ex.map(run, range(len(batches))):
            done.update({str(k):v for k,v in res.items()})
            # checkpoint
            json.dump(done, open(cache,"w"))
            print(f"  done={len(done)}/{len(missing)}")
    json.dump(done, open(cache,"w"))
    print(f"translating complete: {len(done)}/{len(missing)}")
    if len(done) == len(missing) or len(done) > 0:
        hn_to_text = {int(k):v for k,v in done.items()}
        w = write_rows_to_files(edition, lang, hn_to_text, None)
        print(f"wrote {w} rows into {edition} EN files")
