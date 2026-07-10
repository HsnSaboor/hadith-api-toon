#!/usr/bin/env python3
import csv
import json
import os
import re
import urllib.request

BASE_DIR = "/home/saboor/code/hadith-api-toon"
EDITIONS_DIR = os.path.join(BASE_DIR, "editions")
REMAINS_JSON = os.path.join(BASE_DIR, "scripts/cache/fetched_remains.json")

# 22 Mishkat hadiths with Arabic Mojibake
MISHKAT_NUMS = [
    1572, 4952, 2667, 3970, 4685, 1912, 4716, 1218, 1414, 3131, 5347,
    1344, 1021, 4356, 1036, 4991, 5171, 2452, 2312, 1485, 3045, 5773
]

MISHKAT_SECTIONS = {
    1572: "5", 4952: "25", 2667: "11", 3970: "0", 4685: "25", 1912: "7",
    4716: "25", 1218: "4", 1414: "4", 3131: "13", 5347: "26", 1344: "4",
    1021: "4", 4356: "23", 1036: "4", 4991: "25", 5171: "26", 2452: "10",
    2312: "9", 1485: "5", 3045: "13", 5773: "29"
}

def clean_arabic_for_mishkat(text):
    # Remove HTML entities like &#13;
    text = text.replace("&#13;", "").replace("&#10;", "\n")
    for e in [("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'"),("&apos;","'")]:
        text = text.replace(*e)
    return text.strip()

def fetch_mishkat_arabic(num):
    url = f"https://quranohadith.com/mishkat/{num}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8')
        # Find textarea content-arb-num
        match = re.search(rf'<textarea[^>]*ID="content-arb-{num}"[^>]*>(.*?)</textarea>', html, re.DOTALL | re.IGNORECASE)
        if match:
            return clean_arabic_for_mishkat(match.group(1))
        # Fallback to content-all-num
        match_all = re.search(rf'<textarea[^>]*ID="content-all-{num}"[^>]*>(.*?)</textarea>', html, re.DOTALL | re.IGNORECASE)
        if match_all:
            cleaned = clean_arabic_for_mishkat(match_all.group(1))
            # Remove title prefix if present
            cleaned = re.sub(r'^مشکوۃالمصابیح حدیث: \d+ عربی حدیث: \d+\s*', '', cleaned)
            return cleaned
    except Exception as e:
        print(f"Error fetching Mishkat {num}: {e}")
    return None

def update_edition_row(book, section, hn, new_arabic, new_chain=None):
    filepath = os.path.join(EDITIONS_DIR, book, "sections", f"{section}.toon")
    if not os.path.exists(filepath):
        print(f"Section file not found: {filepath}")
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    header = content.split("\n")[0]
    rest = content[len(header)+1:]
    
    reader = csv.reader(rest.splitlines())
    rows = list(reader)
    
    updated = False
    new_rows = []
    for r in rows:
        if not r:
            continue
        if r[0] == str(hn):
            r[1] = new_arabic
            if new_chain is not None:
                # Column 5 is narrator_chain
                if len(r) > 5:
                    r[5] = new_chain
            updated = True
        new_rows.append(r)
        
    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + "\n")
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(new_rows)
        print(f"Updated {book} Hadith {hn} in section {section}.toon")
        return True
    return False

def update_translation_row(book, lang, section, hn, new_text):
    filepath = os.path.join(EDITIONS_DIR, book, "translations", lang, "sections", f"{section}.toon")
    if not os.path.exists(filepath):
        print(f"Translation file not found: {filepath}")
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    header = content.split("\n")[0]
    rest = content[len(header)+1:]
    
    reader = csv.reader(rest.splitlines())
    rows = list(reader)
    
    updated = False
    new_rows = []
    for r in rows:
        if not r:
            continue
        if r[0] == str(hn):
            r[1] = new_text
            updated = True
        new_rows.append(r)
        
    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + "\n")
            writer = csv.writer(f, lineterminator="\n")
            writer.writerows(new_rows)
        print(f"Updated {book} translation ({lang}) Hadith {hn} in section {section}.toon")
        return True
    return False

def main():
    # 1. Update Mishkat Hadiths
    print("=== Processing Mishkat Arabic Gaps ===")
    for num in MISHKAT_NUMS:
        sec = MISHKAT_SECTIONS[num]
        print(f"Fetching Mishkat Hadith {num}...")
        arabic = fetch_mishkat_arabic(num)
        if arabic:
            update_edition_row("mishkat", sec, num, arabic)
        else:
            print(f"Failed to retrieve clean Arabic for Mishkat Hadith {num}")
            
    # 2. Update remains from Hadith Unlocked JSON
    print("\n=== Processing remains from Hadith Unlocked ===")
    if not os.path.exists(REMAINS_JSON):
        print(f"Fetched remains JSON not found: {REMAINS_JSON}")
        return
        
    with open(REMAINS_JSON, "r", encoding="utf-8") as f:
        remains = json.load(f)
        
    # We also need to map the keys to their correct local section
    # Let's inspect the target keys and their sections
    with open(os.path.join(BASE_DIR, "scripts/cache/to_fetch.json"), "r") as f:
        to_fetch = json.load(f)
        
    key_to_meta = {f"{item['book']}:{item['hadithnumber']}": item for item in to_fetch}
    
    # Map Hadith Unlocked key names back to our book names
    unlocked_to_our = {
        "adab": "aladab-almufrad",
        "lulu-marjan": "lulu-wal-marjan"
    }
    
    for key, data in remains.items():
        parts = key.split(":", 1)
        alias, hn = parts[0], parts[1]
        our_book = unlocked_to_our.get(alias, alias)
        lookup_key = f"{our_book}:{hn}"
        
        meta = key_to_meta.get(lookup_key)
        if not meta:
            continue
            
        book = meta["book"]
        hn = meta["hadithnumber"]
        sec = meta["section"]
        
        print(f"Applying updates for {lookup_key}...")
        # Check if we should update Arabic or English
        for issue in meta["issues"]:
            if issue["lang"] == "ar":
                # Update Arabic body and chain
                update_edition_row(book, sec, hn, data["arabic_body"], data["arabic_chain"])
            elif issue["lang"] == "en":
                # Update English translation
                update_translation_row(book, "en", sec, hn, data["english_body"])

if __name__ == "__main__":
    main()
