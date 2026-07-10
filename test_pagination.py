import requests
from bs4 import BeautifulSoup
import sys

# Get part 3 subjects
res = requests.get('https://al-hadees.com/hadees-subjects/musnad-ahmed/3/0')
soup = BeautifulSoup(res.text, 'html.parser')
links = soup.find_all('a', class_='btn-scale')
for link in links:
    href = link.get('href', '')
    if 'hadees/' in href:
        res2 = requests.get(href)
        if 'page-item' in res2.text or 'pagination' in res2.text or '?page=' in res2.text:
            print("Found pagination on", href)
            sys.exit(0)
print("No pagination found.")
