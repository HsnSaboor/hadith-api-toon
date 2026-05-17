import os, csv, io, re

BASE = "/home/saboor/code/hadith-api-toon/editions"

def get_all_hadith_headers(content):
    """Find all hadiths[N] declarations in content and return their values."""
    return [int(m.group(1)) for m in re.finditer(r'hadiths\[(\d+)\]', content)]

def count_file(fp):
    """Count hadiths in a file, handling all formats."""
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Check for metadata format (has metadata: block)
    has_metadata = content.startswith('metadata:')
    
    # Get all header declarations
    headers = get_all_hadith_headers(content)
    header_total = sum(headers)
    
    if has_metadata:
        # Metadata format: metadata block + single hadiths[N]{...} line with inline data
        return header_total, header_total  # trust header for inline metadata format
    
    # Check if this is inline format (all data on same line as header)
    first_line = lines[0].strip()
    inline_data = False
    if first_line.startswith('hadiths['):
        idx = first_line.find(':')
        if idx >= 0 and first_line[idx+1:].strip():
            inline_data = True
    
    if inline_data:
        return header_total, header_total  # trust header for inline format
    
    # Standard multi-line format: count hadith records
    total_records = 0
    arabic_records = 0
    
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
                    total_records += 1
                    if len(row) >= 2:
                        second = row[1].strip().strip('"').strip("'").strip()
                        if second:
                            arabic_records += 1
        except:
            pass
    
    # If no records found this way but header claims there are some, 
    # the file might use mixed format (each line is a record)
    if total_records == 0 and header_total > 0:
        # Try counting every non-empty, non-header line as a record
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
                        total_records += 1
                        if len(row) >= 2:
                            second = row[1].strip().strip('"').strip("'").strip()
                            if second:
                                arabic_records += 1
            except:
                pass
    
    return total_records, arabic_records

# Read info.toon
books = []
with open('/home/saboor/code/hadith-api-toon/info.toon', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('books['):
            continue
        line = re.sub(r'^\d+:\s*', '', line)
        parts = line.split(',')
        if len(parts) >= 5:
            book_id = parts[0].strip()
            name = parts[1].strip()
            declared = parts[2].strip()
            langs = parts[3].strip().strip('"')
            try:
                declared_num = int(declared)
            except:
                declared_num = 0
            books.append((book_id, name, declared_num, langs))

print("=" * 130)
print(f"{'Book ID':<28} {'Decl':>6} {'ArCnt':>7} {'ArTxt':>7} {'Sections':>9} {'Trans (lang=count)'}")
print("=" * 130)

for book_id, name, declared, langs in books:
    sections_dir = os.path.join(BASE, book_id, 'sections')
    if not os.path.isdir(sections_dir):
        print(f"{book_id:<28} {declared:>6} {'NODIR':>7}")
        continue
    
    section_files = sorted(os.listdir(sections_dir))
    section_files = [f for f in section_files if f.endswith('.toon')]
    
    total_ar = 0
    total_ar_text = 0
    total_header = 0
    
    for fname in section_files:
        fpath = os.path.join(sections_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        headers = get_all_hadith_headers(content)
        hsum = sum(headers)
        total_header += hsum
        
        recs, arabic = count_file(fpath)
        total_ar += recs
        total_ar_text += arabic
    
    # Decide on best Arabic count
    # If section files use standard format, use total_ar
    # If inline, trust header total
    # If mixed, use header total for inline sections + arabic text for standard
    if total_ar == 0 and total_header > 0:
        ar_final = total_header
    elif total_ar > 0 and total_header > 0 and abs(total_ar - total_header) > 10:
        # Likely inline format sections - trust header
        ar_final = total_header
    else:
        ar_final = total_ar if total_ar > 0 else total_header
    
    # Translations
    trans = {}
    trans_dir = os.path.join(BASE, book_id, 'translations')
    if os.path.isdir(trans_dir):
        for lang in sorted(os.listdir(trans_dir)):
            tsections = os.path.join(trans_dir, lang, 'sections')
            if os.path.isdir(tsections):
                t_total = 0
                for tf in sorted(os.listdir(tsections)):
                    if not tf.endswith('.toon'):
                        continue
                    tfp = os.path.join(tsections, tf)
                    recs, _ = count_file(tfp)
                    t_total += recs
                trans[lang] = t_total
    
    trans_str = " ".join(f"{k}={v}" for k, v in sorted(trans.items()))
    issues = []
    
    if abs(ar_final - declared) > 2:
        issues.append(f"DECL({declared}) vs ACT({ar_final})")
    
    # Check for zero translations where lang is declared
    expected_langs = set(langs.split(','))
    for lang in expected_langs:
        if lang == 'ar':
            continue
        if lang not in trans:
            issues.append(f"MISSING_{lang}")
        elif trans.get(lang, 0) == 0:
            issues.append(f"{lang}=0!")
    
    issue_str = " *** " + "; ".join(issues) if issues else ""
    
    sec_str = f"{len(section_files)}"
    print(f"{book_id:<28} {declared:>6} {ar_final:>7} {total_ar_text:>7} {sec_str:>9}  {trans_str}{issue_str}")

print()
print("=" * 130)
print("SPECIAL BOOKS SPOT CHECK:")
print("=" * 130)

checks = [
    ('mustadrak', 8941, '(~8941 Arabic)'),
    ('aladab-almufrad', 1329, '(+1329 Urdu +1326 English)'),
    ('fatah-alrabani', 60, '(~89 Arabic? en=0, ur=89)'),
    ('bulugh-al-maram', 1691, '(+1766 English +196 Urdu)'),
    ('musnad-ahmed', 1369, '(+1359 English +24489 Urdu!)'),
    ('sahih-ibn-khuzaymah', 2159, '(en=0, ur=3828)'),
    ('shamail-tirmazi', 385, '(+733 English +394 Urdu)'),
]

for bid, expected, note in checks:
    sections_dir = os.path.join(BASE, bid, 'sections')
    section_files = [f for f in sorted(os.listdir(sections_dir)) if f.endswith('.toon')]
    
    ar_total = 0
    ar_text = 0
    header_total = 0
    
    for fname in section_files:
        fpath = os.path.join(sections_dir, fname)
        recs, arabic = count_file(fpath)
        ar_total += recs
        ar_text += arabic
        headers = get_all_hadith_headers(open(fpath, 'r', encoding='utf-8').read())
        header_total += sum(headers)
    
    print(f"\n{bid} {note}")
    print(f"  info.toon decl: {expected}")
    print(f"  Section files: {len(section_files)}")
    print(f"  Header declared total: {header_total}")
    print(f"  Actual records counted: {ar_total}")
    print(f"  With Arabic text: {ar_text}")
    
    if ar_total != header_total:
        print(f"  *** DISCREPANCY: header={header_total} vs actual={ar_total}")
    
    trans_dir = os.path.join(BASE, bid, 'translations')
    if os.path.isdir(trans_dir):
        for lang in sorted(os.listdir(trans_dir)):
            tsections = os.path.join(trans_dir, lang, 'sections')
            if os.path.isdir(tsections):
                t_total = 0
                for tf in sorted(os.listdir(tsections)):
                    if not tf.endswith('.toon'):
                        continue
                    recs, _ = count_file(os.path.join(tsections, tf))
                    t_total += recs
                print(f"  Translation {lang}: {t_total}")
