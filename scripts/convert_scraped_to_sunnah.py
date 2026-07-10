#!/usr/bin/env python3
"""Convert scraped_data .toon files to sunnah.com-download JSON format."""

import json
import os
import re

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sunnah.com-download")
SCRAPED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraped_data")

# Map scraped_data dir names to sunnah.com-download slugs
SLUG_MAP = {
    "bukhari": "bukhari",
    "muslim": "muslim",
    "abudawud": "abudawud",
    "tirmidhi": "tirmidhi",
    "nasai": "nasai",
    "ibnmajah": "ibnmajah",
    "malik": "malik",
    "musnad-ahmed": "ahmad",
    "sunan-darmi": "darimi",
    "sahih-ibn-khuzaymah": "ibnkhuzayma",
    "mustadrak": "hakim",
    "musannaf-ibn-abi-shaybah": "ibnabishayba",
    "sunan-al-daraqutni": "daraqutni",
    "bayhaqi": "bayhaqi",
    "shamail-tirmazi": "shamail",
    "mishkat": "mishkat",
    "bulugh-al-maram": "bulugh",
    "aladab-almufrad": "adab",
}

LANG_MAP = {
    "urdu": "ur",
    "english": "en",
    "bangla": "bn",
    "bosnian": "bs",
}


def parse_toon(filepath):
    """Parse a .toon file: hadiths[N]{hadithnumber,text}: line followed by "id","text" lines."""
    hadiths = []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("hadiths"):
            continue
        # Parse "number","text"
        m = re.match(r'^"(\d+)","(.*)"$', line)
        if m:
            hadiths.append({
                "hadithnumber": m.group(1),
                "text": m.group(2),
            })
        else:
            # Try without quotes
            m = re.match(r'^(\d+),"(.*)"$', line)
            if m:
                hadiths.append({
                    "hadithnumber": m.group(1),
                    "text": m.group(2),
                })
    return hadiths


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    converted = 0
    total_files = 0

    for src_dir, target_slug in SLUG_MAP.items():
        dirpath = os.path.join(SCRAPED_DIR, src_dir)
        if not os.path.isdir(dirpath):
            continue

        for fname in os.listdir(dirpath):
            if not fname.endswith(".toon"):
                continue

            lang_name = fname.replace(".toon", "")
            # Only import Urdu from scraped_data (skip English/Bangla/Bosnian)
            if lang_name != "urdu":
                print(f"  SKIP {src_dir}/{fname} (only importing Urdu)")
                total_files += 1
                continue
            total_files += 1

            lang_code = LANG_MAP.get(lang_name, lang_name[:2])

            # Read and parse the .toon file
            filepath = os.path.join(dirpath, fname)
            hadiths = parse_toon(filepath)
            if not hadiths:
                print(f"  Empty: {src_dir}/{fname}")
                continue

            # Write to sunnah.com-download
            target_dir = os.path.join(OUT_DIR, target_slug)
            os.makedirs(target_dir, exist_ok=True)
            out_path = os.path.join(target_dir, f"{lang_code}.json")

            # If file already exists, merge without overwriting existing rich fields
            existing = {}
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    try:
                        for item in json.load(f):
                            existing[item["hadithnumber"]] = item
                    except:
                        pass

            for h in hadiths:
                hn = h["hadithnumber"]
                if hn in existing:
                    existing[hn]["text"] = h["text"]
                else:
                    existing[hn] = h

            ordered = sorted(existing.values(), key=lambda x: int(x["hadithnumber"]))
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(ordered, f, ensure_ascii=False, indent=2)

            print(f"  {src_dir}/{fname} -> {target_slug}/{lang_code}.json ({len(ordered)} hadiths)")
            converted += 1

    print(f"\nConverted {converted}/{total_files} files")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
