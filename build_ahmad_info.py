import json

temp_file = "/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/sections_temp.json"
out_file = "/home/saboor/code/hadith-api-toon/sunnah.com-download/ahmad/info.json"

with open(temp_file, "r", encoding="utf-8") as f:
    temp_sections = json.load(f)

# Build info structure
info = {
    "metadata": {
        "book_id": "ahmad",
        "book_name": "Musnad Ahmad",
        "total_hadiths": sum((int(s["last"]) - int(s["first"]) + 1) for s in temp_sections if s["last"] and s["first"]),
        "available_languages": "ar,ur",
        "intro": "Musnad Ahmad scraped from al-hadees.com"
    },
    "translations": [
        {
            "language": "ar",
            "sections": str(len(temp_sections)),
            "path": "translations/ar"
        },
        {
            "language": "ur",
            "sections": str(len(temp_sections)),
            "path": "translations/ur"
        }
    ],
    "sections": []
}

for s in temp_sections:
    name_ar = s.get("name_ar", "").strip()
    name_ur = s.get("name_ur", "").strip()
    
    # Fill empties
    if not name_ar and not name_ur:
        name_ar = f"باب {s['id']}"
        name_ur = f"باب {s['id']}"
    elif not name_ar:
        name_ar = name_ur
    elif not name_ur:
        name_ur = name_ar
        
    info["sections"].append({
        "id": s["id"],
        "name": name_ar,
        "name_ar": name_ar,
        "name_en": "",
        "name_ur": name_ur,
        "hadith_first": s["first"],
        "hadith_last": s["last"],
        "arabic_first": s["first"],
        "arabic_last": s["last"]
    })

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print(f"Generated info.json with {len(temp_sections)} sections.")
