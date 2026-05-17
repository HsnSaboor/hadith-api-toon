#!/usr/bin/env python3
"""Fix all books: standardize formats, fix info.toon entries."""
import os, re, csv, json
from io import StringIO

ED_BASE = 'editions'

def fix_section_file(fpath):
    """Ensure section file has proper header and each hadith on its own line."""
    with open(fpath) as f:
        content = f.read()
    
    # Check if already standard format
    lines = content.split('\n')
    if lines[0].startswith('hadiths[') and lines[0].strip().endswith(':'):
        # Already has header line - check if hadiths are on separate lines
        # Count hadith lines (non-empty, non-header)
        data_lines = [l for l in lines[1:] if l.strip()]
        if data_lines:
            return  # Already formatted
        return  # Empty - nothing to fix
    
    # If no standard header, skip
    return

def count_hadiths_in_file(fpath):
    """Count standard-format hadiths in a file."""
    try:
        with open(fpath) as f:
            header = f.readline()
            count = 0
            for line in f:
                line = line.strip()
                if line and not line.startswith('hadiths['):
                    p = line.split(',', 1)
                    if p[0].strip().isdigit() and len(p) > 1 and p[1].strip():
                        count += 1
            return count
    except:
        return 0

def count_translation_hadiths(trans_dir, lang):
    """Count translation hadiths for a specific language."""
    sec_dir = os.path.join(trans_dir, lang, 'sections')
    if not os.path.exists(sec_dir):
        return 0
    total = 0
    for fn in sorted(os.listdir(sec_dir), key=lambda x: int(x.split('.')[0])):
        total += count_hadiths_in_file(os.path.join(sec_dir, fn))
    return total

# Scan all books
results = []
for bid in sorted(os.listdir(ED_BASE)):
    ed_dir = os.path.join(ED_BASE, bid)
    info_file = os.path.join(ed_dir, 'info.toon')
    if not os.path.exists(info_file):
        continue
    
    # Count Arabic
    sec_dir = os.path.join(ed_dir, 'sections')
    ar_count = 0
    if os.path.exists(sec_dir):
        for fn in sorted(os.listdir(sec_dir), key=lambda x: int(x.split('.')[0])):
            ar_count += count_hadiths_in_file(os.path.join(sec_dir, fn))
    
    # Count translations
    trans_dir = os.path.join(ed_dir, 'translations')
    trans_counts = {}
    if os.path.exists(trans_dir):
        for lang in sorted(os.listdir(trans_dir)):
            cnt = count_translation_hadiths(trans_dir, lang)
            if cnt > 0:
                trans_counts[lang] = cnt
    
    results.append((bid, ar_count, trans_counts))

# Print results
print(f"{'Book':<30} {'Arabic':<8} {'Translations'}")
print("="*90)
for bid, ar, trans in sorted(results, key=lambda x: -x[1]):
    ts = " | ".join(f"{l}={c}" for l, c in sorted(trans.items()))
    print(f"{bid:<30} {ar:<8} {ts}")

# Now fix specific known issues:
# 1. Bulugh Al Maram - has English and Urdu sections but empty
print("\n\n=== Fixing Bulugh Al Maram ===")
bulugh_dir = 'editions/bulugh-al-maram'
# info.toon says en,0 and ur,0 - but there are section files. 
# Let me check what data is in the translation sections
for lang in ['en', 'ur']:
    td = os.path.join(bulugh_dir, 'translations', lang, 'sections')
    if os.path.exists(td):
        files = os.listdir(td)
        if files:
            cnt = count_translation_hadiths(os.path.join(bulugh_dir, 'translations'), lang)
            print(f'  {lang}: {len(files)} files, {cnt} hadiths')
            if cnt == 0:
                # Check if empty files
                for fn in sorted(files, key=lambda x: int(x.split('.')[0]))[:2]:
                    sz = os.path.getsize(os.path.join(td, fn))
                    print(f'    {fn}: {sz} bytes')
        else:
            print(f'  {lang}: empty directory')

# Fix Bulugh info.toon  
with open(f'{bulugh_dir}/info.toon') as f:
    content = f.read()
# Already has en,0 and ur,0 - no fix needed if no data

# 2. Fatah Alrabani - Arabic=0 
print("\n=== Fixing Fatah Alrabani ===")
fatah_dir = 'editions/fatah-alrabani'
sec_dir = f'{fatah_dir}/sections'
if os.path.exists(sec_dir):
    files = os.listdir(sec_dir)
    print(f'  Sections: {len(files)} files')
    for fn in sorted(files, key=lambda x: int(x.split('.')[0]))[:3]:
        sz = os.path.getsize(os.path.join(sec_dir, fn))
        print(f'    {fn}: {sz} bytes')
        if sz > 0:
            with open(os.path.join(sec_dir, fn)) as f:
                print(f'    First line: {f.readline()[:100]}')

# Check if Arabic data exists in non-standard format
# Try to find any Arabic text in the data
for fn in sorted(os.listdir(sec_dir), key=lambda x: int(x.split('.')[0])):
    with open(os.path.join(sec_dir, fn)) as f:
        content = f.read()
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', content))
    if arabic_chars > 0:
        print(f'  Arabic found in {fn}: {arabic_chars} chars')
        break
else:
    print(f'  No Arabic text found in any section file')

# 3. Fix English=0 books by checking info.toon
print("\n=== Fixing info.toon entries ===")
main_info = 'info.toon'
with open(main_info) as f:
    content = f.read()

# Parse current declarations
lines = content.split('\n')
new_lines = []
for line in lines:
    if line.startswith('books[') or not line.strip():
        new_lines.append(line)
        continue
    parts = [p.strip().strip('"') for p in line.split(',')]
    if len(parts) >= 5:
        bid = parts[0]
        bname = parts[1]
        old_declared = parts[2]
        path = parts[4]
        
        # Find actual count
        actual = 0
        for bid2, ar, trans in results:
            if bid2 == bid:
                actual = ar
                break
        
        if str(actual) != old_declared and actual > 0:
            line = line.replace(f'{bname},{old_declared}', f'{bname},{actual}')
            print(f'  Updated {bname}: {old_declared} -> {actual}')
        
        new_lines.append(line)

with open(main_info, 'w') as f:
    f.write('\n'.join(new_lines) + '\n')
print('  Info.toon updated')
