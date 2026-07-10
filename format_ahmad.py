import json
import csv
import io
import re

info_path = "/home/saboor/code/hadith-api-toon/editions/musnad-ahmed/info.toon"

sections = []
in_sections = False
with open(info_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("sections["):
            in_sections = True
            continue
            
        if in_sections and line.startswith('"'):
            reader = csv.reader(io.StringIO(line.strip()))
            row = list(next(reader))
            if len(row) >= 12:
                try:
                    first = int(row[10])
                    last = int(row[11])
                except ValueError:
                    first = -1
                    last = -1
                    
                sec = {
                    "id": row[0].strip(),
                    "en": row[1],
                    "ar": row[2],
                    "ur": row[9],
                    "first": first,
                    "last": last
                }
                sections.append(sec)

langs = {"en": "en", "ar": "ar", "ur": "ur"}

for lang, name_key in langs.items():
    file_path = f"/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/{lang}.json"
    print(f"Processing {lang}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"{lang}.json not found, skipping.")
        continue
        
    new_data = []
    for item in data:
        h_str = str(item.get("hadithnumber", ""))
        match = re.search(r'\d+', h_str)
        h_num = int(match.group()) if match else -1
        
        found_sec = None
        for sec in sections:
            if sec["first"] <= h_num <= sec["last"]:
                found_sec = sec
                break
                
        bab_number = found_sec["id"] if found_sec else ""
        book_name = found_sec[name_key] if found_sec else ""
        
        new_item = {
            "hadithnumber": str(item.get("hadithnumber", "")),
            "narrator": item.get("narrator", ""),
            "status": item.get("status", ""),
            "reference": item.get("reference", f"Musnad Ahmad {h_str}"),
            "in_book_reference": item.get("in_book_reference", ""),
            "bab_number": bab_number,
            "book_name": book_name,
            "text": item.get("text", "")
        }
        new_data.append(new_item)
        
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

print("Formatted successfully.")
