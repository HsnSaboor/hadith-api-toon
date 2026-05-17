#!/usr/bin/env python3
"""Restructure lulu-wal-marjan edition to match website chapter structure.

Reads from scraped_data/lulu-wal-marjan_full.json and creates 55 section files.
"""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(__file__))

# Load scraped hadiths
with open(os.path.join(BASE, "scraped_data", "lulu-wal-marjan_full.json"), "r", encoding="utf-8") as f:
    scraped = json.load(f)

# 55 chapters from the website
CHAPTERS = [
    (0, "Introduction", "مقدمة", "مقدمہ", 4),
    (1, "Faith", "كِتَابُ الْإِيمَانِ", "کتاب: ایمان کا بیان", 129),
    (2, "Purification", "كِتَابُ الطَّهَارَةِ", "کتاب: طہارت کے مسائل", 34),
    (3, "Menstruation", "كِتَابُ الْحَيْضِ", "کتاب: حیض کے مسائل", 45),
    (4, "Prayer", "كِتَابُ الصَّلَاةِ", "کتاب: نماز کے مسائل", 85),
    (5, "Mosques and Places of Prayer", "كِتَابُ الْمَسَاجِدِ وَمَوَاضِعِ الصَّلَاةِ", "کتاب: مسجدوں اور نمازوں کی جگہوں کا بیان", 100),
    (6, "Travelers' Prayer and Shortening", "كِتَابُ صَلَاةِ الْمُسَافِرِينَ وَقَصْرِهَا", "کتاب: مسافروں کی نماز اور اس کے قصر کا بیان", 87),
    (7, "Friday Prayer", "كِتَابُ الْجُمُعَةِ", "کتاب: جمعہ کا بیان", 20),
    (8, "The Two Eids", "كِتَابُ الْعِيدَيْنِ", "کتاب: نماز عیدین کا بیان", 10),
    (9, "Prayer for Rain (Istisqa)", "كِتَابُ الِاسْتِسْقَاءِ", "کتاب: نماز استسقاء کا بیان", 5),
    (10, "Eclipse Prayer", "كِتَابُ الْكُسُوفِ", "کتاب: کسوف کی نماز کا بیان", 11),
    (11, "Funerals", "كِتَابُ الْجَنَائِزِ", "کتاب: جنازے کے مسائل", 36),
    (12, "Zakat", "كِتَابُ الزَّكَاةِ", "کتاب: زکوٰۃ کا بیان", 85),
    (13, "Fasting", "كِتَابُ الصِّيَامِ", "کتاب: روزہ کے مسائل", 75),
    (14, "I'tikaf", "كِتَابُ الِاعْتِكَافِ", "کتاب: اعتکاف کا بیان", 4),
    (15, "Hajj", "كِتَابُ الْحَجِّ", "کتاب: حج کے مسائل", 153),
    (16, "Marriage", "كِتَابُ النِّكَاحِ", "کتاب: نکاح کے مسائل", 32),
    (17, "Breastfeeding", "كِتَابُ الرَّضَاعِ", "کتاب: دودھ پلانے کے مسائل", 20),
    (18, "Divorce", "كِتَابُ الطَّلَاقِ", "کتاب: طلاق کے مسائل", 16),
    (19, "Lian", "كِتَابُ اللِّعَانِ", "کتاب: لعان کا بیان", 6),
    (20, "Emancipation of Slaves", "كِتَابُ الْعِتْقِ", "کتاب: بردہ آزاد کرنے کا بیان", 7),
    (21, "Trade and Commerce", "كِتَابُ الْبُيُوعِ", "کتاب: خریدو فروخت کے مسائل", 34),
    (22, "Muza'ara and Sharecropping", "كِتَابُ الْمُسَاقَاةِ", "کتاب: مساقات کے مسائل", 42),
    (23, "Inheritance", "كِتَابُ الْفَرَائِضِ", "کتاب: میراث کے احکام و مسائل", 4),
    (24, "Gifts and Charity", "كِتَابُ الْهِبَةِ", "کتاب: ہبہ اور صدقہ کے مسائل", 7),
    (25, "Wills and Testaments", "كِتَابُ الْوَصَايَا", "کتاب: وصیت کے مسائل", 9),
    (26, "Vows", "كِتَابُ النَّذْرِ", "کتاب: نذر کے مسائل", 5),
    (27, "Oaths", "كِتَابُ الْأَيْمَانِ", "کتاب: قسموں کے مسائل", 19),
    (28, "Qasama (Retaliation)", "كِتَابُ الْقَسَامَةِ", "کتاب: قسامہ کے مسائل", 12),
    (29, "Hudud (Prescribed Punishments)", "كِتَابُ الْحُدُودِ", "کتاب: حدود کے مسائل", 16),
    (30, "Judgements and Rulings", "كِتَابُ الْأَقْضِيَةِ", "کتاب: احکام اور فیصلوں کے مسائل", 10),
    (31, "Lost Items (Luqata)", "كِتَابُ اللُّقَطَةِ", "کتاب: گری پڑی چیز ملنے کے مسائل", 6),
    (32, "Jihad", "كِتَابُ الْجِهَادِ", "کتاب: جہاد کے مسائل", 64),
    (33, "Leadership and Governance", "كِتَابُ الْإِمَارَةِ", "کتاب: امارت کے بیان", 61),
    (34, "Hunting and Slaughtering", "كِتَابُ الصَّيْدِ وَالذَّبَائِحِ", "کتاب: شکار اور ذبح کے مسائل", 26),
    (35, "Sacrifices", "كِتَابُ الْأَضَاحِي", "کتاب: قربانی کے احکام و مسائل", 12),
    (36, "Drinks", "كِتَابُ الْأَشْرِبَةِ", "کتاب: پینے کی اشیاء کا بیان", 45),
    (37, "Dress and Adornment", "كِتَابُ اللِّبَاسِ وَالزِّينَةِ", "کتاب: لباس اور زینت کے بیان میں", 43),
    (38, "Manners and Etiquette", "كِتَابُ الْآدَابِ", "کتاب: آداب کا بیان", 16),
    (39, "Greetings (Salam)", "كِتَابُ السَّلَامِ", "کتاب: سلام کے مسائل", 53),
    (40, "Expressions and Wordings", "كِتَابُ الْأَلْفَاظِ", "کتاب: الفاظ ادب وغیرہ کا بیان", 5),
    (41, "Poetry", "كِتَابُ الشِّعْرِ", "کتاب: الشعر", 2),
    (42, "Dreams", "كِتَابُ الرُّؤْيَا", "کتاب: خوابوں کا بیان", 12),
    (43, "Virtues and Merits", "كِتَابُ الْفَضَائِلِ", "کتاب: فضائل و مناقب کا بیان", 73),
    (44, "Virtues of the Companions", "كِتَابُ فَضَائِلِ الصَّحَابَةِ", "کتاب: صحابہ کرام رضی اللہ عنہ کے فضائل", 112),
    (45, "Goodness and Righteousness", "كِتَابُ الْبِرِّ وَالصِّلَةِ", "کتاب: نیکی اور سلوک اور ادب کے مسائل", 43),
    (46, "Destiny (Qadr)", "كِتَابُ الْقَدَرِ", "کتاب: تقدیر کے مسائل", 10),
    (47, "Knowledge", "كِتَابُ الْعِلْمِ", "کتاب: کتاب العلم", 8),
    (48, "Remembrance, Supplication, Repentance", "كِتَابُ الذِّكْرِ وَالدُّعَاءِ", "کتاب: ذکر الٰہی، دعا، توبہ اور استغفار کے مسائل", 33),
    (49, "Repentance", "كِتَابُ التَّوْبَةِ", "کتاب: توبہ کرنے کا بیان", 18),
    (50, "Hypocrites and Their Characteristics", "كِتَابُ صِفَاتِ الْمُنَافِقِينَ", "کتاب: منافقوں کے اوصاف اور ان کے متعلق احکامات", 33),
    (51, "Paradise and Its Blessings", "كِتَابُ الْجَنَّةِ", "کتاب: جنت اور اس کی نعمتیں اور اہل جنت کے اوصاف", 32),
    (52, "Tribulations and Signs of the Hour", "كِتَابُ الْفِتَنِ", "کتاب: فتنوں اور قیامت کی نشانیوں کا بیان", 36),
    (53, "Heart-Softeners (Riqaq)", "كِتَابُ الرِّقَاقِ", "کتاب: دنیا سے نفرت دلانے اور دل کو نرم کرنے والی احادیث کا بیان", 28),
    (54, "Interpretation of the Quran", "كِتَابُ التَّفْسِيرِ", "کتاب: قرآن حکیم کی چند آیتوں کی تفسیر", 14),
]

