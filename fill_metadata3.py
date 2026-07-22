#!/usr/bin/env python3
"""Fill missing intros + chapter names, CORRECTLY escaping newlines/quotes this time.
Lessons from prior broken attempts:
1. LLM output often contains literal newlines (paragraphs, markdown headers) -- these
   MUST be escaped to literal \\n before writing into the single-line toon field.
2. LLM output may contain literal " characters (quoted phrases) -- these MUST be
   escaped to "" (toon's doubling convention) before writing.
3. For sections[] rows: build the ENTIRE new row from scratch as a properly quoted
   '","'-joined string, never append raw unquoted fragments to an existing row string.
4. Verify with csv.reader immediately after every write; abort that field if it fails.
"""
import os, re, json, requests, concurrent.futures, time, csv, io

ED = '/home/saboor/code/hadith-api-toon/editions'
GW = 'http://localhost:8317/v1/chat/completions'
KEY = 'sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh'
MODEL = 'claude-sonnet-5'
WORKERS = 3
LANGMAP = {'en':'English','ur':'Urdu','bn':'Bengali','fr':'French','hi':'Hindi','id':'Indonesian',
           'tr':'Turkish','ta':'Tamil','ru':'Russian','roman-ur':'Romanized Urdu','de':'German','es':'Spanish'}

gaps = json.load(open('/tmp/gaps_redo.json'))

def escape_for_toon(s):
    """Escape a raw string value for embedding as a toon double-quoted field."""
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = s.replace('"', '""')      # toon's own quote-doubling convention
    s = s.replace('\n', '\\n')    # literal backslash-n, matches existing convention in repo
    return s

def extract_text(msg_content):
    if isinstance(msg_content, str):
        return msg_content
    if isinstance(msg_content, list):
        parts = [b.get('text', '') for b in msg_content if isinstance(b, dict) and b.get('type') == 'text']
        return '\n'.join(parts)
    return ''

def glm_call(prompt, retries=5):
    for attempt in range(retries):
        try:
            r = requests.post(GW, headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=300)
            if r.status_code == 200:
                content = extract_text(r.json()['choices'][0]['message']['content']).strip()
                content = re.sub(r'^\[?\d+\]?[.)\]]\s*', '', content).strip()
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
            return m.group(1).replace('\\n', ' ')  # flatten any existing escapes into plain text for the source
    bn = re.search(r'book_name:\s*"?([^"\n]+)"?', t)
    if bn:
        return bn.group(1)
    return None

def verify_line(ln, expected_fields=None):
    """Verify a single toon-format line parses correctly with csv.reader."""
    try:
        rows = list(csv.reader(io.StringIO(ln)))
        if not rows:
            return False
        if expected_fields is not None and len(rows[0]) != expected_fields:
            return False
        return True
    except Exception:
        return False

def fill_one_intro(ed, field):
    ip = f'{ED}/{ed}/info.toon'
    t = open(ip, encoding='utf-8', errors='replace').read()
    m = re.search(rf'{field}:\s*"(.*?)"', t, re.S)
    if m and len(m.group(1).strip()) >= 20:
        return f'{ed} {field}: already filled'
    src = get_intro_source(ed)
    if not src:
        return f'{ed} {field}: NO SOURCE'
    lang_code = field.replace('intro_', '') if field != 'intro' else 'en'
    target = LANGMAP.get(lang_code, 'English')
    if len(src) < 50:
        expanded = glm_call(f"Write a brief scholarly introduction (2-3 plain-text sentences, no markdown headers) in English for the Islamic hadith book titled: {src}")
        if expanded:
            src = expanded
    translated = glm_call(
        f"Translate this book introduction into {target}. Faithful scholarly register. "
        f"Output ONLY the translation as plain prose text -- no markdown headers, no bullet points, no line breaks. "
        f"Keep it as a single continuous paragraph:\n\n{src}"
    )
    if not translated:
        return f'{ed} {field}: TRANSLATE FAILED'
    val = translated if translated.startswith('[AI-translation]') else '[AI-translation] ' + translated
    val_esc = escape_for_toon(val)
    test_line = f'{field}: "{val_esc}"'
    # verify no stray raw newline remains and quotes are balanced
    if '\n' in val_esc.replace('\\n', ''):
        return f'{ed} {field}: FAILED post-escape newline check'
    t = open(ip, encoding='utf-8', errors='replace').read()
    if re.search(rf'{field}:\s*".*?"', t, re.S):
        t2 = re.sub(rf'{field}:\s*".*?"', f'{field}: "{val_esc}"', t, count=1, flags=re.S)
    else:
        t2 = re.sub(r'(available_languages:\s*"[^"]*")', r'\1\n  ' + f'{field}: "{val_esc}"', t, count=1)
        if t2 == t:
            return f'{ed} {field}: NO ANCHOR FOUND'
    open(ip, 'w', encoding='utf-8').write(t2)
    return f'{ed} {field}: filled'

