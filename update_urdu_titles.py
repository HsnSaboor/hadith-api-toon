import re
import csv
import io
import json

toc_text = """
1والدینكتاب الْوَالِدَيْنِ1 تا 46
2صلہ رحمیكتاب صِلَةِ الرَّحِمِ47 تا 73
3موالی (آزاد کردہ غلام)كتاب مَوَالِي74 تا 75
4بیٹیوں کی پرورشكتاب عول البنات76 تا 83
5بچوں کی دیکھ بھالكتاب رعاية الأولاد84 تا 100
6پڑوسی / ہمسائےكتاب الْجَارِ101 تا 128
7سخاوت اور یتیمكتاب الْكَرَمِ وَ يَتِيمٌ129 تا 142
8بچوں کی وفاتكتاب موت الأولاد143 تا 155
9ماتحتوں سے حسن سلوکكتاب الملكة156 تا 211
10سرپرستی اور نگہبانیكتاب الرعاية212 تا 220
11نیکی اور بھلائیكتاب الْمَعْرُوفِ221 تا 237
12لوگوں سے خندہ پیشانی سے ملناكتاب الِانْبِسَاطِ إِلَى النَّاسِ238 تا 255
13مشورہ کرناكتاب الْمَشُورَةِ256 تا 259
14حسن اخلاقكتاب حسن الخلق-
15لعنت کرناكتاب اللعن309 تا 332
16تعریف کرناكتاب المدح333 تا 343
17ملاقات کے لیے جاناكتاب الزِّيَارَةِ344 تا 352
18بزرگوں کا احترامكتاب الأكَابِرِ353 تا 361
19بچوں کا بیانكتاب الصَّغِيرِ362 تا 371
20رحم دلی / شفقتكتاب رَحْمَةِ372 تا 384
21باہمی تعلقاتكتاب ذات البين385 تا 396
22قطع تعلق / بول چال چھوڑناكتاب الهجر397 تا 414
23مشورہ دینا / رہنمائیكتاب الإشارة415 تا 418
24گالی گلوچ / برا بھلا کہناكتاب السِّبَابِ419 تا 441
25تعمیرات میں فضول خرچیكتاب السَّرَفِ فِي الْبِنَاءِ442 تا 461
26نرمی / شفقتكتاب الرِّفْقِ462 تا 474
27دنیاوی امور کا خیال رکھناكتاب الاعتناء بالدنيا-
28ظلمكتاب الظُّلْم483 تا 490
29بیماروں کی عیادتكتاب عيادة المرضى491 تا 537
30عمومی برتاؤكتاب التصرف العام538 تا 603
31دعاكتاب الدعاء604 تا 738
32مہمان اور خرچ کرناكتاب الضيف والنفقة739 تا 753
33اقوالكتاب الأقوال754 تا 810
34نامكتاب الأسْمَاءِ811 تا 841
35کنیتكتاب الكُنْيَةِ842 تا 855
36شاعریكتاب الشِّعْرِ856 تا 874
37گفتگو / کلامكتاب الْكَلامِ875 تا 887
38معاملات کا انجامكتاب عاقبة الأمور888 تا 906
39بدشگونیكتاب الطيرة907 تا 918
40چھینکنا اور جمائی لیناكتاب الْعُطَاسَ والتثاؤب919 تا 951
41حرکات و اشاراتكتاب الحركات952 تا 964
42سلامكتاب السَّلامِ965 تا 1050
43اجازت طلب کرناكتاب الاسْتِئْذَانُ1051 تا 1100
44اہل کتابكتاب أَهْلِ الْكِتَابِ1101 تا 1116
45خطوط / رسائلكتاب الرَّسَائِلِ1117 تا 1135
46مجالسكتاب الْمَجَالِسِ1136 تا 1152
47لوگوں کے ساتھ برتاؤكتاب تعامل الناس1153 تا 1174
48بیٹھنا اور لیٹناباب الجلوس والاستلقاء1175 تا 1198
49صبح اور شامكتاب الصباح والمساء1199 تا 1204
50سونا اور رات گزارناكتاب النوم والمبيت-
51جانوركتاب الْبَهَائِمِ-
52قیلولہ (دوپہر کا آرام)كتاب الْقَائِلَةِ1238 تا 1243
53ختنہكتاب الْخِتَانِ-
54جوا اور اس جیسے کھیلكتاب القمار ونحوه1259 تا 1281
55پہچان / معرفتكتاب المعرفة-
56بے جا مداخلت اور سختیكتاب الفضول والجفاء-
57غصہكتاب الْغَضَبِ1317 تا 1322
"""

urdu_titles = {}
for line in toc_text.strip().split("\n"):
    match = re.match(r'^(\d+)(.*?)(كتاب|باب)', line)
    if match:
        sec_id = int(match.group(1))
        ur_title = match.group(2).strip()
        urdu_titles[sec_id] = ur_title

info_path = "/home/saboor/code/hadith-api-toon/editions/aladab-almufrad/info.toon"
new_info_lines = []
in_sections = False

sections = []

with open(info_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("sections["):
            in_sections = True
            new_info_lines.append(line)
            continue
            
        if in_sections and line.startswith('"'):
            reader = csv.reader(io.StringIO(line.strip()))
            row = list(next(reader))
            sec_id = int(row[0].strip())
            
            # Replace name_ur (index 9) with new urdu title
            if sec_id in urdu_titles:
                row[9] = urdu_titles[sec_id]
            
            sec = {
                "id": str(sec_id),
                "name_ur": row[9],
                "first": int(row[10]),
                "last": int(row[11])
            }
            sections.append(sec)
            
            r_str = ",".join(f'"{str(c)}"' for c in row)
            new_info_lines.append(r_str + "\n")
        else:
            new_info_lines.append(line)

with open(info_path, "w", encoding="utf-8") as f:
    f.writelines(new_info_lines)

ur_file_path = "/home/saboor/code/hadith-api-toon/sunnah.com-download/adab/ur.json"
with open(ur_file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    h_str = str(item.get("hadithnumber", ""))
    match = re.search(r'\d+', h_str)
    if match:
        h_num = int(match.group())
        found_sec = None
        for sec in sections:
            if sec["first"] <= h_num <= sec["last"]:
                found_sec = sec
                break
        
        if found_sec:
            item["book_name"] = found_sec["name_ur"]

with open(ur_file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Urdu titles successfully updated in info.toon and ur.json")
