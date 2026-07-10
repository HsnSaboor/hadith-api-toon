import requests
url = "https://sunnah.com/bukhari/1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}
try:
    res = requests.get(url, headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Content length: {len(res.text)}")
except Exception as e:
    print(e)
