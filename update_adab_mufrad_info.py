import re
import os
import json
from deep_translator import GoogleTranslator

toc_text = """
1Parentsكتاب الْوَالِدَيْنِ1to46
2Ties of Kinshipكتاب صِلَةِ الرَّحِمِ47to73
3Mawlas (Clients of Manumission)كتاب مَوَالِي74to75
4Looking after girlsكتاب عول البنات76to83
5Looking after childrenكتاب رعاية الأولاد84to100
6Neighboursكتاب الْجَارِ101to128
7Generosity and Orphansكتاب الْكَرَمِ وَ يَتِيمٌ129to142
8Children's Deathكتاب موت الأولاد143to155
9Being a masterكتاب الملكة156to211
10Supervisionكتاب الرعاية212to220
11Good Conductكتاب الْمَعْرُوفِ221to237
12Cheerfulness Towards Peopleكتاب الِانْبِسَاطِ إِلَى النَّاسِ238to255
13Consultationكتاب الْمَشُورَةِ256to259
14Excellence in Characterكتاب حسن الخلق
15Cursingكتاب اللعن309to332
16Praiseكتاب المدح333to343
17Visitationكتاب الزِّيَارَةِ344to352
18The Elderlyكتاب الأكَابِرِ353to361
19Childrenكتاب الصَّغِيرِ362to371
20Mercyكتاب رَحْمَةِ372to384
21Social Behaviourكتاب ذات البين385to396
22Abandonmentكتاب الهجر397to414
23Advisingكتاب الإشارة415to418
24Disparagingكتاب السِّبَابِ419to441
25Extravagance in Buildingكتاب السَّرَفِ فِي الْبِنَاءِ442to461
26Compassionكتاب الرِّفْقِ462to474
27Attending to this worldكتاب الاعتناء بالدنيا
28Injusticeكتاب الظُّلْم483to490
29Visiting the Illكتاب عيادة المرضى491to537
30General Behaviorكتاب التصرف العام538to603
31Supplicationكتاب الدعاء604to738
32Guests and Spendingكتاب الضيف والنفقة739to753
33Sayingsكتاب الأقوال754to810
34Namesكتاب الأسْمَاءِ811to841
35Kunyasكتاب الكُنْيَةِ842to855
36Poetryكتاب الشِّعْرِ856to874
37Wordsكتاب الْكَلامِ875to887
38Consequencesكتاب عاقبة الأمور888to906
39Omensكتاب الطيرة907to918
40Sneezing and Yawningكتاب الْعُطَاسَ والتثاؤب919to951
41Gesturesكتاب الحركات952to964
42Greetingsكتاب السَّلامِ965to1050
43Asking Permissionكتاب الاسْتِئْذَانُ1051to1100
44The People of the Bookكتاب أَهْلِ الْكِتَابِ1101to1116
45Lettersكتاب الرَّسَائِلِ1117to1135
46Gatheringsكتاب الْمَجَالِسِ1136to1152
47Behaviour with peopleكتاب تعامل الناس1153to1174
48Sitting and lying downباب الجلوس والاستلقاء1175to1198
49Mornings and eveningsكتاب الصباح والمساء1199to1204
50Sleep and night lodgingكتاب النوم والمبيت
51Animalsكتاب الْبَهَائِمِ
52Midday Napsكتاب الْقَائِلَةِ1238to1243
53Circumcisionكتاب الْخِتَانِ
54Betting and similar pastimesكتاب القمار ونحوه1259to1281
55Recognitionكتاب المعرفة
56Meddling and Harshnessكتاب الفضول والجفاء
57Angerكتاب الْغَضَبِ1317to1322
"""

sections_meta = {}
for line in toc_text.strip().split('\n'):
    match = re.match(r'^(\d+)(.*?)(كتاب .*?|باب .*?)(?:\d+to\d+)?$', line)
    if match:
        sec_id = int(match.group(1))
        en_name = match.group(2).strip()
        ar_name = match.group(3).strip()
        sections_meta[sec_id] = {'en': en_name, 'ar': ar_name}

# Translate to bn, fr, id, ru, tr, ur
langs_to_translate = ['bn', 'fr', 'id', 'ru', 'tr', 'ur']
print("Translating names...")
for lang in langs_to_translate:
    print(f"Translating {lang}...")
    translator = GoogleTranslator(source='en', target=lang)
    for sec_id, names in sections_meta.items():
        try:
            names[lang] = translator.translate(names['en'])
        except Exception as e:
            names[lang] = names['en']

print("Extracting true boundaries from sections files...")
for sec_id in range(1, 58):
    file_path = f"/home/saboor/code/hadith-api-toon/editions/aladab-almufrad/sections/{sec_id}.toon"
    first = None
    last = None
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith('"'):
                parts = line.split('","')
                hnum = parts[0].strip('"')
                if not first:
                    first = hnum
                last = hnum
    sections_meta[sec_id]['first'] = first
    sections_meta[sec_id]['last'] = last

info_path = "/home/saboor/code/hadith-api-toon/editions/aladab-almufrad/info.toon"
with open(info_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_sections = False
for line in lines:
    if line.startswith("sections["):
        new_lines.append("sections[57]{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}:\n")
        in_sections = True
        
        for sec_id in range(1, 58):
            m = sections_meta[sec_id]
            # Replace double quotes to avoid breaking toon
            name_ar = m['ar'].replace('"', '')
            name_bn = m['bn'].replace('"', '')
            name_en = m['en'].replace('"', '')
            name_fr = m['fr'].replace('"', '')
            name_id = m['id'].replace('"', '')
            name_ru = m['ru'].replace('"', '')
            name_tr = m['tr'].replace('"', '')
            name_ur = m['ur'].replace('"', '')
            first = m['first']
            last = m['last']
            
            row = f'" {sec_id:2}","{name_en}","{name_ar}","{name_bn}","{name_en}","{name_fr}","{name_id}","{name_ru}","{name_tr}","{name_ur}","{first}","{last}","{first}","{last}"\n'
            new_lines.append(row)
    elif not in_sections:
        new_lines.append(line)

with open(info_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("info.toon updated successfully.")

