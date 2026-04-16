#!/usr/bin/env python3
import subprocess
import re


def translate(text, target_lang):
    """Translate text using deep-translator CLI"""
    truncated = text[:2000]
    cmd = [
        "deep-translator",
        "-trans",
        "google",
        "-src",
        "en",
        "-tg",
        target_lang,
        "-txt",
        truncated,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"  Error translating to {target_lang}: {result.stderr}")
            return None
    except Exception as e:
        print(f"  Exception translating to {target_lang}: {e}")
        return None


def process_book(book_name, intro_text):
    """Process a single book - translate intro to es, tr, hi"""
    print(f"\nProcessing {book_name}...")

    results = {}

    print("  Translating to Spanish (es)...")
    results["es"] = translate(intro_text, "es")

    print("  Translating to Turkish (tr)...")
    results["tr"] = translate(intro_text, "tr")

    print("  Translating to Hindi (hi)...")
    results["hi"] = translate(intro_text, "hi")

    return results


# Group 4 book intros
books = {
    "mustadrak": """Al-Mustadrak 'ala al-Sahihayn (The Supplement to the Two Sahihs) is a renowned hadith collection compiled by Imam al-Hakim al-Nisapuri (rahimahullah). It contains hadiths that he considered authentic (sahih) but were not included in Sahih al-Bukhari and Sahih Muslim. This collection contains 667 hadiths covering various aspects of Islamic teachings.

Author bio:
Abu Abd Allah Muhammad ibn Ali al-Hakim al-Nisapuri (933-1014 CE / 321-405 AH), commonly known as Imam al-Hakim, was a famous hadith scholar from Nishapur. He was renowned for his extensive knowledge of hadith and his ability to distinguish between authentic and weak narrations.

His full name is Abu Abd Allah Muhammad ibn Ali ibn Muhammad al-Hakim al-Nisapuri al-Shafi'i. He studied under many prominent scholars and was known for his piety and strict adherence to hadith methodology.

This collection is important because:
1. It supplements the two most authentic hadith collections (Sahih al-Bukhari and Sahih Muslim)
2. It includes hadiths that are authenticated by Imam al-Hakim but not included in the Sahihayn
3. It provides additional evidence for Islamic jurisprudence
4. It covers a wide range of topics in Islamic law and theology
5. It helps scholars find hadiths that support various legal rulings

The Mustadrak contains hadiths that are classified as:
- Sahih (authentic) according to Imam al-Hakim's criteria
- Hasan (good) narrations
- Occasionally includes hadiths with explanations of their authenticity

This collection is particularly valuable for:
- Providing additional evidence for Islamic rulings
- Understanding the full scope of hadith literature
- Supporting legal deductions from the Sunnah
- Preserving hadiths that might otherwise be less accessible""",
    "nasai": """Sunan an-Nasā'ī is a collection of hadīth compiled by Imām Aḥmad an-Nasā'ī (rahimahullāh). His collection is unanimously considered to be one of the six canonical collections of hadith (Kutub as-Sittah) of the Sunnah of the Prophet (ﷺ). It contains roughly 5700 hadīth (with repetitions) in 52 books.

Author bio:
Aḥmad ibn Shu`ayb ibn `Alī ibn Sīnān Abū `Abd ar-Raḥmān al-Nasā'ī (214 - 303 AH/ ca. 829 - 915 AD/CE), was born in the year 214 A.H in the famous city of Nasa, situated in Western Asia known at that time as Khurasan which was a famous centre for Islamic knowledge where many Ulama were situated and studies in hadith and fiqh was at its peak. He primarily attended the gatherings and circles of knowledge in his town where he specialized in his study of hadith. When he was 20 years old, he started traveling and made his first journey to Qutaibah. He covered the Arabian Peninsula seeking knowledge from the Ulama and Muhadditheen of Iraq, Kufa, Hijaz, Syria and Egypt . Finally he decided to settle in Egypt.

Memory, Piety, and other qualities:
He was a man full of taqwa and he possessed a photographic memory too. The famous scholar and commentator of the Holy Qur'an Al-Dhahabi would say narrating from his teachers that this Great Imam was the most knowledgeable in Egypt. The Great Imam would put on good clothing according to the Sunnah of our beloved Prophet Muhammad pbuh and would eat poultry everyday with nabeedh acting on the Sunnah so that he could worship Allah with ease. In fact it is narrated that the man would fast every other day which is classified in the hadith as the fast of Dawud (as) he would worship Allah continuously throughout the nights and teach Hadith throughout the day. The Imam would also perform Hajj nearly every year and would also take part in Jihad. He was a truthful man.

Teachers and Students:
Imam an-Nasa'i studied from many teachers, the famous ones are: Ishaq ibn Rahweh, Imam Abu Dawud Al-Sijistani (author of Sunan Abu Dawud), Qutaibah ibn Sa'id, Imam Zuhri, Muhammad ibn Nasr, Imam Malik, Imam Shafi'I, and others. Many students studied under him, the famous ones are: Imam Tahawi, Imam Ahmad ibn Shu'aib an-Nasa'i (his grandson), and many others.

His Book Sunan an-Nasa'i:
Imam an-Nasa'i was particular about the authenticity of the hadiths in his collection. He would not include weak narrations and would carefully verify the chains of transmission. His collection is known for its organization and the quality of its narrations.""",
    "nawawi": """Introduction

All praise is due to Allah, Lord of all the worlds, Who sustains the heavens and the earth and manages the affairs of all creation. Who sent messengers to the obligated servants to guide them and explain the rulings of the religion through clear arguments and clear signs. I praise Him for all His blessings and ask for an increase in His grace. I testify that there is no true god but Allah, He alone, He has no partner, He is Mighty, Merciful and Ever-Forgiving. And I testify that our leader Hazrat Muhammad (peace be upon him) is His servant, His messenger, His beloved and His friend.

Forty Hadith of an-Nawawi

Imam an-Nawawi (rahimahullah) compiled this collection of 40 hadiths as a concise yet comprehensive guide to the fundamental teachings of Islam. These hadiths cover the essential aspects of Islamic faith, practice, and morality. The collection is widely studied and memorized by Muslims around the world due to its importance and accessibility.

Imam an-Nawawi (631-676 AH / 1233-1277 CE) was a renowned scholar of hadith, fiqh, and Islamic spirituality. He lived most of his life in Damascus and authored many important works including "Riyad as-Salihin" and his commentary on Sahih Muslim.

These 40 hadiths were selected by Imam an-Nawawi for their comprehensive coverage of Islamic teachings. They include the famous hadith of intention, the hadith of Jibril about the pillars of Islam, and many other fundamental narrations that form the basis of Islamic understanding.""",
    "qudsi": """Al-Ahadith Al-Qudsiyyah (Sacred Hadiths) are hadiths where the Prophet Muhammad (peace be upon him) narrates sayings directly from Allah. Unlike regular hadiths which are the Prophet's own words and actions, Qudsi hadiths are divine revelations communicated through the Prophet. The collection contains 40 hadiths.

Author: These hadiths were compiled by Imam an-Nawawi (rahimahullah) in his famous work "Al-Arba'in Hadithan" (Forty Hadiths), which includes both regular hadiths and Qudsi hadiths.

The term "Qudsi" means "sacred" or "holy," indicating that these narrations are of divine origin. The scholars differentiate between hadith qudsi and hadith nabawi (Prophetic hadith) in that the former is revealed inspiration from Allah while the latter is derived from the Prophet's own wisdom and example.

These 40 hadiths cover various aspects of Islamic belief and practice, including intention, knowledge, worship, and spiritual development. Imam an-Nawawi selected these hadiths for their importance and comprehensive coverage of Islamic teachings.""",
    "sahih-ibn-khuzaymah": """Sahih Ibn Khuzaymah (The Authenticated Collection of Ibn Khuzaymah) is a collection of hadith compiled by Imam Ibn Khuzaymah (rahimahullah). It contains 49 hadiths focusing on purification, prayer, and the fundamentals of Islamic practice. The collection is known for its strict authentication criteria and is considered one of the important hadith collections.

Author: Imam Abu Bakr Ahmad ibn Hanbal al-Marwazi, known as Ibn Khuzaymah, was a renowned hadith scholar known for his meticulous authentication of hadiths. His collection is valued for its rigor in verifying the authenticity of narrations.

This collection is important because:
1. It provides authentic hadiths on purification and prayer
2. It includes guidance on forgotten prayers and their makeup
3. It covers the excellence of proper wudu (ablution)
4. It addresses the virtue of performing prayers in congregation
5. It provides detailed information about the proper way to perform purification

Key topics covered include:
- The virtue of performing wudu properly
- The reward for those who perform prayers
- Guidance on making up missed prayers
- The excellence of attending the mosque
- The importance of prayers in congregation

This collection serves as a valuable resource for understanding the proper way to perform purification and prayer in Islam.""",
}

# Process all books
all_results = {}
for book_name, intro in books.items():
    all_results[book_name] = process_book(book_name, intro)

# Print results
print("\n" + "=" * 80)
print("TRANSLATION RESULTS")
print("=" * 80)

for book_name, translations in all_results.items():
    print(f"\n{book_name}:")
    for lang, text in translations.items():
        if text:
            escaped = (
                text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            )
            print(f'  intro_{lang}: "{escaped}"')
        else:
            print(f'  intro_{lang}: ""  # FAILED')

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
for book_name, translations in all_results.items():
    success = sum(1 for t in translations.values() if t is not None)
    print(f"{book_name}: {success}/3 translations successful")
