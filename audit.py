import os
import csv
import io
import re

BASE = "/home/saboor/code/hadith-api-toon/editions"

def count_hadiths_in_file(filepath):
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('hadiths[') or line.startswith('metadata:') or line.startswith('---'):
            continue
        try:
            reader = csv.reader(io.StringIO(line))
            for row in reader:
                if len(row) >= 2:
                    first = row[0].strip()
                    second = row[1].strip().strip('"').strip("'").strip()
                    if first.isdigit() and second:
                        count += 1
        except:
            pass
    return count

def count_hadiths_in_sections(sections_dir):
    if not os.path.isdir(sections_dir):
        return None, {}, set()
    total = 0
    section_counts = {}
    files = sorted(os.listdir(sections_dir))
    for fname in files:
        if fname.endswith('.toon'):
            fpath = os.path.join(sections_dir, fname)
            c = count_hadiths_in_file(fpath)
            sid = fname.replace('.toon', '')
            section_counts[sid] = c
            total += c
    return total, section_counts, set(section_counts.keys())

# Read info.toon
books = []
with open('/home/saboor/code/hadith-api-toon/info.toon', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('books['):
            continue
        # Remove line number prefix
        line = re.sub(r'^\d+:\s*', '', line)
        parts = line.split(',')
        if len(parts) >= 5:
            book_id = parts[0].strip()
            name = parts[1].strip()
            declared = parts[2].strip()
            langs = parts[3].strip().strip('"')
            path = parts[4].strip()
            try:
                declared_num = int(declared)
            except:
                declared_num = 0
            books.append((book_id, name, declared_num, langs, path))

# Audit
print(f"{'Book ID':<30} {'Decl':>5} {'Arabic':>7} {'Lang Counts'}")
print("=" * 100)
for book_id, name, declared, langs, path in books:
    ar_count, ar_section_counts, ar_section_files = count_hadiths_in_sections(os.path.join(BASE, book_id, 'sections'))
    
    trans_info = {}
    
    trans_dir = os.path.join(BASE, book_id, 'translations')
    if os.path.isdir(trans_dir):
        for lang in sorted(os.listdir(trans_dir)):
            lang_sections = os.path.join(trans_dir, lang, 'sections')
            if os.path.isdir(lang_sections):
                lang_count, _, lang_section_files = count_hadiths_in_sections(lang_sections)
                if lang_count is not None:
                    trans_info[lang] = (lang_count, lang_section_files)
    
    ar_str = f"{ar_count}" if ar_count is not None else "MISSING"
    
    issues = []
    
    # Check declared vs actual Arabic
    if ar_count is not None and abs(ar_count - declared) > 1:
        issues.append(f"DECL({declared}) != ACT({ar_count})")
    
    # Check translations for issues
    for lang, (lc, lsf) in sorted(trans_info.items()):
        if lc == 0 and lang in langs.split(','):
            issues.append(f"{lang}=0!")
        # Check missing sections
        missing = ar_section_files - lsf
        extra = lsf - ar_section_files
        if missing and lang in langs.split(','):
            issues.append(f"{lang} miss sections: {sorted(missing, key=lambda x: [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', x)])[:3]}")
    
    lang_str = " ".join(f"{k}={v[0]}" for k, v in sorted(trans_info.items()))
    
    print(f"{book_id:<30} {declared:>5} {ar_str:>7}  {lang_str}")
    if issues:
        for iss in issues:
            print(f"  {'':<30} {'ISSUE:':>5} {iss}")
    print()
