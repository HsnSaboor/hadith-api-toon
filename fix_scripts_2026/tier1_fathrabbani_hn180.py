#!/usr/bin/env python3
"""
Fix fath-al-rabbani HN180: EN/DE/ES had it filled with a copy-paste error
(near-duplicate of HN179's "relief of Islam" content); bn/fr/hi/id/roman-ur/
ru/ta/tr didn't have HN180 at all. UR's version (Allah predetermined
destinies 50,000 years before creating the heavens/earth) is confirmed
authentic, corroborated by Musnad Ahmad HN6579 (same narrator, same
content) - see DATASET_FIX_PLAN_2026.md and KNOWN_ISSUES.md fath-al-rabbani
item 4/5.

Own translations (not LLM) written for each target language, matching the
narrator-honorific and phrasing conventions already used elsewhere in this
same book (checked against neighboring rows HN181 for style/register before
writing). See translations dict below.

- EN: replaced (was wrong content) - scholarly text, no AI tag needed (this
  book's EN is predominantly scholarly; this row matches that register)
- DE/ES: replaced (were wrong content, were already [AI-translation] tagged
  copies of EN's error) - kept [AI-translation] tag, corrected content
- fr/bn/hi/id/roman-ur/ru/ta/tr: new row inserted (previously absent),
  [AI-translation] tagged to match this book's existing AI-language status
  for these 8 languages
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from toon_io import read_toon, write_toon, serialize_row

REPO = '/home/saboor/code/hadith-api-toon'

TRANSLATIONS = {
    'en': 'It was narrated that Abdullah ibn Amr ibn al-\'As (may Allah be pleased with him) said: The Messenger of Allah (peace be upon him) said: "Allah, the Exalted, determined the destinies fifty thousand years before He created the heavens and the earth."',
    'de': '[AI-translation] Es wurde überliefert, dass Abdullah ibn Amr ibn al-\'As (möge Allah mit ihm zufrieden sein) sagte: Der Gesandte Allahs (Friede sei mit ihm) sagte: „Allah, der Erhabene, bestimmte die Schicksale fünfzigtausend Jahre bevor Er die Himmel und die Erde erschuf."',
    'es': '[AI-translation] Se narró que Abdullah ibn Amr ibn al-\'As (que Allah esté complacido con él) dijo: El Mensajero de Allah (la paz sea con él) dijo: "Allah, el Exaltado, determinó los destinos cincuenta mil años antes de crear los cielos y la tierra."',
    'fr': '[AI-translation] Il a été rapporté qu\'Abdullah ibn Amr ibn al-\'As (qu\'Allah soit satisfait de lui) a dit : Le Messager d\'Allah (paix et bénédictions d\'Allah sur lui et sa famille) a dit : « Allah le Très-Haut a déterminé les destins cinquante mille ans avant de créer les cieux et la terre. »',
    'bn': '[AI-translation] আবদুল্লাহ ইবনে আমর ইবনে আল-আস (রাদিয়াল্লাহু আনহু) থেকে বর্ণিত, তিনি বলেন: রাসূলুল্লাহ (সাল্লাল্লাহু আলাইহি ওয়াসাল্লাম) বলেছেন: "আল্লাহ তাআলা আসমান ও জমিন সৃষ্টির পঞ্চাশ হাজার বছর পূর্বে তাকদীর নির্ধারণ করে রেখেছিলেন।"',
    'hi': '[AI-translation] अब्दुल्लाह इब्न अम्र इब्न अल-आस (रदिअल्लाहु अन्हु) से रिवायत है, उन्होंने कहा: रसूलुल्लाह (सल्लल्लाहु अलैहि व सल्लम) ने फरमाया: "अल्लाह तआला ने आसमानों और ज़मीन की तख़लीक़ से पचास हज़ार साल पहले तक़दीर का अंदाज़ा लगा लिया था।"',
    'id': '[AI-translation] Diriwayatkan dari Abdullah bin Amr bin al-\'Ash radhiyallahu \'anhu, ia berkata: Rasulullah shallallahu \'alaihi wa sallam bersabda: "Allah Ta\'ala telah menetapkan takdir lima puluh ribu tahun sebelum menciptakan langit dan bumi."',
    'roman-ur': '[AI-translation] Abdullāh ibn Amr ibn al-\'Ās raḍiyallāhu \'anhu se riwāyat hai, unhon ne kihā: Rasūlullāh sallallāhu \'alaihi wa sallam ne farmāyā: "Allāh Ta\'ālā ne āsmānon aur zamīn kī takhlīq se pachās hazār sāl pehle taqdīr kā andāza lagā liyā thā."',
    'ru': '[AI-translation] Передают со слов Абдуллаха ибн Амра ибн аль-Аса (да будет доволен им Аллах), что Посланник Аллаха (мир ему) сказал: «Поистине, Всевышний Аллах предопределил судьбы за пятьдесят тысяч лет до создания небес и земли».',
    'ta': '[AI-translation] அப்துல்லாஹ் இப்னு அம்ர் இப்னு அல்-ஆஸ் (ரலி) அவர்கள் அறிவிக்கின்றார்கள்: அல்லாஹ்வின் தூதர் (ஸல்) அவர்கள் கூறினார்கள்: "வானங்களையும் பூமியையும் படைப்பதற்கு ஐம்பதாயிரம் ஆண்டுகளுக்கு முன்பே அல்லாஹ் தஆலா விதிகளை நிர்ணயித்துவிட்டான்."',
    'tr': '[AI-translation] Abdullah bin Amr bin el-Âs (Allah ondan razı olsun)\'dan rivayet edildi ki: Resulullah (sallallahu aleyhi ve sellem) şöyle buyurdu: "Şüphesiz Allah Teâlâ, gökleri ve yeri yaratmadan elli bin yıl önce kaderleri takdir etmiştir."',
}

REPLACE_LANGS = {'en', 'de', 'es'}  # already had (wrong) HN180
INSERT_LANGS = {'fr', 'bn', 'hi', 'id', 'roman-ur', 'ru', 'ta', 'tr'}  # missing HN180


def main():
    for lang, text in TRANSLATIONS.items():
        path = f'{REPO}/editions/fath-al-rabbani/translations/{lang}/sections/3.toon'
        d = read_toon(path)
        new_spans = []
        inserted = False
        replaced = False
        for raw, fields in d['spans']:
            hn = fields[0].strip('"')
            if hn == '180' and lang in REPLACE_LANGS:
                new_fields = ['180', text]
                new_spans.append((serialize_row(new_fields), new_fields))
                replaced = True
                continue
            new_spans.append((raw, fields))
            if hn == '179' and lang in INSERT_LANGS:
                new_fields = ['180', text]
                new_spans.append((serialize_row(new_fields), new_fields))
                inserted = True

        if lang in REPLACE_LANGS:
            assert replaced, f'{lang}: HN180 not found to replace'
            action = 'replaced'
        else:
            assert inserted, f'{lang}: could not insert after HN179 (not found)'
            action = 'inserted'

        write_toon(path, d['header_line'], d['block_name'], d['columns'], new_spans)
        print(f'{lang}: {action} HN180, new row count = {len(new_spans)}')


if __name__ == '__main__':
    main()
