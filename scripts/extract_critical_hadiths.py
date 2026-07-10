#!/usr/bin/env python3
import csv
import json
import os

AUDIT_FILE = "/home/saboor/code/hadith-api-toon/audit_1000_deep.toon"
OUTPUT_FILE = "/home/saboor/code/hadith-api-toon/scripts/cache/to_fetch.json"

# Map our book keys to Hadith Unlocked aliases
BOOK_ALIAS_MAP = {
    "abudawud": "abudawud",
    "aladab-almufrad": "adab",
    "lulu-wal-marjan": "lulu-marjan",
    "mishkat": "mishkat",
    "muslim": "muslim",
    "tirmidhi": "tirmidhi",
}

def main():
    if not os.path.exists(AUDIT_FILE):
        print(f"Audit file not found: {AUDIT_FILE}")
        return

    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = 'issue_details{book,section,hadithnumber,language,issue_type,description}'
    end_marker = 'end_issue_details'
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)

    if start_idx == -1 or end_idx == -1:
        print("Issue details block not found in audit file")
        return

    body = content[start_idx + len(start_marker) + 2 : end_idx].strip()
    reader = csv.reader(body.split('\n'))
    
    unique_hadiths = {}
    for r in reader:
        if not r:
            continue
        book, section, hn, lang, issue_type, desc = r
        if issue_type in ['PLACEHOLDER', 'MOJIBAKE', 'REPLACEMENT_CHAR']:
            if book in BOOK_ALIAS_MAP:
                alias = BOOK_ALIAS_MAP[book]
                key = f"{book}:{hn}"
                if key not in unique_hadiths:
                    unique_hadiths[key] = {
                        "book": book,
                        "alias": alias,
                        "hadithnumber": hn,
                        "section": section,
                        "issues": []
                    }
                unique_hadiths[key]["issues"].append({
                    "lang": lang,
                    "type": issue_type,
                    "desc": desc
                })

    print(f"Found {len(unique_hadiths)} unique hadiths with critical issues.")
    
    # Save list to file
    out_list = list(unique_hadiths.values())
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_list, f, indent=2, ensure_ascii=False)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
