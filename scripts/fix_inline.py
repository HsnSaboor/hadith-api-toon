#!/usr/bin/env python3
"""Fix inline CSV format for a specific book.
Usage: python3 fix_inline.py <book_id>
"""
import os, re, sys, csv
from io import StringIO

def fix_book(bid):
    sec_dir = f'editions/{bid}/sections'
    if not os.path.exists(sec_dir):
        print(f'No sections dir for {bid}')
        return 0
    
    total = 0
    for fn in sorted(os.listdir(sec_dir), key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 0):
        fpath = os.path.join(sec_dir, fn)
        with open(fpath) as f:
            content = f.read()
        
        # Check if inline (header ends with "}: " and first data follows on same line)
        idx = content.find('}: ')
        if idx < 0:
            continue  # already standard or different format
        
        before = content[:idx]
        after = content[idx+3:]
        
        # If there's content after the header on the same line, it needs fixing
        if not after.strip():
            continue
        
        # Split records: they're separated by ",,," or are sequential CSV records
        # Try splitting by ",,," first
        records_raw = re.split(r'",,,', after)
        
        rows = []
        for rec in records_raw:
            # Each record should be: number,arabic,grades,...
            # But they might be concatenated without separators
            # Try parsing as CSV
            try:
                reader = csv.reader(StringIO(rec))
                for row in reader:
                    if row and row[0].strip().isdigit():
                        rows.append(row)
            except:
                pass
        
        if not rows:
            # Fallback: try to find hadiths by number patterns
            nums = re.findall(r'(?<![,\d])(\d+)(?=\s*,"|\s*,)', after)
            if nums:
                print(f'  {fn}: found {len(nums)} numbers but parse failed')
            continue
        
        # Write fixed file
        new_lines = [f'hadiths[{len(rows)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:']
        for row in rows:
            while len(row) < 7:
                row.append('')
            new_lines.append(','.join(row))
        
        with open(fpath, 'w') as f:
            f.write('\n'.join(new_lines) + '\n')
        
        total += len(rows)
        if len(rows) > 0:
            print(f'  {fn}: {len(rows)} hadiths ({rows[0][0]}-{rows[-1][0]})')
    
    return total

# Also fix translation sections (JSON -> CSV)
def fix_translations(bid):
    trans_dir = f'editions/{bid}/translations'
    if not os.path.exists(trans_dir):
        return
    
    for lang in os.listdir(trans_dir):
        sec_dir = os.path.join(trans_dir, lang, 'sections')
        if not os.path.exists(sec_dir):
            continue
        
        for fn in sorted(os.listdir(sec_dir), key=lambda x: int(x.split('.')[0])):
            fpath = os.path.join(sec_dir, fn)
            with open(fpath) as f:
                content = f.read()
            
            # Check if JSON/Python dict format
            first_line = content.strip().split('\n')[0].strip()
            if first_line.startswith('{') and ("'hadithnumber'" in first_line or '"hadithnumber"' in first_line):
                # Python dict format
                entries = []
                for line in content.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = ast.literal_eval(line)
                        if isinstance(d, dict) and 'hadithnumber' in d:
                            entries.append((d['hadithnumber'], d.get('text', '')))
                    except:
                        pass
                
                if entries:
                    new_lines = [f'hadiths[{len(entries)}]{{hadithnumber,text}}:']
                    for hn, txt in entries:
                        new_lines.append(f'{hn},"{txt.replace(chr(34), chr(34)+chr(34))}"')
                    with open(fpath, 'w') as f:
                        f.write('\n'.join(new_lines) + '\n')
                    print(f'  trans/{lang}/{fn}: {len(entries)} hadiths')

if __name__ == '__main__':
    bid = sys.argv[1]
    import ast
    print(f'Fixing {bid}...')
    n = fix_book(bid)
    fix_translations(bid)
    print(f'Total: {n} Arabic hadiths fixed')
