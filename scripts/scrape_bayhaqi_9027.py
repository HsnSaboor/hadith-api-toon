#!/usr/bin/env python3
"""Programmatic check of bayhaqi 9027 across all sources."""

import requests
import re
import json

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def check_fawazahmed0():
    print("=== Checking fawazahmed0 Hadith API ===")
    try:
        r = requests.get("https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/info.json", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Check if bayhaqi is in any of the editions or books
            keys = list(data.keys())
            bayhaqi_keys = [k for k in keys if "bayhaqi" in k.lower()]
            print("  Bayhaqi related keys in API info:", bayhaqi_keys)
            
            # Check for a potential URL for bayhaqi
            if bayhaqi_keys:
                print("  Bayhaqi exists in info.json!")
            else:
                print("  Bayhaqi is NOT hosted on fawazahmed0 Hadith API.")
        else:
            print(f"  Failed to fetch info.json, status: {r.status_code}")
    except Exception as e:
        print("  Error:", e)

def check_sunnah_com():
    print("=== Checking sunnah.com ===")
    # Try multiple URLs for bayhaqi on sunnah.com
    urls = [
        "https://sunnah.com/bayhaqi",
        "https://sunnah.com/bayhaqi/9027",
        "https://sunnah.com/nasai/9027",  # Al-Sunan al-Kubra of Nasa'i is sometimes mapped
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            print(f"  URL: {url} -> Status: {r.status_code}")
            if r.status_code == 200:
                if "Page not found" in r.text or "404" in r.text:
                    print("    (Returned 200 but content indicates 404/Not Found)")
        except Exception as e:
            print(f"  Error on {url}:", e)

def check_quranohadith_com():
    print("=== Checking quranohadith.com (Al-Hadees) ===")
    url = "https://quranohadith.com/bayhaqi/9027"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  URL: {url} -> Status: {r.status_code}")
        if r.status_code == 200:
            textareas = re.findall(r'<textarea[^>]*>(.*?)</textarea>', r.text, re.DOTALL)
            print(f"  Found {len(textareas)} textareas:")
            for i, ta in enumerate(textareas):
                val = ta.strip()
                # Print first line of each textarea
                first_line = val.split('\n')[0].strip() if val else "(empty)"
                print(f"    Textarea {i}: {first_line[:120]}...")
    except Exception as e:
        print("  Error:", e)

def main():
    check_fawazahmed0()
    check_sunnah_com()
    check_quranohadith_com()

if __name__ == "__main__":
    main()