# Calculate hadith ranges
ranges = []
start = 1
for ch in CHAPTERS:
    count = ch[4]
    end = start + count - 1
    ranges.append((ch[0], start, end))
    start = end + 1

# Verify total
total = sum(ch[4] for ch in CHAPTERS)
assert total == 1907, f"Expected 1907 total hadiths, got {total}"

EDITION_DIR = os.path.join(BASE, "editions", "lulu-wal-marjan")
SECTIONS_DIR = os.path.join(EDITION_DIR, "sections")

# Clear and recreate sections dir
os.makedirs(SECTIONS_DIR, exist_ok=True)
for f in os.listdir(SECTIONS_DIR):
    os.remove(os.path.join(SECTIONS_DIR, f))

# For hadith 0 (special case from intro/kitab al-fada'il), handle it
# The main book numbering starts at 1. Hadith 0 in scraped data is "Kitab al-Fada'il" related.

# Write section files for Arabic
for ch_id, start_h, end_h in ranges:
    ch_hadiths = []
    for num in range(start_h, end_h + 1):
        entry = scraped.get(str(num), {})
        arabic = entry.get("arabic", "")
        if arabic:
            # Normalize: strip newlines and extra whitespace from arabic
            arabic = ' '.join(arabic.split())
        ch_hadiths.append((num, arabic))
    
    filename = os.path.join(SECTIONS_DIR, f"{ch_id}.toon")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"hadiths[{len(ch_hadiths)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:\n")
        for num, arabic in ch_hadiths:
            if arabic:
                # Check if arabic contains comma - if so, wrap in quotes
                if ',' in arabic or '"' in arabic:
                    arabic_escaped = arabic.replace('"', '""')
                    f.write(f'{num},"{arabic_escaped}",,,,,\n')
                else:
                    f.write(f'{num},{arabic},,,,,\n')
            else:
                f.write(f'{num},,,,,,\n')
    
    print(f"Chapter {ch_id}: {len(ch_hadiths)} hadiths ({start_h}-{end_h})")

