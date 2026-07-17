#!/usr/bin/env python3
"""GAPS14 Phase A — mechanical safe fixes. Idempotent. Logs changes."""
import os, re, unicodedata, glob, sys

ED = '/home/saboor/code/hadith-api-toon/editions'
log = []
def L(s): log.append(s); print(s)

BIDI = {0x200E,0x200F,0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069}

# ---- A1: NFC normalize repo-wide ----
def A1_nfc():
    n=0
    for f in glob.glob(f'{ED}/**/*.toon', recursive=True):
        t = open(f, encoding='utf-8').read()
        nfc = unicodedata.normalize('NFC', t)
        if nfc != t:
            open(f, 'w', encoding='utf-8').write(nfc); n+=1
    L(f'A1 NFC: normalized {n} files')

# ---- A2: bidi strip (nasai sec36 + ur) ----
def A2_bidi():
    files=[f'{ED}/nasai/sections/36.toon', f'{ED}/nasai/translations/ur/sections/36.toon']
    n=0
    for f in files:
        if not os.path.exists(f): continue
        t=open(f,encoding='utf-8').read()
        nt=''.join(c for c in t if ord(c) not in BIDI)
        if nt!=t: open(f,'w',encoding='utf-8').write(nt); n+=1; L(f'  bidi stripped {f}')
    L(f'A2 bidi: {n} files')

# ---- A3: scraping residue strip (per-edition regex) ----
RESIDUE = {
 'ibnmajah': (r'\n?Sunnan e Ibn e Maja Hadees: \d+ Arabic Hadees: \d+$', ['translations/en/sections']),
 'nasai': (r'n?Sunnan e Nisai Hadees: \d+ Arabic Hadees: \d+', ['translations/en/sections','translations/fr/sections','translations/id/sections','translations/tr/sections']),
 'shamail-tirmidhi': (r'\n?شمائل\s*ترمذی\s*حدیث\s*:\s*\d+\s*عربی\s*حدیث\s*:\s*$', ['translations/ur/sections']),
 'silsila-sahih': (r'Al-Silsila-tu-Ahadees-e-Sahiha Hadees: \d+ Arabic Hadees:?\s*$', ['translations/en/sections']),
 'tirmidhi': (r'Jam e Tirmizi Hadees: \d+ Arabic Hadees: \d+', ['translations/en/sections','translations/roman-ur/sections']),
 'malik': (r'Hadees: \d+ Arabic Hadees: \d+$', ['translations/fr/sections']),  # corrected \d+
 'muajam-tabarani-saghir': (r'Hadees: \d+ Arabic Hadees: \d+$', ['translations/ur/sections']),  # corrected \d+
}
def A3_residue():
    total=0
    for ed,(pat,dirs) in RESIDUE.items():
        rx=re.compile(pat); ec=0
        for d in dirs:
            base=f'{ED}/{ed}/{d}'
            if not os.path.isdir(base): continue
            for f in os.listdir(base):
                if not f.endswith('.toon'): continue
                p=f'{base}/{f}'
                t=open(p,encoding='utf-8').read()
                nt=rx.sub('', t)
                if nt!=t:
                    open(p,'w',encoding='utf-8').write(nt); ec+=1
        if ec: L(f'  residue {ed}: {ec} files'); total+=ec
    L(f'A3 residue: {total} files')

# ---- A4: grade canonicalization (mechanical subset) ----
def fix_grades_whole_file(ed, subs):
    """subs: list of (find_str, repl_str). Whole-file replace on AR sections."""
    sd=f'{ED}/{ed}/sections'
    if not os.path.isdir(sd): return 0
    n=0
    for f in os.listdir(sd):
        if not f.endswith('.toon'): continue
        p=f'{sd}/{f}'; t=open(p,encoding='utf-8').read(); o=t
        for a,b in subs: t=t.replace(a,b)
        if t!=o: open(p,'w',encoding='utf-8').write(t); n+=1
    return n