def fill_chapter_langs_for_book(ed, langs_needed):
    """Fill ALL missing chapter-name langs for a book in one shot, rebuilding rows from scratch."""
    ip = f'{ED}/{ed}/info.toon'
    t = open(ip, encoding='utf-8', errors='replace').read()
    m = re.search(r'sections\[(\d+)\]\{([^}]+)\}', t)
    if not m:
        return f'{ed}: no sections[] index'
    count = int(m.group(1))
    fields = [f.strip() for f in m.group(2).split(',')]
    if 'name_en' not in fields:
        return f'{ed}: no name_en source'
    lines = t.split('\n')
    hdr_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith('sections['):
            hdr_idx = i; break
    if hdr_idx is None:
        return f'{ed}: no header line'

    # parse existing rows properly via csv.reader
    row_data = []  # list of dict field->value, in order
    end_idx = hdr_idx + 1
    while end_idx < len(lines):
        ln = lines[end_idx].strip()
        if not ln.startswith('"'):
            break
        try:
            parsed = list(csv.reader(io.StringIO(ln)))[0]
        except Exception:
            end_idx += 1
            continue
        if len(parsed) < len(fields):
            end_idx += 1
            continue
        row = dict(zip(fields, parsed))
        row_data.append(row)
        end_idx += 1

    if not row_data:
        return f'{ed}: no rows parsed'

    langs_needed = [l for l in langs_needed if f'name_{l}' not in fields]
    if not langs_needed:
        return f'{ed}: chapter names already complete'

    # translate each needed lang, one call per lang (batch = all sections)
    new_col_data = {}  # lang -> {sec_id: value}
    for lang in langs_needed:
        target = LANGMAP[lang]
        items = [(row['id'], row['name_en']) for row in row_data if row.get('name_en', '').strip()]
        if not items:
            continue
        lines_batch = [f"[{i+1}] {name}" for i, (sid, name) in enumerate(items)]
        prompt = (f"Translate each chapter title into {target}. Faithful, concise, plain text only. "
                  f"For each, output ONLY the translated title preceded by [N] on its own line, no extra commentary.\n\n" + "\n\n".join(lines_batch))
        result_map = {}
        for attempt in range(4):
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
            idx = {i+1: sid for i, (sid, _) in enumerate(items)}
            chunks = re.split(r'\n(?=\[?\d+\]?[.)\]]\s)', content)
            for ch in chunks:
                mm = re.match(r'\s*\[?(\d+)\]?[.)\]]\s*(.*)', ch, re.S)
                if mm:
                    n = int(mm.group(1))
                    txt = mm.group(2).strip()
                    txt = txt.split('\n')[0].strip()  # force single line, drop anything after
                    if n in idx and len(txt) >= 1:
                        result_map[idx[n]] = txt
            if len(result_map) >= len(items) * 0.8:
                break
        new_col_data[lang] = result_map

    # rebuild fields + rows from scratch
    new_fields = fields + [f'name_{l}' for l in langs_needed]
    new_lines = [f'sections[{count}]{{{",".join(new_fields)}}}:']
    fixed_count = 0
    for row in row_data:
        vals = [row.get(f, '') for f in fields]
        for lang in langs_needed:
            v = new_col_data.get(lang, {}).get(row['id'], '')
            vals.append(v)
        escaped_vals = [escape_for_toon(v) for v in vals]
        new_row = '","'.join(escaped_vals)
        new_row = f'"{new_row}"'
        if not verify_line(new_row, expected_fields=len(new_fields)):
            # fall back: keep old fields only, blank new ones, still verify
            vals_fallback = [row.get(f, '') for f in fields] + [''] * len(langs_needed)
            escaped_fallback = [escape_for_toon(v) for v in vals_fallback]
            new_row = '"' + '","'.join(escaped_fallback) + '"'
        else:
            fixed_count += 1
        new_lines.append(new_row)

    # splice back into file, preserving everything before sections[
    pre = '\n'.join(lines[:hdr_idx]).rstrip('\n')
    final_text = pre + '\n\n' + '\n'.join(new_lines) + '\n'
    open(ip, 'w', encoding='utf-8').write(final_text)
    return f'{ed}: filled chapter names for {len(langs_needed)} langs ({fixed_count}/{len(row_data)} rows verified)'

# Build per-book job groups
from collections import defaultdict
intro_by_ed = defaultdict(list)
for j in gaps['intros']:
    intro_by_ed[j['ed']].append(j['field'])
chap_by_ed = defaultdict(list)
for j in gaps['chapters']:
    chap_by_ed[j['ed']].append(j['lang'])

all_eds = sorted(set(list(intro_by_ed.keys()) + list(chap_by_ed.keys())))
print(f'books to process: {len(all_eds)}', flush=True)

def process_book(ed):
    out = []
    for field in intro_by_ed.get(ed, []):
        out.append(fill_one_intro(ed, field))
    if ed in chap_by_ed:
        out.append(fill_chapter_langs_for_book(ed, chap_by_ed[ed]))
    return ed, out

done = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(process_book, ed): ed for ed in all_eds}
    for f in concurrent.futures.as_completed(futs):
        done += 1
        ed = futs[f]
        try:
            _, results = f.result()
            for r in results:
                print(f'  [{done}/{len(all_eds)}] {r}', flush=True)
        except Exception as e:
            print(f'  [{done}/{len(all_eds)}] {ed}: ERR {e}', flush=True)
print('ALL DONE', flush=True)
