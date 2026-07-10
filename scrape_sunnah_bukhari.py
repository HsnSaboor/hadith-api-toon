import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os

OUTPUT_DIR = "/home/saboor/code/hadith-api-toon/sunnah.com-download/bukhari"
os.makedirs(OUTPUT_DIR, exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_json(url, retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception:
            time.sleep(2)
    return []

def get_html(url, retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.text
        except Exception:
            time.sleep(2)
    return ""

def clean_html(raw_html):
    if not raw_html:
        return ""
    # Strip basic HTML tags
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', str(raw_html))
    return cleantext.strip()

ar_data = []
en_data = []
ur_data = []
bn_data = []
sections = []

def make_dict(ajax_res):
    d = {}
    for item in ajax_res:
        urn = item.get('matchingArabicURN')
        d[urn] = item
    return d

for book_id in range(1, 98):
    print(f"Fetching Book {book_id}/97...")
    html = get_html(f"https://sunnah.com/bukhari/{book_id}")
    if not html:
        print(f"Failed to fetch book {book_id}")
        continue
        
    soup = BeautifulSoup(html, 'html.parser')
    containers = soup.find_all('div', class_='actualHadithContainer')
    
    en_res = get_json(f"https://sunnah.com/ajax/english/bukhari/{book_id}")
    ur_res = get_json(f"https://sunnah.com/ajax/urdu/bukhari/{book_id}")
    bn_res = get_json(f"https://sunnah.com/ajax/bangla/bukhari/{book_id}")
    
    en_dict = make_dict(en_res)
    ur_dict = make_dict(ur_res)
    bn_dict = make_dict(bn_res)
    
    print(f"  Found {len(containers)} hadiths in Book {book_id}")
    
    for c in containers:
        cid = c.get('id')
        if not cid or not cid.startswith('h'):
            continue
        urn = int(cid.replace('h', ''))
        
        # References
        ref_table = c.find('table', class_='hadith_reference')
        ref = ""
        in_book = ""
        usc = ""
        deprecated = False
        if ref_table:
            rows = ref_table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 2:
                    key = tds[0].text.strip().lower()
                    val = tds[1].text.strip()
                    val = re.sub(r'^:\s*', '', val).strip()
                    if 'reference' in key and 'in-book' not in key and 'usc' not in key:
                        ref = val
                    elif 'in-book' in key:
                        in_book = val
                    elif 'usc' in key:
                        usc = val
                if 'deprecated' in row.text.lower():
                    deprecated = True
                    
        h_num = ref.replace('Sahih al-Bukhari', '').strip()
        
        ar_div = c.find('div', class_='arabic_hadith_full')
        ar_text_raw = ar_div.text.strip() if ar_div else ""
        
        # We need chapter info. We will try to pull from EN dict, then UR dict, then BN dict
        bab_num = ""
        book_name = ""
        if urn in en_dict:
            bab_num = str(en_dict[urn].get('babNumber', ''))
            book_name = str(en_dict[urn].get('bookName', ''))
        elif urn in ur_dict:
            bab_num = str(ur_dict[urn].get('babNumber', ''))
            book_name = str(ur_dict[urn].get('bookName', ''))
        
        # Helper to create item
        def create_item(lang_dict):
            text = ""
            narrator = ""
            if urn in lang_dict:
                obj = lang_dict[urn]
                text = clean_html(obj.get('hadithText', ''))
                narrator = clean_html(obj.get('hadithSanad', ''))
            return {
                "hadithnumber": h_num,
                "narrator": narrator,
                "status": "Sahih",
                "reference": ref,
                "in_book_reference": in_book,
                "usc_msa_reference": usc,
                "usc_msa_reference_deprecated": deprecated,
                "bab_number": bab_num,
                "book_name": book_name,
                "text": text
            }
            
        ar_data.append({
            "hadithnumber": h_num,
            "narrator": "",
            "status": "Sahih",
            "reference": ref,
            "in_book_reference": in_book,
            "usc_msa_reference": usc,
            "usc_msa_reference_deprecated": deprecated,
            "bab_number": bab_num,
            "book_name": book_name,
            "text": ar_text_raw
        })
        
        en_data.append(create_item(en_dict))
        ur_data.append(create_item(ur_dict))
        bn_data.append(create_item(bn_dict))

with open(f"{OUTPUT_DIR}/ar.json", "w", encoding="utf-8") as f:
    json.dump(ar_data, f, ensure_ascii=False, indent=2)
with open(f"{OUTPUT_DIR}/en.json", "w", encoding="utf-8") as f:
    json.dump(en_data, f, ensure_ascii=False, indent=2)
with open(f"{OUTPUT_DIR}/ur.json", "w", encoding="utf-8") as f:
    json.dump(ur_data, f, ensure_ascii=False, indent=2)
with open(f"{OUTPUT_DIR}/bn.json", "w", encoding="utf-8") as f:
    json.dump(bn_data, f, ensure_ascii=False, indent=2)

print("Saved all Bukhari data successfully.")
print(f"Total Hadiths extracted: {len(ar_data)}")
