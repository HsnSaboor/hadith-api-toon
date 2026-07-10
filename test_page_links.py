import requests
from bs4 import BeautifulSoup

url = 'https://al-hadees.com/hadees/musnad-ahmed/26/0'
res = requests.get(url)
soup = BeautifulSoup(res.text, 'html.parser')

pages = soup.find_all('a', class_='page-link')
for page in pages:
    print(page.get('href'))
