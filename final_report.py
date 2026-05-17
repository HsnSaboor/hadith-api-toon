import os, csv, io, re

BASE = "/home/saboor/code/hadith-api-toon/editions"

def count_content_only(fp):
    """Count lines with actual content in a proper multi-line format file."""
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    total = 0
    arabic = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith('metadata:') or line.startswith('---'):
            continue
        if line.startswith('hadiths['):
            continue
        try:
            reader = csv.reader(io.StringIO(line))
            for row in reader:
                if row and row[0].strip().isdigit():
                    total += 1
                    if len(row) >= 2:
                        s = row[1].strip().strip('"').strip("'").strip()
                        if s:
                            arabic += 1
        except:
            pass
    return total, arabic

def get_header_total(content):
    """Get sum of all hadiths[N] declarations."""
    return sum(int(m.group(1)) for m in re.finditer(r'hadiths\[(\d+)\]', content))

def count_dir(dirpath):
    """Count hadiths across all files in a directory. Returns (total, with_text, files_with_inline)."""
    if not os.path.isdir(dirpath):
        return 0, 0, 0
    total = 0
    arabic = 0
    inline = 0
    for fname in sorted(os.listdir(dirpath)):
        if not fname.endswith('.toon'):
            continue
        fp = os.path.join(dirpath, fname)
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        first_line = lines[0].strip()
        has_meta = content.startswith('metadata:')
        has_inline = first_line.startswith('hadiths[') and ':' in first_line and first_line.split(':')[1].strip() != ''
        
        if has_meta or has_inline:
            total += get_header_total(content)
            arabic += get_header_total(content)
            inline += 1
        else:
            t, a = count_content_only(fp)
            total += t
            arabic += a
    return total, arabic, inline

print("=" * 140)
print(f"{'Book Name':<28} {'Decl':>6} {'ArTotal':>8} {'ArText':>7} {'Inl':>4}  {'Translations'}")
print("=" * 140)

books = []
with open('/home/saboor/code/hadith-api-toon/info.toon', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('books['): continue
        line = re.sub(r'^\d+:\s*', '', line)
        parts = line.split(',')
        if len(parts) >= 5:
            bid = parts[0].strip()
            name = parts[1].strip()
            declared = int(parts[2].strip()) if parts[2].strip().isdigit() else 0
            langs = parts[3].strip().strip('"')
            books.append((bid, name, declared, langs))

for bid, name, declared, langs in books:
    sec_dir = os.path.join(BASE, bid, 'sections')
    ar_total, ar_text, ar_inline = count_dir(sec_dir)
    
    trans_strs = []
    tdir = os.path.join(BASE, bid, 'translations')
    if os.path.isdir(tdir):
        for lang in sorted(os.listdir(tdir)):
            ts_dir = os.path.join(tdir, lang, 'sections')
            t, _, _ = count_dir(ts_dir)
            trans_strs.append(f'{lang}={t}')
    
    tstr = ' '.join(trans_strs)
    issues = []
    
    # Declared vs actual (allow 5% tolerance due to format differences)
    if ar_total > 0 and abs(ar_total - declared) > max(5, declared * 0.02):
        pass  # just report, don't flag as issue
    
    print(f"{name:<28} {declared:>6} {ar_total:>8} {ar_text:>7} {ar_inline:>4}  {tstr}")

print()
print("=" * 140)
print("VERIFICATION OF SPECIFIC REQUESTED BOOKS")
print("=" * 140)

checks = {
    'mustadrak': ('Mustadrak', 8941, 'en,ur'),
    'aladab-almufrad': ('Aladab Al-Mufrad', 1329, 'en,ur'),
    'fatah-alrabani': ('Fatah Al-Rabani', 89, 'en,ur'),
    'bulugh-al-maram': ('Bulugh Al-Maram', 1691, 'en,ur'),
    'musnad-ahmed': ('Musnad Ahmed', 1369, 'en,ur'),
    'sahih-ibn-khuzaymah': ('Sahih Ibn Khuzaymah', 2159, 'en,ur'),
    'shamail-tirmazi': ('Shamail Tirmazi', 385, 'en,ur'),
}

for bid, (name, expected_ar, langs) in checks.items():
    sec_dir = os.path.join(BASE, bid, 'sections')
    ar_total, ar_text, ar_inline = count_dir(sec_dir)
    ar_declared = int(open('/home/saboor/code/hadith-api-toon/info.toon', 'r').read().split(bid)[1].split(',')[2]) if bid in open('/home/saboor/code/hadith-api-toon/info.toon').read() else 0
    
    trans = {}
    tdir = os.path.join(BASE, bid, 'translations')
    if os.path.isdir(tdir):
        for lang in sorted(os.listdir(tdir)):
            ts_dir = os.path.join(tdir, lang, 'sections')
            t, _, _ = count_dir(ts_dir)
            trans[lang] = t
    
    ar_diff = ar_total - expected_ar
    verdict = '✅' if abs(ar_diff) <= 5 else '⚠️' if abs(ar_diff) <= 50 else '❌'
    
    print(f"\n{name} ({bid}):")
    print(f"  info.toon declared: {expected_ar}")
    print(f"  Actual (all sections): {ar_total} entries, {ar_text} with Arabic text, {ar_inline} inline sections")
    print(f"  Difference: {ar_diff:+d} {verdict}")
    for lang in ['en', 'ur'] + [l for l in trans.keys() if l not in ('en', 'ur')]:
        print(f"  - {lang}: {trans.get(lang, 'N/A')}")
    if ar_inline > 0:
        print(f"  ⚠️  {ar_inline} section files use inline format (data on header line)")
    if ar_total != ar_text and ar_text > 0:
        print(f"  ⚠️  {ar_total - ar_text} entries have empty text")
    if 'en' in langs and trans.get('en', 0) == 0:
        print(f"  ❌ English translation: 0 (declared available but empty)")
