#!/usr/bin/env python3
import csv
import os
import re

BASE_DIR = "/home/saboor/code/hadith-api-toon"
EDITIONS_DIR = os.path.join(BASE_DIR, "editions")

# Aligned Arabic edits
ARABIC_EDITS = {
    "lulu-wal-marjan": {
        "2": {
            "142": {
                "arabic": "أَنَّ رَسُولَ اللَّهِ ﷺ قَالَ لَوْلاَ أَنْ أَشُقَّ عَلَى أُمَّتِي أَوْ عَلَى النَّاسِ لأَمَرْتُهُمْ بِالسِّوَاكِ مَعَ كُلِّ صَلاَةٍ",
                "chain": "حَدَّثَنَا عَبْدُ اللَّهِ بْنُ يُوسُفَ قَالَ أَخْبَرَنَا مَالِكٌ عَنْ أَبِي الزِّنَادِ عَنِ الأَعْرَجِ عَنْ أَبِي هُرَيْرَةَ ؓ"
            }
        }
    },
    "bayhaqi": {
        "6": {
            "6519": {
                "arabic": "قَالَ رَسُولُ اللهِ ﷺ مَنْ أَتَتْ عَلَيْهِ سِتُّونَ سَنَةً فَقَدْ أَعْذَرَ اللهُ إِلَيْهِ فِي الْعُمُرِ",
                "chain": "وَأَخْبَرَنَا أَبُو عَبْدِ اللهِ الْحَافِظُ وَأَبُو الْحُسَيْنِ بْنُ بِشْرَانَ قَالَا أنبأ عَبْدُ اللهِ بْنُ مُحَمَّدِ بْنِ إِسْحَاقَ الْفَاكِهِيُّ بِمَكَّةَ ثنا أَبُو يَحْيَى بْنُ أَبِي مَسَرَّةَ ثنا أَبُو عَبْدِ الرَّحْمَنِ الْمُقْرِئُ ثنا سَعِيدُ بْنُ أَبِي أَيُّوبَ حَدَّثَنِي مُحَمَّدُ بْنُ عَجْلَانَ عَنْ سَعِيدِ بْنِ أَبِي سَعِيدٍ الْمَقْبُرِيِّ عَنْ أَبِي هُرَيْرَةَ قَالَ"
            }
        },
        "18": {
            "19814": {
                "arabic": "خَسَفَتِ الشَّمْسُ عَلَى عَهْدِ رَسُولِ اللهِ ﷺ الْحَدِيثَ إِلَى أَنْ قَالَتْ فَقَالَ وَاللهِ لَوْ تَعْلَمُونَ مَا أَعْلَمُ لَضَحِكْتُمْ قَلِيلًا وَلَبَكَيْتُمْ كَثِيرًا",
                "chain": "أَخْبَرَنَا أَبُو عَمْرٍو الْأَدِيبُ أنبأ أَبُو بَكْرٍ الْإِسْمَاعِيلِيُّ ثنا عِمْرَانُ بْنُ مُوسَى ثنا عُثْمَانُ بْنُ أَبِي شَيْبَةَ ثنا عَبْدَةُ بْنُ سُلَيْمَانَ عَنْ هِشَامٍ عَنْ أَبِيهِ عَنْ عَائِشَةَ ؓ قَالَتْ"
            },
            "20295": {
                "arabic": "ؓ زَوْجِ النَّبِيِّ ﷺ قَالَتْ لَمَّا اسْتُخْلِفَ عُمَرُ بْنُ الْخَطَّابِ ؓ أَكَلَ هُوَ وَأَهْلُهُ مِنَ الْمَالِ وَاحْتَرَفَ فِي مَالِ نَفْسِهِ",
                "chain": "قَالَ وَحَدَّثَنِي عُرْوَةُ بْنُ الزُّبَيْرِ عَنْ عَائِشَةَ"
            }
        },
        "19": {
            "21165": {
                "arabic": "عَنِ النَّبِيِّ ﷺ أَنَّهُ قَالَ: «أَتَدْرُونَ مَا الْعِضَةُ؟» قَالُوا: اللهُ وَرَسُولُهُ أَعْلَمُ، قَالَ: «نَقْلُ الْحَدِيثِ مِنْ بَعْضِ النَّاسِ إِلَى بَعْضٍ لِيُفْسِدَ بَيْنَهُمْ»",
                "chain": "وَأَخْبَرَنَا أَبُو الْحَسَنِ عَلِيُّ بْنُ مُحَمَّدٍ الْمُقْرِئُ أنبأ الْحَسَنُ بْنُ مُحَمَّدِ بْنِ إِسْحَاقَ ثنا يُسُفُ بْنُ يَعْقُوبَ ثنا أَحْمَدُ بْنُ عِيسَى ثنا ابْنُ وَهْبٍ أَخْبَرَنِي ابْنُ لَهِيعَةَ وَعَمْرُو بْنُ الْحَارِثِ عَنْ يَزِيدَ بْنِ أَبِي حَبِيبٍ عَنْ سِنَانٍ يَعْنِي ابْنَ سَعْدٍ عَنْ أَنَسِ بْنِ مَالِكٍ"
            },
            "21166": {
                "arabic": "كُنَّا جُلُوسًا عِنْدَ حُذَيْفَةَ ؓ فَمَرَّ رَجُلٌ فَقَالُوا هَذَا يَرْفَعُ الْحَدِيثَ إِلَى عُثْمَانَ فَقَالَ حُذَيْفَةُ ؓ سَمِعْتُ رَسُولَ اللهِ ﷺ يَقُولُ لَا يَدْخُلُ الْجَنَّةَ قَتَّاتٌ",
                "chain": "أَخْبَرَنَا أَبُو عَبْدِ اللهِ الْحَافِظُ ثنا أَبُو عَبْدِ اللهِ مُحَمَّدُ بْنُ يَعْقُوبَ الشَّيْبَانِيُّ إِمْلَاءً ثنا مُحَمَّدُ بْنُ عَبْدِ الْوَهَّابِ الْفَرَّاءُ أنبأ أَبُو نُعَيْمٍ ثنا سُفْيَانُ عَنْ مَنْصُورٍ عَنْ إِبْرَاهِيمَ عَنْ هَمَّامِ بْنِ الْحَارِثِ قَالَ"
            },
            "21167": {
                "arabic": "قَالَ رَسُولُ اللهِ ﷺ إِذَا حَدَّثَ الرَّجُلُ بِحَدِيثٍ ثُمَّ الْتَفَتَ فَهِيَ أَمَانَةٌ لَفْظَ حَدِيثِ الْقَعْنَبِيِّ",
                "chain": "أَخْبَرَنَا أَبُو بَكْرٍ مُحَمَّدُ بْنُ الْحَسَنِ بْنِ فُورَكٍ أنبأ عَبْدُ اللهِ بْنُ جَعْفَرٍ ثنا يُونُسُ بْنُ حَبِيبٍ ثنا أَبُو دَاوُدَ ثنا ابْنُ أَبِي ذِئْبٍ ح وَأَخْبَرَنَا أَبُو صَالِحِ بْنُ أَبِي طَاهِرٍ الْعَنْبَرِيُّ أنبأ جَدِّي يَحْيَى بْنُ مَنْصُورٍ الْقَاضِي ثنا مُحَمَّدُ بْنُ عَمْرٍو كَشْمَرْدُ أنبأ الْقَعْنَبِيُّ ثنا ابْنُ أَبِي ذِئْبٍ عَنْ عَبْدِ الرَّحْمَنِ بْنِ عَطَاءٍ عَنْ عَبْدِ الْمَلِكِ بْنِ جَابِرِ بْنِ عَتِيكٍ عَنْ جَابِرِ بْنِ عَبْدِ اللهِ ؓ قَالَ"
            }
        }
    },
    "musnad-ahmed": {
        "5": {
            "11852": {
                "arabic": "نَهَى رَسُولُ اللهِ ﷺ عَنِ الدُّبَّاءِوَالنَّقِيرِ واَلْمُزَفَّتِ وَقَالَ انْتَبِذْ فِي سِقَائِكَ وَأَوْكِهِ",
                "chain": "حَدَّثَنَا رَوْحٌ قَالَ حَدَّثَنَا أَشْعَثُ عَنِ الْحَسَنِ عَنْ أَبِي سَعِيدٍ الْخُدْرِيِّ قَالَ"
            }
        }
    }
}

