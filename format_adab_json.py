import json

def load_json(lang):
    with open(f"/home/saboor/code/hadith-api-toon/sunnah.com-download/adab/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

en_data = load_json("en")
ar_data = load_json("ar")
ur_data = load_json("ur")

en_meta = {}
for item in en_data:
    hnum = item.get("hadithnumber")
    en_meta[hnum] = {
        "narrator": item.get("narrator", ""),
        "status": item.get("status", ""),
        "reference": item.get("reference", ""),
        "in_book_reference": item.get("in_book_reference", "")
    }

def format_file(data, lang):
    new_data = []
    for item in data:
        hnum = item.get("hadithnumber")
        meta = en_meta.get(hnum, {
            "narrator": "",
            "status": "",
            "reference": f"Al-Adab Al-Mufrad {hnum}",
            "in_book_reference": ""
        })
        
        new_item = {
            "hadithnumber": hnum,
            "narrator": meta["narrator"],
            "status": meta["status"],
            "reference": meta["reference"],
            "in_book_reference": meta["in_book_reference"],
            "bab_number": item.get("bab_number", ""),
            "book_name": item.get("book_name", ""),
            "text": item.get("text", "")
        }
        new_data.append(new_item)
    
    out_path = f"/home/saboor/code/hadith-api-toon/sunnah.com-download/adab/{lang}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

format_file(en_data, "en")
format_file(ar_data, "ar")
format_file(ur_data, "ur")

print("Formatted successfully.")
