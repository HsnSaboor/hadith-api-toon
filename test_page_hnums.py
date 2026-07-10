import requests
from bs4 import BeautifulSoup
import re

def print_first_hadith(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    number_divs = soup.find_all('div', class_='text-gray', string=re.compile(r'Hadees Number:'))
    if number_divs:
        h_num_match = re.search(r'Hadees Number:\s*(\d+)', number_divs[0].text)
        print(f"First hadith on {url}:", h_num_match.group(1) if h_num_match else "None")
    else:
        print(f"No hadiths on {url}")

print_first_hadith('https://al-hadees.com/hadees/musnad-ahmed/26/0')
print_first_hadith('https://al-hadees.com/hadees/musnad-ahmed/26/1')
print_first_hadith('https://al-hadees.com/hadees/musnad-ahmed/26/2')
