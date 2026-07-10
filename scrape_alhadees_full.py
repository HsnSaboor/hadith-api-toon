import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
import sys

BASE_URL = "https://al-hadees.com"

def get_soup(url, retries=5):
    for i in range(retries):
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                return BeautifulSoup(res.text, 'html.parser')
        except Exception:
            time.sleep(2)
    return None

def clean_text(text):
    lines = text.split('\n')
    cleaned_lines = []
    for l in lines:
        if not l.strip():
            continue
        if re.search(r'(مسند|سنن|صحیح|جامع|حدیث).*?:', l):
            if len(l) < 150:
                continue
        cleaned_lines.append(l.strip())
    return '\n'.join(cleaned_lines).strip()

def scrape_book(book_id, display_name):
    print(f"Starting {display_name} Scraper...")
    OUTPUT_DIR = f"/home/saboor/code/hadith-api-toon/sunnah.com-download/{book_id.replace('musnad-ahmed', 'ahmad')}"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    parts_links = []
    page = 0
    while True:
        soup = get_soup(f"{BASE_URL}/hadees-name/{book_id}/{page}")
        if not soup: break
        links = [a['href'] for a in soup.find_all('a', href=True) if f'/hadees-subjects/{book_id}/' in a['href']]
        if not links: break
        new_links = [l for l in links if l not in parts_links]
        if not new_links: break
        parts_links.extend(new_links)
        page += 1
        
    parts_links = list(dict.fromkeys(parts_links))
    print(f"Found {len(parts_links)} total parts.")
    
    ar_data = []
    ur_data = []
    sections = []
    bab_counter = 1
    
    for part_url in parts_links:
        print(f"Fetching part: {part_url}")
        
        subject_links = []
        p_page = 0
        while True:
            paginated_part = re.sub(r'/\d+$', f'/{p_page}', part_url)
            part_soup = get_soup(paginated_part)
            if not part_soup: break
            links_found = []
            for a in part_soup.find_all('a', class_='btn-scale', href=True):
                if f'/hadees/{book_id}/' in a['href']:
                    name_div = a.find('div', class_='font-arabic2')
                    subj_name = name_div.text.strip() if name_div else f"Subject {bab_counter + len(subject_links)}"
                    links_found.append((a['href'], subj_name))
            
            new_links = [l for l in links_found if l not in subject_links]
            if not new_links: break
            subject_links.extend(new_links)
            p_page += 1
            
        print(f"  Found {len(subject_links)} subjects in this part.")
        
        for subj_url, subj_name in subject_links:
            first_hadith = None
            last_hadith = None
            h_page = 0
            
            while True:
                paginated_subj = re.sub(r'/\d+$', f'/{h_page}', subj_url)
                subj_soup = get_soup(paginated_subj)
                if not subj_soup: break
                    
                number_divs = subj_soup.find_all('div', class_='text-gray', string=re.compile(r'Hadees Number:'))
                if not number_divs: break
                    
                for num_div in number_divs:
                    text_match = re.search(r'Hadees Number:\s*(\d+)', num_div.text)
                    if not text_match: continue
                    h_num = text_match.group(1)
                    
                    if first_hadith is None: first_hadith = h_num
                    last_hadith = h_num
                    
                    row_div = num_div.parent
                    status = ""
                    status_span = row_div.find('span', class_='badge')
                    if status_span: status = status_span.text.strip()
                        
                    card_body = row_div.parent
                    card_footer = card_body.find_next_sibling('div', class_=re.compile(r'card-footer'))
                    
                    ar_text = ""
                    ur_text = ""
                    
                    if card_footer:
                        ar_ta = card_footer.find('textarea', id=re.compile(r'content-arb-'))
                        if ar_ta: ar_text = clean_text(ar_ta.text)
                            
                        ur_ta = card_footer.find('textarea', id=re.compile(r'content-urd-'))
                        if ur_ta: ur_text = clean_text(ur_ta.text)
                            
                    ref_name = display_name
                    if display_name == "Musnad Ahmad": ref_name = "Musnad Ahmad"
                    
                    ar_data.append({
                        "hadithnumber": h_num,
                        "narrator": "",
                        "status": status,
                        "reference": f"{ref_name} {h_num}",
                        "in_book_reference": "",
                        "bab_number": str(bab_counter),
                        "book_name": subj_name,
                        "text": ar_text
                    })
                    ur_data.append({
                        "hadithnumber": h_num,
                        "narrator": "",
                        "status": status,
                        "reference": f"{ref_name} {h_num}",
                        "in_book_reference": "",
                        "bab_number": str(bab_counter),
                        "book_name": subj_name,
                        "text": ur_text
                    })
                h_page += 1
                
            if first_hadith and last_hadith:
                sections.append({
                    "id": str(bab_counter),
                    "name_ur": subj_name,
                    "name_ar": subj_name,
                    "first": first_hadith,
                    "last": last_hadith
                })
                bab_counter += 1
                
            if bab_counter % 50 == 0:
                with open(f"{OUTPUT_DIR}/ar.json", "w", encoding="utf-8") as f:
                    json.dump(ar_data, f, ensure_ascii=False, indent=2)
                with open(f"{OUTPUT_DIR}/ur.json", "w", encoding="utf-8") as f:
                    json.dump(ur_data, f, ensure_ascii=False, indent=2)
                with open(f"{OUTPUT_DIR}/sections_temp.json", "w", encoding="utf-8") as f:
                    json.dump(sections, f, ensure_ascii=False, indent=2)

    with open(f"{OUTPUT_DIR}/ar.json", "w", encoding="utf-8") as f:
        json.dump(ar_data, f, ensure_ascii=False, indent=2)
    with open(f"{OUTPUT_DIR}/ur.json", "w", encoding="utf-8") as f:
        json.dump(ur_data, f, ensure_ascii=False, indent=2)
    with open(f"{OUTPUT_DIR}/sections_temp.json", "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
        
    print(f"Scraped {len(ar_data)} hadiths successfully for {display_name}.")

if __name__ == "__main__":
    book = sys.argv[1] if len(sys.argv) > 1 else "musnad-ahmed"
    display = "Musnad Ahmad" if book == "musnad-ahmed" else "Sunan Al Kubra Bayhaqi"
    scrape_book(book, display)
