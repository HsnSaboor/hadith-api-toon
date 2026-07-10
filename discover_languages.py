import requests
import re

BOOKS = [
    "bukhari", "muslim", "nasai", "abudawud", "tirmidhi", "ibnmajah",
    "malik", "ahmad", "darimi", "ibnkhuzayma", "ibnhibban", "hakim",
    "abdurrazzaq", "ibnabishayba", "daraqutni", "bayhaqi", "nasaikubra",
    "adab", "shamail", "nawawi40", "riyadussalihin", "mishkat",
    "bulugh", "forty", "hisn", "virtues"
]

LANG_NAMES = {
    "english": "English", "urdu": "Urdu", "bangla": "Bangla", "hindi": "Hindi",
    "russian": "Russian", "turkish": "Turkish", "german": "German",
    "french": "French", "chinese": "Chinese", "portuguese": "Portuguese",
    "indonesian": "Indonesian", "tamil": "Tamil", "spanish": "Spanish",
    "japanese": "Japanese", "bosnian": "Bosnian", "uyghur": "Uyghur",
    "albanian": "Albanian", "amharic": "Amharic", "hausa": "Hausa",
    "swahili": "Swahili", "kurdish": "Kurdish", "persian": "Persian",
    "pashto": "Pashto", "sindhi": "Sindhi", "korean": "Korean",
    "malayalam": "Malayalam", "thai": "Thai", "vietnamese": "Vietnamese",
    "dutch": "Dutch", "italian": "Italian", "azerbaijani": "Azerbaijani",
    "somali": "Somali", "tajik": "Tajik", "marathi": "Marathi",
    "nepali": "Nepali", "swedish": "Swedish",
}

AVBL_RE = re.compile(r'avbl_languages\s*=\s*\[([^\]]+)\]')
LANG_RE = re.compile(r'id="ch_([a-z]+)"')

def get_languages(book):
    for url in [f"https://sunnah.com/{book}/1", f"https://sunnah.com/{book}:1"]:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                continue
            m = AVBL_RE.search(resp.text)
            if m:
                raw = m.group(1)
                codes = re.findall(r'"([a-z]+)"', raw)
                if codes:
                    return [LANG_NAMES.get(c, c) for c in codes], resp.status_code, url
            radios = LANG_RE.findall(resp.text)
            if radios:
                return [LANG_NAMES.get(r, r) for r in radios], resp.status_code, url
            return [], resp.status_code, url
        except Exception as e:
            continue
    return None, None, None

for book in BOOKS:
    langs, status, url = get_languages(book)
    if langs is None:
        print(f"{book:20s} ERROR (status={status})")
    elif langs:
        print(f"{book:20s} {', '.join(langs)}")
    else:
        print(f"{book:20s} English only")