def update_edition_row(book, section, hn, new_arabic, new_chain):
    filepath = os.path.join(EDITIONS_DIR, book, "sections", f"{section}.toon")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    header = content.split("\n")[0]
    rest = content[len(header)+1:]
    reader = csv.reader(rest.splitlines())
    rows = list(reader)
    updated = False
    new_rows = []
    for r in rows:
        if not r: continue
        if r[0] == str(hn):
            r[1] = new_arabic
            if len(r) > 5:
                r[5] = new_chain
            updated = True
        new_rows.append(r)
    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + "\n")
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(new_rows)
        print(f"Updated Arabic for {book} Hadith {hn} in section {section}.toon")

def delete_lulu_1907():
    print("Deleting stray Hadith 1907 in lulu-wal-marjan...")
    files = [
        "sections/54.toon",
        "translations/en/sections/54.toon",
        "translations/ur/sections/54.toon",
        "translations/ar/sections/54.toon"
    ]
    for rel_path in files:
        filepath = os.path.join(EDITIONS_DIR, "lulu-wal-marjan", rel_path)
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        header = content.split("\n")[0]
        rest = content[len(header)+1:]
        reader = csv.reader(rest.splitlines())
        rows = list(reader)
        new_rows = [r for r in rows if r and r[0] != "1907"]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + "\n")
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(new_rows)
        print(f"  Removed from {rel_path}")

    # Update info.toon
    info_path = os.path.join(EDITIONS_DIR, "lulu-wal-marjan", "info.toon")
    with open(info_path, "r", encoding="utf-8") as f:
        info_content = f.read()
    # Replace last hadith 1907 with 1906 for section 54
    new_info = info_content.replace('"54","Interpretation of the Quran","كِتَابُ التَّفْسِيرِ","Al-Lulu wal-Marjan","Interpretation of the Quran","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","کتاب: قرآن حکیم کی چند آیتوں کی تفسیر","1894","1907","",""',
                                    '"54","Interpretation of the Quran","كِتَابُ التَّفْسِيرِ","Al-Lulu wal-Marjan","Interpretation of the Quran","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","Al-Lulu wal-Marjan","کتاب: قرآن حکیم کی چند آیتوں کی تفسیر","1894","1906","",""')
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(new_info)
    print("  Updated lulu-wal-marjan/info.toon metadata.")

def main():
    # 1. Update the Arabic bodies and chains
    for book, sections in ARABIC_EDITS.items():
        for sec, hadiths in sections.items():
            for hn, data in hadiths.items():
                update_edition_row(book, sec, hn, data["arabic"], data["chain"])
                
    # 2. Delete lulu 1907
    delete_lulu_1907()

if __name__ == "__main__":
    main()
