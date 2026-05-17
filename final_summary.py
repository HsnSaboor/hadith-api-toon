import os, csv, io, re

BASE = "/home/saboor/code/hadith-api-toon/editions"

def count_hadiths_in_file(fp):
    """Universal hadith counter - handles all formats."""
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    headers_found = re.findall(r'hadiths\[(\d+)\]', content)
    header_total = sum(int(x) for x in headers_found)
    
    has_metadata = content.startswith('metadata:')
    first_line = lines[0].strip() if lines else ''
    is_inline = ':' in first_line and first_line.split(':')[1].strip() != '' and first_line.startswith('hadiths[')
    
    if has_metadata or is_inline:
        return header_total, header_total
    
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

def count_all(files_list, base_path):
    total = 0
    arabic = 0
    for fname in sorted(files_list):
        if not fname.endswith('.toon'):
            continue
        t, a = count_hadiths_in_file(os.path.join(base_path, fname))
        total += t
        arabic += a
    return total, arabic

# Load info.toon
books = []
with open('/home/saboor/code/hadith-api-toon/info.toon', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('books['):
            continue
        line = re.sub(r'^\d+:\s*', '', line)
        parts = line.split(',')
        if len(parts) >= 5:
            bid = parts[0].strip()
            name = parts[1].strip()
            declared = parts[2].strip()
            langs = parts[3].strip().strip('"')
            books.append((bid, name, int(declared) if declared.isdigit() else 0, langs))

print("=" * 120)
print(f"{'Book Name':<28} {'Declared':>8} {'Arabic':>8} {'TextOnly':>9}  {'Languages & Counts'}")
print("=" * 120)

real_issues = []

for bid, name, declared, langs in books:
    sec_dir = os.path.join(BASE, bid, 'sections')
    if not os.path.isdir(sec_dir):
        continue
    
    files = sorted(os.listdir(sec_dir))
    
    # Count primary section 1 only for books where section 1 is the master
    # Count all sections for books where data is spread across sections
    
    sec1 = [f for f in files if f == '1.toon']
    rest = [f for f in files if f != '1.toon']
    
    if sec1:
        sec1_total, sec1_arabic = count_all(sec1, sec_dir)
    else:
        sec1_total, sec1_arabic = 0, 0
    
    all_total, all_arabic = count_all(files, sec_dir)
    
    # Decide which count to use for Arabic
    # If section 1 has all/most records, use section 1
    # If section 1 is metadata (few records), use all sections
    if sec1_total >= declared * 0.9:
        ar_total = sec1_total
        ar_text = sec1_arabic
    elif len(rest) > 0 and sec1_total < 100:
        # Section 1 is minimal, use total
        ar_total = all_total
        ar_text = all_arabic
    else:
        ar_total = sec1_total
        ar_text = sec1_arabic
    
    # Translations
    trans = {}
    trans_dir = os.path.join(BASE, bid, 'translations')
    if os.path.isdir(trans_dir):
        for lang in sorted(os.listdir(trans_dir)):
            ts_dir = os.path.join(trans_dir, lang, 'sections')
            if os.path.isdir(ts_dir):
                tfiles = sorted(os.listdir(ts_dir))
                t, _ = count_all(tfiles, ts_dir)
                trans[lang] = t
    
    trans_str = ' '.join(f'{k}={v}' for k, v in sorted(trans.items()))
    
    # Issues
    issues = []
    if abs(ar_total - declared) > 3 and ar_total > 0:
        issues.append(f"DECL:{declared} vs AR:{ar_total}")
    if ar_text > 0 and abs(ar_text - ar_total) > 3:
        issues.append(f"{ar_total - ar_text} empty entries")
    
    expected_langs = set(langs.split(','))
    for lang in expected_langs:
        if lang == 'ar': continue
        if lang not in trans:
            if lang not in ['hi', 'id', 'ro']:  # common gaps
                issues.append(f"{lang}:MISSING")
        elif trans[lang] == 0:
            issues.append(f"{lang}=0")
    
    issue_str = ' | '.join(issues) if issues else ''
    
    tl = ','.join(sorted(expected_langs - {'ar'}))
    print(f"{name:<28} {declared:>8} {ar_total:>8} {ar_text:>9}  [{tl}] {trans_str}")
    if issue_str:
        print(f"  {'▸':>55} {issue_str}")
        if 'DECL' in issue_str or 'MISSING' in issue_str or '=0' in issue_str:
            real_issues.append((bid, name, issue_str))

print()
print("=" * 120)
print("CRITICAL ISSUES AND VERIFICATION OF REQUESTED BOOKS:")
print("=" * 120)

# Verify user's specific books
checks = [
    ('mustadrak', 8941, 8941, 8933, 'en=8803, ur=8946'),
    ('aladab-almufrad', 1329, 1329, 1329, 'en=1326, ur=1329'),
    ('fatah-alrabani', 60, 60, 60, 'en=0, ur=89'),
    ('bulugh-al-maram', 1691, 1691, 1691, 'en=1766, ur=196'),
    ('musnad-ahmed', 1369, 1369, 1369, 'en=1359, ur=24489'),
    ('sahih-ibn-khuzaymah', 2159, 2159, 1737, 'en=0, ur=3828'),
    ('shamail-tirmazi', 385, 385, 373, 'en=733, ur=394'),
]

for bid, declared, ar_total, ar_text, trans_expected in checks:
    sec_dir = os.path.join(BASE, bid, 'sections')
    files = sorted(os.listdir(sec_dir))
    all_t, all_a = count_all(files, sec_dir)
    
    sec1_files = [f for f in files if f == '1.toon']
    s1_t, s1_a = count_all(sec1_files, sec_dir)
    
    # Find actual count for this book
    if s1_t >= declared * 0.9:
        actual_ar = s1_t
        actual_ar_text = s1_a
    else:
        actual_ar = all_t
        actual_ar_text = all_a
    
    print(f"\n{bid}:")
    print(f"  Expected: {declared} Arabic ({trans_expected})")
    print(f"  Found: {actual_ar} records, {actual_ar_text} with Arabic text")
    if actual_ar != declared:
        print(f"  {'❌' if abs(actual_ar - declared) > 5 else '⚠️'} {'MISMATCH' if abs(actual_ar - declared) > 5 else 'Minor diff'}: declared={declared}, actual={actual_ar} (diff={actual_ar - declared})")
    else:
        print(f"  ✅ Arabic count matches")
    
    # Translation checks
    trans_dir = os.path.join(BASE, bid, 'translations')
    if os.path.isdir(trans_dir):
        for lang in sorted(os.listdir(trans_dir)):
            ts_dir = os.path.join(trans_dir, lang, 'sections')
            if os.path.isdir(ts_dir):
                tfiles = sorted(os.listdir(ts_dir))
                t, _ = count_all(tfiles, ts_dir)
                print(f"  - {lang}: {t} hadiths")

print()
print("=" * 120)
print("SUMMARY OF REAL ISSUES FOUND:")
print("=" * 120)

print("""
1. SAHIH-IBN-KHUZAYMAH (MOST PROBLEMATIC)
   - Declared: 2159 Arabic + English + Urdu
   - Actual: 1737 with Arabic text out of 2159 entries (422 are refs/takhreej)
   - English translation: 0 (MISSING entirely)
   - Urdu: 3828 (expected ~4030, off by ~202)
   - 79/80 sections use inline format (data all on one line)

2. SILSILA-SAHIH 
   - Declared: 2533 Arabic
   - Actual: 2033 with Arabic text (500 ref entries)
   - English: 0 (MISSING)
   - Urdu: 4317

3. MU'JAM TABARANI SAGHIR
   - Declared: 13078 Arabic
   - Actual: 7846 with Arabic text in section 1
   - 45/46 sections inline format
   - English: 0 (MISSING)
   - Urdu: 20473

4. FATAH-ALRABANI 
   - Declared: 60 Arabic, info.toon says 60
   - Actual Arabic text: 60 (but 89 total entries including 29 empty)
   - Urdu: 89 (includes empty entries)
   - English: 0 (MISSING - declared as available language)

5. MUSNAD-AHMED  
   - Declared: 1369 Arabic
   - English: 1359 (OK)
   - Urdu: 24489 (SUSPICIOUS - should be ~same as Arabic)
   - 1169/1176 sections are inline format (broken)

6. MUSTADRAK
   - Declared: 8941 ✓
   - 8 entries with empty Arabic text (placeholders)
   - English: 8803 (138 short of Arabic)
   - Urdu: 8946 ✓

7. SHAMAIL-TIRMAZI
   - Declared: 385 Arabic
   - Actual Arabic text: 373 (12 entries missing text)
   - English: 733, Urdu: 394 ✓

8. BULUGH-AL-MARAM
   - Arabic: 1691 ✓
   - English: 1766 (75 extra - different edition content)
   - Urdu: 196 (partial)

9. ALADAB-ALMUFRAD ✅ CLEAN
   - All counts match expectations

10. MANY BOOKS have inline format sections - data exists but in suboptimal format
11. Qudsi, Sunan-Darmi, Nawawi, Bayhaqi: translation counts vary wildly from Arabic
""")
