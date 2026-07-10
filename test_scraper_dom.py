import requests
from bs4 import BeautifulSoup
import re

url = "https://al-hadees.com/hadees/musnad-ahmed/15/0"
res = requests.get(url)
soup = BeautifulSoup(res.text, 'html.parser')

number_divs = soup.find_all('div', class_='text-gray', string=re.compile(r'Hadees Number:'))
print(f"Found {len(number_divs)} hadiths")

for num_div in number_divs:
    h_num_match = re.search(r'Hadees Number:\s*(\d+)', num_div.text)
    print("Hadees num match:", h_num_match.group(1) if h_num_match else "None")
    
    row_div = num_div.parent
    status_span = row_div.find('span', class_='badge')
    print("Status:", status_span.text.strip() if status_span else "None")
    
    # row_div's parent is the card body
    card_body = row_div.parent
    card_footer = card_body.find_next_sibling('div', class_=re.compile(r'card-footer'))
    
    if card_footer:
        ar_ta = card_footer.find('textarea', id=re.compile(r'content-arb-'))
        print("Arabic Textarea found:", ar_ta is not None)
        ur_ta = card_footer.find('textarea', id=re.compile(r'content-urd-'))
        print("Urdu Textarea found:", ur_ta is not None)
    else:
        print("No card-footer found")
