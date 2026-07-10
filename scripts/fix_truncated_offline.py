#!/usr/bin/env python3
import os
import re
import csv
import json
from pathlib import Path
from datasets import load_dataset

BASE_DIR = Path("/home/saboor/code/hadith-api-toon")
EDITIONS_DIR = BASE_DIR / "editions"
TASKS_PATH = BASE_DIR / "backfill_tasks" / "truncated_tasks.json"

NEW_DB_DIR = Path("/home/saboor/code/hadith-api-toon-new/production_build")
ORIG_DB_DIR = Path("/home/saboor/code/hadith-api-1/database/originals")
I360_DIR = Path("/home/saboor/islam360_downloads/hadith")

UR_TO_ROMAN_MAP = {
    'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ٹ': 't', 'ث': 's', 'ج': 'j', 'چ': 'ch',
    'ح': 'h', 'خ': 'kh', 'د': 'd', 'ڈ': 'd', 'ذ': 'z', 'ر': 'r', 'ڑ': 'r', 'ز': 'z',
    'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a',
    'غ': 'gh', 'f': 'f', 'ق': 'q', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'و': 'w', 'ہ': 'h', 'ھ': 'h', 'ء': 'a', 'ی': 'y', 'ے': 'ay', 'ں': 'n', 'ؤ': 'o',
    'آ': 'aa', 'ة': 't'
}

def transliterate_urdu_to_roman(text):
    res = []
    for c in text:
        res.append(UR_TO_ROMAN_MAP.get(c, c))
    cleaned = "".join(res)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

I360_URDU_MAP = {
    'أ': ' ', 'إ': 'آ', 'ځ': 'پ', '﷽': 'ﷺ', 'ل': 'ف', 'ش': 'ر', 'و': 'م', 'ت': 'ا',
    'ۄ': 'ہ', 'ە': 'ے', 'ح': 'ت', 'ہ': 'ھ', 'ڬ': 'ک', 'ۏ': 'ی', 'ؼ': 'ع', 'ه': 'l',
    'ز': 'د', 'ً': 'و', 'ى': 'ن', 'د': 'ج', 'ض': 'س', 'غ': 'ط', 'ث': 'b', 'م': 'q',
    'ڲ': 'گ', 'ۗ': '۔', 'ذ': 'ح', 'ظ': 'ص', 'ط': 'ش', 'ؽ': 'غ', 'ع': 'ض', 'ډ': 'چ',
    'ص': 'ز', 'ڽ': 'ں', '+': '(', ',': ')', '“': '"', '”': '"', '‛': '"', '$': '!',
    '=': ':', 'ة': 'ئ', 'ؖ': 'رضی اللہ عنہ', 'ر': 'خ', '؏': '،', 'س': 'ذ', 'ػ': 'ظ',
    'ڔ': 'ڑ', 'ڋ': 'ڈ', 'ټ': 'ٹ', 'خ': 'ث', 'ٔ': 'ّ', 'ٳ': 'ٰ', 'آ': 'ء', 'ۆ': 'ؤ',
    '٪': '٪', 'ي': 'ی'
}

def decode_i360(text):
    if not text or not isinstance(text, str): return ""
    match = re.search(r"['\"]text['\"]\s*:\s*(['\"])(.*?)\1", text, re.S)
    if match:
        text = match.group(2)
    text = re.sub(r"^unistr\(\s*['\"]+", "", text)
    text = re.sub(r"['\"]+\s*\)\s*$", "", text)
    text = text.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
    decoded = "".join([I360_URDU_MAP.get(c, c) for c in text])
    return " ".join(decoded.split())

PLACEHOLDER = re.compile(
    r'^(same as|similar to|as above|see (the )?hadith|narration about|'
    r'wrong same as|\.\.\.\s*$|\(as hadith|refer to hadith|same\b|see above|'
    r'mentioned above|same hadith)', re.I)

MARKDOWN_PLACEHOLDERS = ["### अनुवाद", "হাদিস নং", "অনুবাদ", "হাদীস নম্বর"]

def is_truncated(arabic, text):
    if not arabic.strip() or not text.strip():
        return False
    if len(arabic) > 200 and len(text) < 80 and len(text) < 0.1 * len(arabic):
        return True
    return False

def is_placeholder(text):
    text_stripped = text.strip()
    if PLACEHOLDER.match(text_stripped):
        return True
    for mp in MARKDOWN_PLACEHOLDERS:
        if mp in text_stripped:
            return True
    return False

def normalize_arabic(text):
    if not text:
        return ""
    text = re.sub(r'[\u064B-\u065F\u0670\u0671\u0640]', '', text)
    text = re.sub(r'[^\u0621-\u064A\s]', '', text)
    text = re.sub(r'\s+', '', text)
    return text

