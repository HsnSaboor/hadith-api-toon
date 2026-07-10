import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}
res = requests.get('https://sunnah.com/ajax/urdu/bukhari/1', headers=headers)
print("Status:", res.status_code)
print("Content length:", len(res.text))
if res.status_code == 200:
    print("Content sample:", res.text[:200])
