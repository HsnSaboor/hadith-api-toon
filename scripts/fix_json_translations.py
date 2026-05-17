#!/usr/bin/env python3
"""Fix all JSON-format translations across all books."""
import os, re, ast

books_with_json = {
    'bulugh-al-maram': {'en': 1730, 'ur': 192},
    'musnad-ahmed': {'en': 1331, 'ur': 24865},
    'sahih-ibn-khuzaymah': {'ur': 4026},
    'shamail-tirmazi': {'en': 724, 'ur': 388},
    'aladab-almufrad': {},  # already fixed
}

total_fixed = 0

for bid, langs in books_with_json.items():
    for lang in langs:
        sec_dir = f'editions/{bid}/translations/{lang}/sections'
        if not os.path.exists(sec_dir):
            continue
        
        print(f'\n{bid} ({lang}):')
        all_entries = []
        files_processed = 0
        
        for fn in sorted(os.listdir(sec_dir), key=lambda x: int(x.split('.')[0])):
            fpath = os.path.join(sec_dir, fn)
            with open(fpath) as f:
                content = f.read()
            
            # Check if Python dict format (starts with {'hadithnumber' or {"hadithnumber")
            first_line = content.strip().split('\n')[0].strip()
            if not (first_line.startswith('{') and "'hadithnumber'" in first_line):
                continue  # already CSV or unknown format
            
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
            
            if not entries:
                continue
            
            all_entries.extend(entries)
            
            # Write standard format
            new_lines = [f'hadiths[{len(entries)}]{{hadithnumber,text}}:']
            for hn, txt in entries:
                escaped = txt.replace('"', '""')
                new_lines.append(f'{hn},"{escaped}"')
            
            with open(fpath, 'w') as f:
                f.write('\n'.join(new_lines) + '\n')
            
            files_processed += 1
        
        print(f'  Fixed {files_processed} files, {len(all_entries)} hadiths')
        total_fixed += len(all_entries)

print(f'\nTotal hadiths converted: {total_fixed}')
PYEOF