BOOK_FINAL_MAP = {
    "abudawud": "abudawud_final.json",
    "ahmad": "ahmad_final.json",
    "musnad-ahmed": "ahmad_final.json",
    "aladab-almufrad": "aladab_almufrad_final.json",
    "bayhaqi": "bayhaqi_final.json",
    "bukhari": "bukhari_final.json",
    "bulugh-al-maram": "bulugh_almaram_final.json",
    "sunan-darmi": "darimi_final.json",
    "dehlawi": "dehlawi_final.json",
    "fatah-alrabani": "fatah_alrabani_final.json",
    "ibnmajah": "ibnmajah_final.json",
    "lulu-wal-marjan": "lulu_wal_marjan_final.json",
    "majma-al-zawaid": "majma_al_zawaid_final.json",
    "malik": "malik_final.json",
    "mishkat": "mishkat_almasabih_final.json",
    "muajam-tabarani-saghir": "muajam_tabarani_saghir_final.json",
    "musannaf-ibn-abi-shaybah": "musannaf_ibn_abi_shaybah_final.json",
    "muslim": "muslim_final.json",
    "mustadrak": "mustadrak_final.json",
    "nasai": "nasai_final.json",
    "nawawi40": "nawawi40_final.json",
    "qudsi40": "qudsi40_final.json",
    "riyadussalihin": "riyad_assalihin_final.json",
    "sahih-ibn-khuzaymah": "sahih_ibn_khuzaymah_final.json",
    "shahwaliullah40": "shahwaliullah40_final.json",
    "shamail-tirmazi": "shamail_muhammadiyah_final.json",
    "silsila-sahih": "silsila_sahih_final.json",
    "sunan-al-daraqutni": "sunan_al_daraqutni_final.json",
    "tirmidhi": "tirmidhi_final.json"
}

db_cache = {}
db_by_ar_cache = {}

def get_db(book):
    fn = BOOK_FINAL_MAP.get(book)
    if not fn:
        return None, None
    if fn not in db_cache:
        path = NEW_DB_DIR / fn
        if path.exists():
            print(f"  Loading final database {fn}...")
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f)
                db_cache[fn] = db
                by_ar = {}
                for entry in db.values():
                    norm_ar = normalize_arabic(entry.get("arabic", ""))
                    if norm_ar:
                        by_ar[norm_ar] = entry
                db_by_ar_cache[fn] = by_ar
        else:
            db_cache[fn] = None
            db_by_ar_cache[fn] = None
    return db_cache[fn], db_by_ar_cache[fn]

