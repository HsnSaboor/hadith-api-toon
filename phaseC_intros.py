#!/usr/bin/env python3
import re,json,requests,sys
editions=['abudawud','aladab-almufrad','ibnmajah','mishkat','musnad-ahmad','nasai','nawawi','riyadussalihin','shamail-tirmidhi','virtues']
def fetch_intro(t,field):
    m=re.search(rf'{field}:\s*"(.*?)"', t, re.S); return m.group(1) if m else None
def set_intro(t,field,val):
    return re.sub(rf'{field}:\s*".*?"', f'{field}: "{val.replace(chr(34),chr(34)+chr(34))}"', t, count=1, flags=re.S)
def glm(src,lang):
    r=requests.post('http://localhost:8317/v1/chat/completions',headers={'Authorization':'Bearer sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh','Content-Type':'application/json'},
      json={'model':'databricks-glm/glm-5-2','messages':[{'role':'user','content':f'Translate this text into {lang} faithfully, keeping meaning and register. Output only the translation.\n\n'+src}]},timeout=180)
    return '[AI-translation] '+r.json()['choices'][0]['message']['content'].strip()
LANGMAP={'ur':'Urdu','bn':'Bengali','hi':'Hindi','fr':'French','id':'Indonesian','ru':'Russian','tr':'Turkish','ta':'Tamil','roman-ur':'Romanized Urdu'}
out=[]
for ed in editions:
    p=f'/home/saboor/code/hadith-api-toon/editions/{ed}/info.toon'
    t=open(p,encoding='utf-8',errors='replace').read()
    src=fetch_intro(t,'intro_en') or fetch_intro(t,'intro') or fetch_intro(t,'intro_ar')
    if not src or len(src)<30: out.append(f'{ed}: no source'); continue
    changed=0
    for lang in ('ur','bn','hi'):
        field=f'intro_{lang}'; cur=fetch_intro(t,field)
        if not cur: continue
        corrupt=False
        if re.search(r'[A-Za-z]{5,}',cur) and not re.search(r'hadith|islam|muslim',cur.lower()): corrupt=True
        if re.search(r'[一-鿿]',cur): corrupt=True
        if len(cur)>50 and cur[-1] not in '.?! ': corrupt=True
        if corrupt:
            try: t=set_intro(t,field,glm(src,LANGMAP[lang])); changed+=1
            except Exception as e: out.append(f'{ed} {lang}: err {e}')
    if changed: open(p,'w',encoding='utf-8').write(t)
    out.append(f'{ed}: re-translated {changed}')
print('\n'.join(out))
open('/tmp/phaseC.log','w').write('\n'.join(out))
