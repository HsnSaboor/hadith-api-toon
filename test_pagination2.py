import requests
from bs4 import BeautifulSoup

# Part 5 has 1795 hadiths in 5 subjects. This is a lot.
res = requests.get('https://al-hadees.com/hadees-subjects/musnad-ahmed/5/0')
soup = BeautifulSoup(res.text, 'html.parser')
links = soup.find_all('a', class_='btn-scale')
for link in links:
    href = link.get('href', '')
    if 'hadees/' in href:
        print("Checking subject:", href)
        res2 = requests.get(href)
        soup2 = BeautifulSoup(res2.text, 'html.parser')
        pages = soup2.find_all('a', class_='page-link')
        print(f"Pagination links found: {len(pages)}")
        break
