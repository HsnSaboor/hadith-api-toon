import json

info_path = "/home/saboor/code/hadith-api-toon/editions/aladab-almufrad/info.toon"

# parse info.toon to get section boundaries and names
sections = []
with open(info_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith('"'):
            import csv
            from io import StringIO
            reader = csv.reader(StringIO(line))
            row = list(next(reader))
            # columns: id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last
            if len(row) >= 12:
                sec = {
                    "id": row[0].strip(),
                    "name_en": row[4],
                    "name_ar": row[2],
                    "name_ur": row[9],
                    "first": int(row[10]),
                    "last": int(row[11])
                }
                sections.append(sec)

def process_file(lang, name_key):
    file_path = f"/home/saboor/code/hadith-api-toon/sunnah.com-download/adab/{lang}.json"
    print(f"Processing {lang}.json...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for item in data:
        # Extract numerical part of hadithnumber
        h_str = str(item.get("hadithnumber", ""))
        import re
        match = re.search(r'\d+', h_str)
        if match:
            h_num = int(match.group())
            # Find section
            found_sec = None
            for sec in sections:
                if sec["first"] <= h_num <= sec["last"]:
                    found_sec = sec
                    break
            
            if found_sec:
                item["bab_number"] = found_sec["id"]
                item["book_name"] = found_sec[name_key]
                
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

process_file("en", "name_en")
process_file("ar", "name_ar")
process_file("ur", "name_ur")

print("Done injecting topics.")
