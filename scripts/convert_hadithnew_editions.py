#!/usr/bin/env python3
"""Convert fawazahmed0 Urdu/Bengali editions to sunnah.com-download JSON format."""

import json
import os
import glob

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sunnah.com-download")
EDITIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hadith-new", "editions")

# Map fawazahmed0 edition names to sunnah.com slugs + lang codes
EDITIONS = {
    # Urdu
    "urd-bukhari": ("bukhari", "ur"),
    "urd-muslim": ("muslim", "ur"),
    "urd-abudawud": ("abudawud", "ur"),
    "urd-tirmidhi": ("tirmidhi", "ur"),
    "urd-nasai": ("nasai", "ur"),
    "urd-ibnmajah": ("ibnmajah", "ur"),
    "urd-malik": ("malik", "ur"),
    # Bengali
    "ben-bukhari": ("bukhari", "bn"),
    "ben-muslim": ("muslim", "bn"),
    "ben-abudawud": ("abudawud", "bn"),
    "ben-tirmidhi": ("tirmidhi", "bn"),
    "ben-nasai": ("nasai", "bn"),
    "ben-ibnmajah": ("ibnmajah", "bn"),
    "ben-malik": ("malik", "bn"),
    "ben-nawawi": ("nawawi40", "bn"),
}


def sort_key(h):
    """Sort by hadithnumber, handling fractional numbers like '402.2'."""
    hn = h["hadithnumber"]
    parts = hn.split(".")
    return (int(parts[0]), float(parts[1]) if len(parts) > 1 else 0)


def convert_edition(edition_path, target_slug, lang_code):
    """Convert one edition file to sunnah.com-download format."""
    with open(edition_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hadiths = data.get("hadiths", [])
    if not hadiths:
        print(f"  No hadiths in {os.path.basename(edition_path)}")
        return

    converted = []
    for h in hadiths:
        hn = h.get("hadithnumber")
        text = h.get("text", "")
        if hn is not None:
            converted.append({
                "hadithnumber": str(hn),
                "text": text,
            })

    if not converted:
        print(f"  No valid hadiths in {os.path.basename(edition_path)}")
        return

    target_dir = os.path.join(OUT_DIR, target_slug)
    os.makedirs(target_dir, exist_ok=True)
    out_path = os.path.join(target_dir, f"{lang_code}.json")

    # Merge with existing
    existing = {}
    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            try:
                for item in json.load(f):
                    existing[item["hadithnumber"]] = item
            except:
                pass

    for h in converted:
        hn = h["hadithnumber"]
        if hn in existing:
            existing[hn]["text"] = h["text"]
        else:
            existing[hn] = h

    ordered = sorted(existing.values(), key=sort_key)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)

    with_text = sum(1 for h in ordered if h.get("text"))
    print(f"  {os.path.basename(edition_path)} -> {target_slug}/{lang_code}.json ({len(ordered)} hadiths, {with_text} with text)")


def main():
    print("Converting fawazahmed0 editions to sunnah.com-download format...")
    converted = 0
    failed = 0

    for edition_name, (target_slug, lang_code) in EDITIONS.items():
        # Try .min.json first, then .json
        for ext in [".min.json", ".json"]:
            path = os.path.join(EDITIONS_DIR, edition_name + ext)
            if os.path.exists(path):
                try:
                    convert_edition(path, target_slug, lang_code)
                    converted += 1
                except Exception as e:
                    print(f"  ERROR converting {edition_name}: {e}")
                    failed += 1
                break
        else:
            print(f"  NOT FOUND: {edition_name}")

    print(f"\nDone: {converted} converted, {failed} failed")


if __name__ == "__main__":
    main()
