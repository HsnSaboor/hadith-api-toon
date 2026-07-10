import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os

BASE_URL = "https://al-hadees.com"
AHMAD_INDEX = f"{BASE_URL}/hadees-name/musnad-ahmed/0"

def get_soup(url, retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                return BeautifulSoup(res.text, 'html.parser')
        except Exception as e:
            time.sleep(2)
    return None

def main():
    print("Starting Musnad Ahmad Scraper from al-hadees.com...")
    
    # 1. Get Parts
    soup = get_soup(AHMAD_INDEX)
    if not soup:
        print("Failed to fetch index.")
        return
        
    parts_links = []
    for a in soup.find_all('a', href=True):
        if '/hadees-subjects/musnad-ahmed/' in a['href']:
            parts_links.append(a['href'])
            
    parts_links = list(dict.fromkeys(parts_links))
    print(f"Found {len(parts_links)} parts.")
    
    ar_data = []
    ur_data = []
    sections = []
    
    bab_counter = 1
    
    for part_url in parts_links:
        print(f"Fetching part: {part_url}")
        part_soup = get_soup(part_url)
        if not part_soup:
            continue
            
        subject_links = []
        for a in part_soup.find_all('a', class_='btn-scale', href=True):
            if '/hadees/musnad-ahmed/' in a['href']:
                name_div = a.find('div', class_='font-arabic2')
                subj_name = name_div.text.strip() if name_div else f"Subject {bab_counter}"
                subject_links.append((a['href'], subj_name))
                
        print(f"  Found {len(subject_links)} subjects in this part.")
        
        for subj_url, subj_name in subject_links:
            print(f"    Fetching subject: {subj_url} - {subj_name}")
            
            first_hadith = None
            last_hadith = None
            page = 1
            
            while True:
                # The subj_url ends in /0. Replace it with /page
                paginated_url = re.sub(r'/\d+$', f'/{page}', subj_url)
                subj_soup = get_soup(paginated_url)
                if not subj_soup:
                    break
                    
                number_divs = subj_soup.find_all('div', class_='text-gray', string=re.compile(r'Hadees Number:'))
                if not number_divs:
                    break # No more hadiths on this page
                    
                print(f"      Page {page}: found {len(number_divs)} hadiths")
                
                for num_div in number_divs:
                    text_match = re.search(r'Hadees Number:\s*(\d+)', num_div.text)
                    if not text_match:
                        continue
                    h_num = text_match.group(1)
                    
                    if first_hadith is None:
                        first_hadith = h_num
                    last_hadith = h_num
                    
                    row_div = num_div.parent
                    status = ""
                    status_span = row_div.find('span', class_='badge')
                    if status_span:
                        status = status_span.text.strip()
                        
                    card_body = row_div.parent
                    card_footer = card_body.find_next_sibling('div', class_=re.compile(r'card-footer'))
                    
                    ar_text = ""
                    ur_text = ""
                    
                    if card_footer:
                        ar_ta = card_footer.find('textarea', id=re.compile(r'content-arb-'))
                        if ar_ta:
                            lines = ar_ta.text.split('\n')
                            ar_lines = [l for l in lines if 'مسند احمد حدیث' not in l and l.strip()]
                            ar_text = '\n'.join(ar_lines).strip()
                            
                        ur_ta = card_footer.find('textarea', id=re.compile(r'content-urd-'))
                        if ur_ta:
                            lines = ur_ta.text.split('\n')
                            ur_lines = [l for l in lines if 'مسند احمد حدیث' not in l and l.strip()]
                            ur_text = '\n'.join(ur_lines).strip()
                            
                    ar_item = {
                        "hadithnumber": h_num,
                        "narrator": "",
                        "status": status,
                        "reference": f"Musnad Ahmad {h_num}",
                        "in_book_reference": "",
                        "bab_number": str(bab_counter),
                        "book_name": subj_name,
                        "text": ar_text
                    }
                    ur_item = {
                        "hadithnumber": h_num,
                        "narrator": "",
                        "status": status,
                        "reference": f"Musnad Ahmad {h_num}",
                        "in_book_reference": "",
                        "bab_number": str(bab_counter),
                        "book_name": subj_name,
                        "text": ur_text
                    }
                    ar_data.append(ar_item)
                    ur_data.append(ur_item)
                    
                page += 1 # proceed to next page
                
            sections.append({
                "id": str(bab_counter),
                "name_ur": subj_name,
                "name_ar": subj_name,
                "first": first_hadith,
                "last": last_hadith
            })
            bab_counter += 1
            
            if bab_counter % 5 == 0:
                with open("/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/ar.json", "w", encoding="utf-8") as f:
                    json.dump(ar_data, f, ensure_ascii=False, indent=2)
                with open("/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/ur.json", "w", encoding="utf-8") as f:
                    json.dump(ur_data, f, ensure_ascii=False, indent=2)
                with open("/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/sections_temp.json", "w", encoding="utf-8") as f:
                    json.dump(sections, f, ensure_ascii=False, indent=2)

    with open("/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/ar.json", "w", encoding="utf-8") as f:
        json.dump(ar_data, f, ensure_ascii=False, indent=2)
    with open("/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/ur.json", "w", encoding="utf-8") as f:
        json.dump(ur_data, f, ensure_ascii=False, indent=2)
    with open("/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/sections_temp.json", "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
        
    print(f"Scraped {len(ar_data)} hadiths successfully.")

if __name__ == "__main__":
    main()
