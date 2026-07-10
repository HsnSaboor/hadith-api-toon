import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}
res = requests.get('https://sunnah.com/ajax/english/bukhari/1', headers=headers)
print("English Status:", res.status_code)
if res.status_code == 200:
    print("Content length:", len(res.text))

res = requests.get('https://sunnah.com/ajax/bangla/bukhari/1', headers=headers)
print("Bangla Status:", res.status_code)
if res.status_code == 200:
    print("Content length:", len(res.text))
