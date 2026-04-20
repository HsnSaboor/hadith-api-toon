#!/usr/bin/env python3
import json
import os
import sys

ISLAM360_DIR = "/home/saboor/islam360_downloads/hadith"
EDITIONS_DIR = os.path.join(os.getcwd(), "editions")

# Map Islam360 filenames to target edition IDs
BOOK_MAP = {
    "bukhari": "bukhari",
    "muslim": "muslim",
    "abu_dawood": "abudawud",
    "tirmazi": "tirmidhi",
    "nasai": "nasai",
    "maja": "ibnmajah",
    "mishkat": "mishkat",
}

LANG_MAP = {
    3: "hi", # Hindi
    4: "ro", # Roman Urdu
}

def import_hi_ro(i360_key, edition_id):
    jsonl_path = os.path.join(ISLAM360_DIR, f"{i360_key}.jsonl")
    if not os.path.exists(jsonl_path):
        return

    print(f"Extracting HI/RO for {edition_id}...")
    
    # Store translations by language then kitab_id
    # data[lang][kitab_id] = [json_lines]
    data = {"hi": {}, "ro": {}}
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                kid = rec.get("kitab_id", 1)
                hn = str(rec["hadees_number"])
                
                for trans in rec.get("translations", []):
                    lid = trans.get("language_id")
                    if lid in LANG_MAP:
                        lang = LANG_MAP[lid]
                        text = (trans.get("hadees") or "").strip()
                        if text:
                            data[lang].setdefault(kid, []).append(
                                json.dumps({"hadithnumber": hn, "text": text}, ensure_ascii=False)
                            )
            except: continue

    # Write files
    for lang in ["hi", "ro"]:
        if not data[lang]: continue
        
        base_dir = os.path.join(EDITIONS_DIR, edition_id, "translations", lang, "sections")
        os.makedirs(base_dir, exist_ok=True)
        
        for kid, lines in data[lang].items():
            out_path = os.path.join(base_dir, f"{kid}.toon")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        
        # Write metadata.toon if missing
        meta_path = os.path.join(EDITIONS_DIR, edition_id, "translations", lang, "metadata.toon")
        if not os.path.exists(meta_path):
            lang_name = "Hindi" if lang == "hi" else "Roman Urdu"
            with open(meta_path, "w") as f:
                f.write(f"metadata:\n  language: {lang}\n  language_name: {lang_name}\n  source: islam360\n")

if __name__ == "__main__":
    for k, v in BOOK_MAP.items():
        import_hi_ro(k, v)
    print("Done!")