def fix_grade_field_prefix(ed, prefix):
    """strip `prefix` from start of grades field (3rd) in AR sections."""
    sd=f'{ED}/{ed}/sections'
    if not os.path.isdir(sd): return 0
    n=0
    for f in os.listdir(sd):
        if not f.endswith('.toon'): continue
        p=f'{sd}/{f}'; lines=open(p,encoding='utf-8',errors='replace').read().split('\n'); out=[]; ch=False
        for ln in lines:
            if ln.startswith('"'):
                p2=ln.split('","')
                if len(p2)>=3 and p2[2].startswith(prefix):
                    p2[2]=p2[2][len(prefix):]; ln='","'.join(p2); ch=True
            out.append(ln)
        if ch: open(p,'w',encoding='utf-8').write('\n'.join(out)); n+=1
    return n

def A4_grades():
    ij = fix_grades_whole_file('ibnmajah', [('Da’if',"Da'if"),('Da,if',"Da'if"),('Da`if',"Da'if")])
    na = fix_grades_whole_file('nasai', [('Da if',"Da'if"),('"Daif"','"Da\'if"')])
    kh = fix_grade_field_prefix('sahih-ibn-khuzaymah', ': ')
    L(f'A4 grades: ibnmajah {ij}, nasai {na}, khuzaymah-colon {kh} files')

# ---- A5: intro byte-replace ----
def A5_intro():
    subs={
     f'{ED}/bayhaqi/info.toon':[('سunan','سنن')],
     f'{ED}/bulugh-al-maram/info.toon':[('\\n','\n')],
     f'{ED}/nasai-kubra/info.toon':[('سunan','سنن'),('آرنج','ترتیب')],
     f'{ED}/musannaf-ibn-abi-shaybah/info.toon':[('کو含اتے','رکھتا'),('آرنج','ترتیب')],
    }
    n=0
    for p,slist in subs.items():
        if not os.path.exists(p): continue
        t=open(p,encoding='utf-8').read(); o=t
        for a,b in slist: t=t.replace(a,b)
        if t!=o: open(p,'w',encoding='utf-8').write(t); n+=1; L(f'  intro fixed {p}')
    L(f'A5 intro: {n} files')

# ---- A6: silsila narrator_chain clear (numeric -> '') ----
def A6_silsila():
    p=f'{ED}/silsila-sahih/sections/1.toon'
    if not os.path.exists(p): L('A6 silsila: file missing'); return
    lines=open(p,encoding='utf-8',errors='replace').read().split('\n'); out=[]; n=0
    for ln in lines:
        if ln.startswith('"'):
            p2=ln.split('","')
            # 7-field AR: narrator_chain is field index 5
            if len(p2)>=6 and re.fullmatch(r'\d+', p2[5].strip('"').strip()):
                p2[5]=''; ln='","'.join(p2); n+=1
        out.append(ln)
    open(p,'w',encoding='utf-8').write('\n'.join(out))
    L(f'A6 silsila: cleared {n} numeric narrator_chain rows')

# ---- A7: muajam header 522->520 ----
def A7_muajam():
    p=f'{ED}/muajam-tabarani-saghir/translations/en/sections/2.toon'
    if not os.path.exists(p): L('A7 muajam: file missing'); return
    lines=open(p,encoding='utf-8',errors='replace').read().split('\n')
    rows_n=sum(1 for ln in lines if ln.startswith('"'))
    lines[0]=re.sub(r'hadiths\[\d+\]', f'hadiths[{rows_n}]', lines[0])
    open(p,'w',encoding='utf-8').write('\n'.join(lines))
    L(f'A7 muajam: header -> hadiths[{rows_n}]')

if __name__=='__main__':
    A1_nfc()
    A2_bidi()
    A3_residue()
    A4_grades()
    A5_intro()
    A6_silsila()
    A7_muajam()
    open('/tmp/gaps14_phaseA.log','w').write('\n'.join(log))
    print('=== Phase A complete ===')
