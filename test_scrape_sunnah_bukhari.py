import requests
from bs4 import BeautifulSoup
import json
import re

headers = {"User-Agent": "Mozilla/5.0"}
book_id = 1

# Fetch HTML
res = requests.get(f'https://sunnah.com/bukhari/{book_id}', headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')

# Fetch AJAX
en_res = requests.get(f'https://sunnah.com/ajax/english/bukhari/{book_id}', headers=headers).json()
ur_res = requests.get(f'https://sunnah.com/ajax/urdu/bukhari/{book_id}', headers=headers).json()
bn_res = requests.get(f'https://sunnah.com/ajax/bangla/bukhari/{book_id}', headers=headers).json()

def make_dict(ajax_res):
    d = {}
    for item in ajax_res:
        urn = item.get('matchingArabicURN')
        d[urn] = item
    return d

en_dict = make_dict(en_res)
ur_dict = make_dict(ur_res)
bn_dict = make_dict(bn_res)

containers = soup.find_all('div', class_='actualHadithContainer')
print(f"Found {len(containers)} containers")

for c in containers[:1]:
    cid = c.get('id') # e.g. h100010
    urn = int(cid.replace('h', ''))
    
    # Extract references
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
                val = re.sub(r'^:\s*', '', val).strip() # Remove leading colon
                if 'reference' in key and 'in-book' not in key and 'usc' not in key:
                    ref = val
                elif 'in-book' in key:
                    in_book = val
                elif 'usc' in key:
                    usc = val
            if 'deprecated' in row.text.lower():
                deprecated = True
                
    # Extract hadith number from reference
    h_num = ref.replace('Sahih al-Bukhari', '').strip()
    
    # Extract Arabic
    ar_div = c.find('div', class_='arabic_hadith_full')
    ar_text = ar_div.text.strip() if ar_div else ""
    
    print("URN:", urn)
    print("Hadith Number:", h_num)
    print("Reference:", ref)
    print("In-book:", in_book)
    print("USC:", usc)
    print("Deprecated:", deprecated)
    print("Arabic length:", len(ar_text))
    print("Has EN:", urn in en_dict)
    print("Has UR:", urn in ur_dict)
    print("Has BN:", urn in bn_dict)
    
    if urn in en_dict:
        print("EN Text snippet:", (en_dict[urn].get('hadithSanad', '') + " " + en_dict[urn].get('hadithText', ''))[:100])
