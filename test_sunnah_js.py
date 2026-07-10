import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
}
res = requests.get('https://sunnah.com/js/sunnah.js', headers=headers)
with open("sunnah.js", "w") as f:
    f.write(res.text)
