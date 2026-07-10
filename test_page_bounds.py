import requests
from bs4 import BeautifulSoup
import re

res = requests.get('https://al-hadees.com/hadees/musnad-ahmed/26/1000')
soup = BeautifulSoup(res.text, 'html.parser')
number_divs = soup.find_all('div', class_='text-gray', string=re.compile(r'Hadees Number:'))
print(f"Hadiths on page 1000: {len(number_divs)}")
