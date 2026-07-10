import requests
from bs4 import BeautifulSoup

res = requests.get('https://al-hadees.com/hadees/musnad-ahmed/26/1')
print("Status code for /26/1:", res.status_code)
soup = BeautifulSoup(res.text, 'html.parser')
number_divs = soup.find_all('div', class_='text-gray')
for n in number_divs[:2]:
    print(n.text.strip())

res = requests.get('https://al-hadees.com/hadees/musnad-ahmed/26/0')
print("Status code for /26/0:", res.status_code)
soup = BeautifulSoup(res.text, 'html.parser')
number_divs = soup.find_all('div', class_='text-gray')
for n in number_divs[:2]:
    print(n.text.strip())
