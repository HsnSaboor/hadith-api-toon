import json
import re
import csv
from io import StringIO
import io

info_path = "/home/saboor/code/hadith-api-toon/editions/aladab-almufrad/info.toon"

sections = []
new_info_lines = []
in_sections = False

with open(info_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("sections["):
            in_sections = True
            new_info_lines.append(line)
            continue
            
        if in_sections and line.startswith('"'):
            reader = csv.reader(StringIO(line.strip()))
            row = list(next(reader))
            sec_id = int(row[0].strip())
            
            # Recalculate true first and last
            file_path = f"/home/saboor/code/hadith-api-toon/editions/aladab-almufrad/sections/{sec_id}.toon"
            first = None
            last = None
            with open(file_path, "r", encoding="utf-8") as sec_f:
                for sline in sec_f:
                    if sline.startswith('"'):
                        parts = sline.split('","')
                        hnum = parts[0].strip('"')
                        if hnum.isdigit():
                            if not first:
                                first = hnum
                            last = hnum
            
            row[10] = first
            row[11] = last
            row[12] = first
            row[13] = last
            
            sec = {
                "id": str(sec_id),
                "name_en": row[4],
                "name_ar": row[2],
                "name_ur": row[9],
                "first": int(first),
                "last": int(last)
            }
            sections.append(sec)
            
            # Form exactly as original toon
            r_str = ",".join(f'"{str(c)}"' for c in row)
            new_info_lines.append(r_str + "\n")
        else:
            new_info_lines.append(line)

with open(info_path, "w", encoding="utf-8") as f:
    f.writelines(new_info_lines)

# Now inject into json
def process_file(lang, name_key):
    file_path = f"/home/saboor/code/hadith-api-toon/sunnah.com-download/adab/{lang}.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for item in data:
        h_str = str(item.get("hadithnumber", ""))
        match = re.search(r'\d+', h_str)
        if match:
            h_num = int(match.group())
            found_sec = None
            for sec in sections:
                if sec["first"] <= h_num <= sec["last"]:
                    found_sec = sec
                    break
            
            if found_sec:
                item["bab_number"] = found_sec["id"].strip()
                item["book_name"] = found_sec[name_key]
                
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

process_file("en", "name_en")
process_file("ar", "name_ar")
process_file("ur", "name_ur")

print("Done")
