#!/usr/bin/env python3
import os
import glob

OUTPUT = 'VERIFICATION_SAMPLES.md'
f = open(OUTPUT, 'w', encoding='utf-8')
f.write('# Verification Samples - All Languages\\n\\n')
f.write('Checking ALL sections to find translations properly\\n\\n')

books = sorted([d for d in os.listdir('editions') if os.path.isdir(f'editions/{d}')])

for book in books:
    arabic_dir = f'editions/{book}/sections'
    trans_dir = f'editions/{book}/translations'
    
    if not os.path.exists(arabic_dir) or not os.path.exists(trans_dir):
        continue
    
    # Gather all Arabic hadiths
    arabic = {}
    for sf in glob.glob(f'{arabic_dir}/*.toon'):
        with open(sf) as fp:
            for line in fp:
                if line.startswith('hadiths['): continue
                p = line.split(',')
                if p and p[0].isdigit():
                    h = int(p[0])
                    if h not in arabic:
                        arabic[h] = p[1].strip().strip('"')
    
    if not arabic: continue
    
    langs = sorted([l for l in os.listdir(trans_dir) if os.path.isdir(f'{trans_dir}/{l}')])
    
    f.write(f'## {book}\\n')
    f.write(f'**Arabic hadiths:** {len(arabic)}\\n\\n')
    
    for lang in langs:
        lp = f'{trans_dir}/{lang}/sections'
        if not os.path.exists(lp): continue
        
        trans = {}
        for sf in glob.glob(f'{lp}/*.toon'):
            with open(sf) as fp:
                for line in fp:
                    if line.strip():
                        try:
                            e = eval(line.strip())
                            h = e.get('hadithnumber')
                            if isinstance(h, str): 
                                h = int(h)
                            t = e.get('text', '')
                            if h and t and h not in trans:
                                trans[h] = t[:100]  # Store preview
                        except: pass
        
        matched = sum(1 for h in arabic if h in trans)
        f.write(f'### {lang.upper()}\\n')
        f.write(f'- **Matched:** {matched}/{len(arabic)} ({100*matched/len(arabic):.1f}%)\n')
        
        # Show first 3 with preview
        if matched > 0:
            for h in sorted(arabic.keys())[:3]:
                if h in trans:
                    ar = arabic[h][:80]
                    tr = trans[h][:80]
                    f.write(f'  - H{h}: AR="...{ar}...", TR="...{tr}..."\n')
        f.write('\n')

f.close()
print(f'Done: wrote {OUTPUT}')