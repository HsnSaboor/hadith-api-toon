import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

# Let's try some common endpoints
urls = [
    "https://sunnah.com/ajax/bukhari/1/urdu",
    "https://sunnah.com/ajax/bukhari/1/translations/urdu",
    "https://sunnah.com/bukhari/1?lang=urdu"
]

for url in urls:
    res = requests.get(url, headers=headers)
    print(f"{url} -> Status: {res.status_code}, Length: {len(res.text)}")
    if res.status_code == 200 and 'اردو' in res.text or 'urdu' in res.text.lower():
        print("Found Urdu!")
        break
