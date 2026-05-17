#!/usr/bin/env python3
"""Debug why specific lulu hadiths don't match Bukhari/Muslim"""
import os, re

BASE = os.path.dirname(os.path.dirname(__file__))
os.chdir(BASE)

def normalize(text):
    text = re.sub(r'[^\u0621-\u064A\s]', '', text)
    text = text.replace('\u0649', '\u064A')
    text = text.replace('\u0626', '\u0625')
    text = text.replace('\u0623', '\u0627')
    text = text.replace('\u0625', '\u0627')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_prophetic_saying(text):
    norm = normalize(text)
    patterns = [
        r'قال\s*(?:رسول\s+الله|النبي)\s*[^:]*:(.*)',
        r'قال\s*(?:رسول\s+الله|النبي)\s*(.*)',
        r'يقول\s*(?:رسول\s+الله|النبي)\s*(.*)',
        r'أن\s+(?:رسول\s+الله|النبي)\s*قال\s*(.*)',
        r'سمعت\s+(?:رسول\s+الله|النبي)\s*(?:يقول)?\s*(.*)',
    ]
    for pat in patterns:
        m = re.search(pat, norm)
        if m:
            content = m.group(1).strip()
            if len(content) > 15:
                return content
    return norm

lulu_7 = 'حديث أبي أيوبَ الأَنصاريّ رضي الله عنه أَنَّ رجلاً قال: يا رسول الله أخبرني بعمل يُدْخِلُني الجنة، فقال القوم: مَا لَهُ مَالَه فقال رسولُ اللهِ صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ : أَرَبٌ مَّا لَهُ فقال النبيُّ صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ : تعبُدُ اللهَ لا تُشْرِكُ بهِ شيئًا وتُقيمُ الصَّلاةَ وَتُؤْتِي الزكاةَ وَتَصِلُ الرَّحِمَ ذرْها قَال كأنّه كانَ عَلى رَاحِلَتِهِ'
lulu_core = extract_prophetic_saying(lulu_7)
print(f'Lulu 7 core ({len(lulu_core)} chars):')
print(f'  {lulu_core[:200]}')

print('\nSearching Bukhari...')
found = False
for fn in sorted(os.listdir('editions/bukhari/sections'), key=lambda x: int(x.split('.')[0])):
    with open(f'editions/bukhari/sections/{fn}') as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',',1)
                if p[0].strip().isdigit():
                    arabic = p[1].strip() if len(p)>1 else ''
                    bt = extract_prophetic_saying(arabic)
                    for i in range(0, max(1, len(lulu_core)-50), 15):
                        phrase = lulu_core[i:i+50]
                        if len(phrase) >= 45 and phrase in bt:
                            print(f'  Found in Bukhari {p[0].strip()}')
                            print(f'  Matched phrase: {phrase}')
                            # Get English
                            for fn2 in sorted(os.listdir('editions/bukhari/translations/en/sections'), key=lambda x: int(x.split('.')[0])):
                                with open(f'editions/bukhari/translations/en/sections/{fn2}') as f2:
                                    for line2 in f2:
                                        if line2.startswith(f'{p[0].strip()},'):
                                            print(f'  English: {line2[line2.find(",")+1:200]}')
                                            break
                            found = True
                            break
                    if found:
                        break
        if found:
            break
    if found:
        break

if not found:
    print('  NOT found in Bukhari')
    print('\nSearching Muslim...')
    for fn in sorted(os.listdir('editions/muslim/sections'), key=lambda x: int(x.split('.')[0])):
        with open(f'editions/muslim/sections/{fn}') as f:
            for line in f:
                if line.strip() and not line.startswith('hadiths['):
                    p = line.split(',',1)
                    if p[0].strip().isdigit():
                        arabic = p[1].strip() if len(p)>1 else ''
                        bt = extract_prophetic_saying(arabic)
                        for i in range(0, max(1, len(lulu_core)-50), 15):
                            phrase = lulu_core[i:i+50]
                            if len(phrase) >= 45 and phrase in bt:
                                print(f'  Found in Muslim {p[0].strip()}')
                                found = True
                                break
                        if found:
                            break
            if found:
                break
        if found:
            break
    if not found:
        print('  NOT found in Muslim either')
