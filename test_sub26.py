import requests
from bs4 import BeautifulSoup
import re

url = 'https://al-hadees.com/hadees/musnad-ahmed/26/0'
res = requests.get(url)
soup = BeautifulSoup(res.text, 'html.parser')
number_divs = soup.find_all('div', class_='text-gray', string=re.compile(r'Hadees Number:'))
print(f"Found {len(number_divs)} hadiths on the page.")

pages = soup.find_all('a', class_='page-link')
print(f"Pagination links found: {len(pages)}")
