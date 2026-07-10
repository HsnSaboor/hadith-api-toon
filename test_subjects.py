import requests
from bs4 import BeautifulSoup
import re

res = requests.get('https://al-hadees.com/hadees-subjects/musnad-ahmed/5/0')
soup = BeautifulSoup(res.text, 'html.parser')
links = soup.find_all('a', class_='btn-scale')
for link in links:
    subj_name = link.find('div', class_='font-arabic2').text.strip()
    texts = link.find_all('div', style='width:70px;')
    h_count = [t.text for t in texts if 'Hadees' in t.text]
    print(f"Subject: {subj_name}, Link: {link['href']}, Count: {h_count}")