txt_cache = {}
def get_txt_translations(book, lang):
    key = (book, lang)
    if key not in txt_cache:
        lang_prefixes = {
            "en": ["eng-", "english"],
            "ur": ["urd-", "urdu"],
            "bn": ["ben-", "bengali"],
            "tr": ["tur-", "turkish"],
            "fr": ["fra-", "french"],
            "id": ["ind-", "indonesian"],
            "ru": ["rus-", "ru-"],
            "hi": ["hin-", "hindi"],
            "roman-ur": ["roman"]
        }.get(lang, [])
        
        book_slug = book.replace("-", "")
        if book == "ibnmajah": book_slug = "ibnmajah"
        elif book == "nawawi40": book_slug = "nawawi"
        elif book == "qudsi40": book_slug = "qudsi"
        
        matched_file = None
        if ORIG_DB_DIR.exists():
            for fn in os.listdir(ORIG_DB_DIR):
                fn_lower = fn.lower()
                if book_slug in fn_lower:
                    for lp in lang_prefixes:
                        if lp in fn_lower:
                            matched_file = ORIG_DB_DIR / fn
                            break
                if matched_file:
                    break
                
        if matched_file:
            print(f"  Loading original text file {matched_file.name} for {book}/{lang}...")
            trans_map = {}
            with open(matched_file, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" in line:
                        parts = line.split("|", 1)
                        hnum = parts[0].strip()
                        text = parts[1].strip()
                        trans_map[hnum] = text
            txt_cache[key] = trans_map
        else:
            txt_cache[key] = None
    return txt_cache[key]

jsonl_cache = {}
def get_jsonl_translations(book, lang):
    key = (book, lang)
    if key not in jsonl_cache:
        fn = {
            "abudawud": "abu_dawood.jsonl",
            "bukhari": "bukhari.jsonl",
            "ibnmajah": "maja.jsonl",
            "mishkat": "mishkat.jsonl",
            "muslim": "muslim.jsonl",
            "musnad-ahmed": "musnad.jsonl",
            "mustadrak": "mustadrak.jsonl",
            "nasai": "nasai.jsonl",
            "silsila-sahih": "silsila.jsonl",
            "tirmidhi": "tirmazi.jsonl",
            "muajam-tabarani-saghir": "alzawaid.jsonl",
            "bayhaqi": "beyhaqi.jsonl",
            "sunan-darmi": "darmi.jsonl",
            "sahih-ibn-khuzaymah": "khuzaymah.jsonl",
            "malik": "muwatta.jsonl",
            "musannaf-ibn-abi-shaybah": "shaybah.jsonl"
        }.get(book)
        
        if fn and I360_DIR.exists():
            path = I360_DIR / fn
            if path.exists():
                print(f"  Loading Islam360 JSONL {fn} for {book}/{lang}...")
                trans_map = {}
                trans_by_ar = {}
                lang_ids = {
                    "en": [2],
                    "hi": [3],
                    "roman-ur": [4, 1],
                    "ur": [1]
                }.get(lang, [])
                
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                            hnum = str(rec["hadees_number"])
                            arabic = rec.get("arabic", "")
                            
                            for trans in rec.get("translations", []):
                                if trans.get("language_id") in lang_ids:
                                    text = (trans.get("hadees") or "").strip()
                                    if text:
                                        if trans.get("language_id") == 1:
                                            text = decode_i360(text)
                                            if lang == "roman-ur":
                                                text = transliterate_urdu_to_roman(text)
                                        if text:
                                            trans_map[hnum] = text
                                            norm_ar = normalize_arabic(arabic)
                                            if norm_ar:
                                                trans_by_ar[norm_ar] = text
                        except Exception:
                            continue
                jsonl_cache[key] = (trans_map, trans_by_ar)
            else:
                jsonl_cache[key] = None
        else:
            jsonl_cache[key] = None
            
    return jsonl_cache[key]

cache_json_data = {}
def get_local_cache_translations(book, lang):
    key = (book, lang)
    if key not in cache_json_data:
        fn = {
            "bayhaqi": "bayhaqi.json",
            "mustadrak": "hakim.json"
        }.get(book)
        
        if fn:
            path = Path("/home/saboor/code/hadith-api-toon/scripts/cache") / fn
            if path.exists():
                print(f"  Loading local cache JSON {fn} for {book}/{lang}...")
                trans_map = {}
                trans_by_ar = {}
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    for chap in d.get("chapters", []):
                        items = chap.get("items") or []
                        if not items:
                            for sec in chap.get("sections", []):
                                items.extend(sec.get("items") or [])
                                
                        for item in items:
                            hnum = str(item.get("number", ""))
                            text_dict = item.get("text", {})
                            text = text_dict.get(lang)
                            arabic = text_dict.get("ar", "")
                            
                            if text and text.strip():
                                trans_map[hnum] = text
                                norm_ar = normalize_arabic(arabic)
                                if norm_ar:
                                    trans_by_ar[norm_ar] = text
                cache_json_data[key] = (trans_map, trans_by_ar)
            else:
                cache_json_data[key] = None
        else:
            cache_json_data[key] = None
    return cache_json_data[key]

fawaz_cache = {}
def get_fawaz_cache():
    if not fawaz_cache:
        print("  Loading fawazahmed0/hadith-data dataset...")
        try:
            dataset = load_dataset('fawazahmed0/hadith-data', split='train')
            for r in dataset:
                name = r.get("name", "")
                if "-" in name:
                    lang_prefix, book_suffix = name.split("-", 1)
                else:
                    continue
                    
                lang = {
                    "eng": "en", "urd": "ur", "ben": "bn", "tur": "tr", 
                    "fra": "fr", "ind": "id", "rus": "ru", "tam": "ta"
                }.get(lang_prefix)
                
                if not lang:
                    continue
                    
                book = {
                    "abudawud": "abudawud", "bukhari": "bukhari", "ibnmajah": "ibnmajah",
                    "malik": "malik", "muslim": "muslim", "nasai": "nasai",
                    "tirmidhi": "tirmidhi", "dehlawi": "dehlawi", "nawawi": "nawawi40",
                    "qudsi": "qudsi40"
                }.get(book_suffix)
                
                if not book:
                    continue
                    
                hnum = str(r.get("hadith", ""))
                text = (r.get("text") or "").strip()
                if text:
                    fawaz_cache.setdefault(book, {}).setdefault(lang, {})[hnum] = text
            print("  Fawaz dataset loaded successfully!")
        except Exception as e:
            print(f"  Failed to load Fawaz dataset: {e}")
    return fawaz_cache

def find_translation(task):
    book = task["book"]
    lang = task["lang"]
    hnum = task["hadithnumber"]
    arabic = task["arabic"]
    norm_arabic = normalize_arabic(arabic)
    
    hnum_clean = str(hnum).strip()
    hnum_base = hnum_clean.split(".")[0]
    
    # 1. New DB Lookup
    db, db_by_ar = get_db(book)
    if db:
        entry = db.get(hnum_clean) or db.get(hnum_base)
        if entry:
            trans_dict = entry.get("translations", {})
            text = trans_dict.get(lang)
            if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
                return text
                
        if db_by_ar and norm_arabic in db_by_ar:
            entry = db_by_ar[norm_arabic]
            text = entry.get("translations", {}).get(lang)
            if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
                return text
                
        if db_by_ar:
            for ar_key, entry in db_by_ar.items():
                if len(norm_arabic) > 10 and (norm_arabic in ar_key or ar_key in norm_arabic):
                    text = entry.get("translations", {}).get(lang)
                    if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
                        return text

    # 2. Original text lookup
    txt_trans = get_txt_translations(book, lang)
    if txt_trans:
        text = txt_trans.get(hnum_clean) or txt_trans.get(hnum_base)
        if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
            return text
            
    # 3. Local cached JSON lookup (Bayhaqi/Mustadrak)
    cache_res = get_local_cache_translations(book, lang)
    if cache_res:
        trans_map, trans_by_ar = cache_res
        text = trans_map.get(hnum_clean) or trans_map.get(hnum_base)
        if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
            return text
        if norm_arabic in trans_by_ar:
            return trans_by_ar[norm_arabic]
        for ar, text in trans_by_ar.items():
            if len(norm_arabic) > 10 and (norm_arabic in ar or ar in norm_arabic):
                if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
                    return text

    # 4. Fawaz dataset lookup
    f_cache = get_fawaz_cache()
    f_book = f_cache.get(book, {})
    f_lang = f_book.get(lang, {})
    if f_lang:
        text = f_lang.get(hnum_clean) or f_lang.get(hnum_base)
        if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
            return text

    # 5. Islam360 JSONL lookup
    jsonl_res = get_jsonl_translations(book, lang)
    if jsonl_res:
        trans_map, trans_by_ar = jsonl_res
        text = trans_map.get(hnum_clean) or trans_map.get(hnum_base)
        if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
            return text
        if norm_arabic in trans_by_ar:
            return trans_by_ar[norm_arabic]
        for ar, text in trans_by_ar.items():
            if len(norm_arabic) > 10 and (norm_arabic in ar or ar in norm_arabic):
                if text and text.strip() and not is_truncated(arabic, text) and not is_placeholder(text):
                    return text

    return None

def find_translation_with_roman(task):
    book = task["book"]
    lang = task["lang"]
    
    if lang == "roman-ur":
        text = find_translation(task)
        if text:
            return text
        task_ur = task.copy()
        task_ur["lang"] = "ur"
        ur_text = find_translation(task_ur)
        if ur_text:
            return transliterate_urdu_to_roman(ur_text)
            
    return find_translation(task)

def update_hadith_file(filepath, hadithnumber, new_text):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    header = content.split("\n")[0]
    rest = content[len(header)+1:]
    reader = csv.reader(rest.splitlines())
    rows = list(reader)
    
    updated = False
    for r in rows:
        if r and r[0] == hadithnumber:
            r[1] = new_text
            updated = True
            break
            
    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + "\n")
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(rows)
        return True
    return False

def main():
    if not TASKS_PATH.exists():
        print("No truncated_tasks.json found.")
        return
        
    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        tasks = json.load(f)
        
    print(f"Loaded {len(tasks)} truncated tasks to resolve offline...")
    
    matched = 0
    remaining_tasks = []
    
    for i, t in enumerate(tasks):
        filepath = BASE_DIR / t["filepath"]
        new_text = find_translation_with_roman(t)
        if new_text and new_text.strip():
            if update_hadith_file(filepath, t["hadithnumber"], new_text):
                matched += 1
                # print(f"  [FIXED] {t['book']}/{t['lang']} hadith {t['hadithnumber']}")
        else:
            remaining_tasks.append(t)
            
    print(f"\nOffline Repair Completed!")
    print(f"Fixed truncated hadiths: {matched}/{len(tasks)} ({matched/len(tasks)*100:.2f}%)")
    print(f"Remaining unmatched: {len(remaining_tasks)}")
    
    # Save the remaining tasks back to truncated_tasks.json
    with open(TASKS_PATH, "w", encoding="utf-8") as f:
        json.dump(remaining_tasks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