# Write info.toon
info_lines = [
    "",
    "translations[2]{language,sections,path}:",
    "en,0,translations/en",
    f"ur,{len(CHAPTERS)},translations/ur",
    "",
    f"sections[{len(CHAPTERS)}]{{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}}:",
]
for ch_id, name_en, name_ar, name_ur, _ in CHAPTERS:
    s, e = ranges[ch_id][1], ranges[ch_id][2]
    info_lines.append(f'{ch_id},"{name_en}","{name_ar}","Al-Lulu wal-Marjan","{name_en}","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","{name_ur}",{s},{e}')

with open(os.path.join(EDITION_DIR, "info.toon"), "w", encoding="utf-8") as f:
    f.write("\n".join(info_lines) + "\n")

print(f"\nDone! Created {len(CHAPTERS)} sections and updated info.toon")

# Now handle Urdu translations
UR_SECTIONS_DIR = os.path.join(EDITION_DIR, "translations", "ur", "sections")
os.makedirs(UR_SECTIONS_DIR, exist_ok=True)
for f in os.listdir(UR_SECTIONS_DIR):
    os.remove(os.path.join(UR_SECTIONS_DIR, f))

for ch_id, start_h, end_h in ranges:
    ch_hadiths = []
    for num in range(start_h, end_h + 1):
        entry = scraped.get(str(num), {})
        urdu = entry.get("urdu", "")
        if urdu:
            urdu = ' '.join(urdu.split())
        ch_hadiths.append((num, urdu))
    
    filename = os.path.join(UR_SECTIONS_DIR, f"{ch_id}.toon")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"hadiths[{len(ch_hadiths)}]{{hadithnumber,text}}:\n")
        for num, urdu in ch_hadiths:
            if urdu:
                # Handle quotes in urdu text
                if ',' in urdu or '"' in urdu:
                    urdu_escaped = urdu.replace('"', '""')
                    f.write(f'{num},"{urdu_escaped}"\n')
                else:
                    f.write(f'{num},{urdu}\n')
            else:
                f.write(f'{num},\n')
    
    print(f"Urdu Chapter {ch_id}: {len(ch_hadiths)} hadiths")

# Update Urdu metadata
with open(os.path.join(EDITION_DIR, "translations", "ur", "metadata.toon"), "w", encoding="utf-8") as f:
    f.write("""metadata:
  language: ur
  language_name: "Urdu"
  script: "Arabic"
  total_hadiths: 1907
  source: "Restructured from scraped data to match website chapter structure"
""")

print("\nUrdu translations restructured!")
