#!/usr/bin/env python3
import subprocess
import re


def translate(text, target_lang):
    """Translate text using deep-translator CLI"""
    # Limit text to 2000 chars to avoid CLI issues
    text_chunk = text[:2000]
    cmd = [
        "deep-translator",
        "-trans",
        "google",
        "-src",
        "en",
        "-tg",
        target_lang,
        "-txt",
        text_chunk,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.stdout.strip() if result.returncode == 0 else None


# Book intros to translate
books = {
    "dehlawi": """Al-Hikmat al-Mulahazat (Wisdom with Considerations) is a collection of profound sayings and maxims compiled by Imam Ibn al-Mubarak (rahimahullah) and other scholars. It contains 40 wisdom statements that provide guidance on various aspects of life, behavior, and spirituality in Islam.

Author: The collection contains sayings attributed to various sources including the Prophet Muhammad (ﷺ), his Companions, and early scholars. The compilation focuses on wisdom, spiritual insight, and practical guidance for Muslims.

This collection is important because:
1. It provides concise yet profound wisdom for daily life
2. It covers topics like war, trust, charity, and personal conduct
3. It emphasizes the importance of discreet action and wise counsel
4. It reflects the moral and spiritual values of early Muslim scholars

The sayings in this collection address:
- The difference between hearing reports and witnessing events
- The nature of warfare and strategy
- The mutual reflection and support among Muslims
- The responsibility of those giving advice
- The virtue of guiding others to good deeds
- The wisdom of maintaining secrecy in matters of need

These maxims serve as practical guidance for Muslims seeking to live according to Islamic principles and develop moral character.""",
    "fatah-alrabani": """Fatah al-Rabbani (The Granting of Divine Mercy) is a comprehensive collection of hadith compiled by Imam al-Suyuti (rahimahullah). It contains 192 hadiths covering various aspects of Islamic teachings, including Aqeedah (theology), Fiqh (jurisprudence), and spiritual development. The collection is organized into multiple books covering different topics of Islamic law and belief.

Author bio:
Imam Jalal al-Din Abd al-Rahman al-Suyuti (1441-1505 CE / 849-911 AH), also known as al-Suyuti, was one of the most prolific Islamic scholars of the medieval period. He was born in Cairo and became a renowned scholar in hadith, fiqh, linguistics, history, and many other Islamic sciences. He wrote over 500 books on various subjects.

Al-Suyuti was a renowned muhaddith (hadith scholar) and is considered one of the most influential scholars in Islamic history. His works cover virtually every branch of Islamic knowledge.

Fatah al-Rabbani is important because:
1. It compiles hadiths from various sources including Musnad Ahmad and other collections
2. It covers comprehensive topics of Islamic theology and law
3. It provides detailed explanations of hadiths with their chains
4. It serves as an important reference for both scholars and students

The collection is organized into sections including:
- Tawhid (Oneness of God) and fundamental principles of religion
- Various aspects of Islamic law and practice
- Stories of the Prophets and companions
- Spiritual and moral guidance

This collection is particularly valued for its educational value in teaching Islamic principles and for its comprehensive coverage of various topics important to Muslims.""",
    "ibnmajah": """Sunan Ibn Mājah is a collection of hadīth compiled by Imām Muḥammad bin Yazīd Ibn Mājah al-Qazvīnī (raḥimahullāh). It is widely considered to be the sixth of the six canonical collection of Ḥadīth (Kutub as-Sittah) of the Sunnah of the Prophet (saws). It consists of 4341 aḥādīth in 37 books.

Author bio:
Abū `Abdullāh Muḥammad bin Yazīd bin `Abdullāh ar-Rab`ī al- Qazvīnī, famously known as Ibn Mājah, was born in 209 AH to a non-Arab tribe by the name of Rab`i in Qazvin (Iran). Various explanations have been given for his nickname, Ibn Mājah, the more prominent being that Mājah was his mother. Some scholars believe that Mājah was the nickname of his father.

Travels to learn Hadith:
Ibn Mājah spent his early years studying Ḥadīth in his hometown of Qazvin, which had by then become a major center of hadith sciences. In 230 AH, at the age of 21 or 22, he travelled to various countries to seek more knowledge. He travelled to Khurasan, Iraq, Hijaz, Egypt and Sham to attend the gatherings of hadīth scholars. He also studied under scholars in Makkah and Madinah, and later travelled to Baghdad, which, according to Imām adh-Dhahabī was the home of chains of narration and memorization the (Dār al isnād al `āli wal ḥifẓ), the seat of the caliphate and knowledge. He never gave up on his quest for knowledge and continued his travels to Damascus, Homs, Egypt, Isfahan, Ashkelon, and Nishapur and became a pupil of the major scholars of ḥadīth of those times.""",
    "lulu-wal-marjan": """Lulu al-Marjan (Pearls and Coral) is a comprehensive collection of hadith compiled by Imam al-Munawi (rahimahullah). It contains 47 hadiths covering various important topics in Islamic teachings, including the virtues of the companions, warning against lying on the Prophet, and fundamental teachings of Islam.

Author: Imam Abdul-Rahman ibn Yusuf al-Munawi (ramadh) was a renowned hadith scholar. The collection is designed to provide important guidance on Islamic belief and practice through carefully selected hadiths.

This collection is important because:
1. It includes warnings against fabricating hadiths
2. It covers the basic pillars of Islam (Iman, Islam, Ihsan)
3. It discusses the virtues and merits of the companions
4. It provides guidance on proper Islamic conduct

Key topics covered include:
- The importance of truthfulness and warning against lying about the Prophet
- The meaning of Iman (faith), Islam (submission), and Ihsan (excellence)
- The signs of the Hour (Day of Judgment)
- The virtues of the Ansar (helpers of the Prophet)
- Various aspects of Islamic worship and conduct

This collection serves as a valuable resource for Muslims seeking to understand the fundamental teachings of Islam and the importance of following authentic hadith.""",
    "malik": """Muwatta Malik is a collection of hadīth compiled by Imām Malik ibn Anas (rahimahullāh). It is one of the oldest and most revered Sunni hadith collections and one of the earliest surviving compendiums of Islamic law. It consists of approximately 2000 hadith in 61 books.

Author bio:
Mālik ibn Anas (c. 711–795), also known as Imam Malik, was a Muslim scholar, jurist, muhaddith and Imam. He was born in Medina, Hejaz (present-day Saudi Arabia). He is known as the founder of the Mālikī school of law (madhhab), one of the four major Sunni schools of jurisprudence.

His full name is Abu ʿAbd Allāh Mālik ibn Anas ibn Mālik ibn Abī ʿĀmir ibn ʿAmr ibn Al-Ḥārith ibn Ghaymān ibn Khuthayn ibn ʿAmr al-Aṣbaḥī. His father Anas ibn Malik is not to be confused with the famous Sahabi (Companion) Anas ibn Malik.

Malik was born in Medina and spent most of his life there. He became learned in Islamic law and attracted a considerable number of students, his followers coming to be known as the Mālikī school of law (madhhab). His prestige involved him in politics, and he was rash enough to declare during a rebellion that loyalty to the caliph was not a religious necessity, since homage to him had been given under compulsion. The caliph, however, was victorious, and Mālik received a flogging for his complicity. This only increased his prestige, and during later years he regained favour with the central government.

His famous work, al-Muwatta' ("The Approved"), was formed of the sound narrations from the Prophet together with the sayings of his companions, their followers, and those after them. Malik said, "I showed my book to seventy scholars of Madinah, and every single one of them approved it for me (kulluhum wata-ani alayh), so I named it 'The Approved.'" Imam Bukhari said that the soundest of all chains of transmission was "Malik, from Nafi, from Ibn Umar." The scholars of hadeeth call it the Golden Chain, and there are eighty narrations with this chain in the Muwatta.""",
}

# Translate for each book
results = {}
for book_name, intro_text in books.items():
    print(f"\n=== Translating {book_name} ===")
    results[book_name] = {}

    for lang_code in ["es", "tr", "hi"]:
        print(f"  Translating to {lang_code}...")
        translation = translate(intro_text, lang_code)
        if translation:
            results[book_name][lang_code] = translation
            print(f"  ✓ {lang_code}: {translation[:100]}...")
        else:
            print(f"  ✗ {lang_code}: FAILED")
            results[book_name][lang_code] = None

# Save results to file for processing
import json

with open("/tmp/translations_group2.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n\n=== Translation Summary ===")
for book_name, translations in results.items():
    print(f"\n{book_name}:")
    for lang, text in translations.items():
        status = "✓" if text else "✗"
        print(f"  {status} {lang}")
