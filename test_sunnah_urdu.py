import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
}
res = requests.get('https://sunnah.com/bukhari/1?lang=urdu', headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')
containers = soup.find_all('div', class_='actualHadithContainer')

print(f"Found {len(containers)} hadiths")
if containers:
    c = containers[0]
    urdu_div = c.find('div', class_='urdu_hadith_full')
    print("Urdu div found?", urdu_div is not None)
    if urdu_div:
        print(urdu_div.text[:100])
