import json
import re

info_path = "/home/saboor/code/hadith-api-toon/editions/abudawud/info.toon"
out_path = "/home/saboor/code/hadith-api-toon/sunnah.com-download/abudawud/info.json"

data = {
    "metadata": {},
    "translations": [],
    "sections": []
}

with open(info_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")

current_block = None
translation_keys = []
section_keys = []

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    if line.startswith("metadata:"):
        current_block = "metadata"
        continue
    
    trans_match = re.match(r'^translations\[\d+\]\{(.*?)\}:', line)
    if trans_match:
        current_block = "translations"
        translation_keys = trans_match.group(1).split(",")
        continue
        
    sec_match = re.match(r'^sections\[\d+\]\{(.*?)\}:', line)
    if sec_match:
        current_block = "sections"
        section_keys = sec_match.group(1).split(",")
        continue

    if current_block == "metadata":
        # Handle key: "value" or key: value
        if ":" in line:
            parts = line.split(":", 1)
            k = parts[0].strip()
            v = parts[1].strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
                # Unescape \n and \"
                v = v.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            else:
                try:
                    v = int(v)
                except:
                    pass
            data["metadata"][k] = v

    elif current_block == "translations":
        if line.startswith('"'):
            # Parse CSV-like string
            import csv
            from io import StringIO
            reader = csv.reader(StringIO(line))
            row = next(reader)
            obj = {k: v for k, v in zip(translation_keys, row)}
            data["translations"].append(obj)

    elif current_block == "sections":
        if line.startswith('"'):
            import csv
            from io import StringIO
            reader = csv.reader(StringIO(line))
            row = next(reader)
            obj = {k: v.strip() for k, v in zip(section_keys, row)}
            data["sections"].append(obj)

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Successfully converted info.toon to {out_path}")
