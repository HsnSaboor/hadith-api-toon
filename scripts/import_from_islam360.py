#!/usr/bin/env python3
import json
import os
import sys
import csv
import io
import re

RAW_SOURCE_DIR = "/home/saboor/takhreej-source/hadith"
EDITIONS_DIR = os.path.join(os.getcwd(), "editions")

# Map Takhreej filenames to target edition IDs
BOOK_MAP = {
    "musnad": "musnad-ahmed",
    "mustadrak": "mustadrak",
    "beyhaqi": "bayhaqi",
    "khuzaymah": "sahih-ibn-khuzaymah",
    "shaybah": "musannaf-ibn-abi-shaybah",
    "silsila": "silsila-sahih",
    "darmi": "sunan-darmi",
    "mishkat": "mishkat",
    "alzawaid": "muajam-tabarani-saghir", # Approximation or new folder needed
}

def escape_toon_val(value):
    if value is None: return ""
    s = str(value).strip()
    if not s: return ""
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s

def yaml_like(d, indent=0):
    lines = []
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{k}:")
            lines.append(yaml_like(v, indent + 1))
        else:
            lines.append(f'{prefix}{k}: "{v}"')
    return "\n".join(lines)

def process_book(i360_key, edition_id):
    jsonl_path = os.path.join(RAW_SOURCE_DIR, f"{i360_key}.jsonl")
    if not os.path.exists(jsonl_path):
        print(f"Skipping {i360_key}, file not found.")
        return

    print(f"Processing {i360_key} -> {edition_id}")
    
    # Group by kitab_id (section)
    sections = {} # kitab_id -> [records]
    kitab_names = {} # kitab_id -> name_ar, name_ur, name_en
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                kid = rec.get("kitab_id", 1)
                sections.setdefault(kid, []).append(rec)
                if kid not in kitab_names:
                    kitab_names[kid] = {
                        "ar": rec.get("kitab", ""),
                        "ur": rec.get("kitab", ""), # Takhreej usually has Urdu name here
                        "en": rec.get("kitab_eng", "")
                    }
            except: continue

    # 1. Write Arabic Sections
    ar_sec_dir = os.path.join(EDITIONS_DIR, edition_id, "sections")
    os.makedirs(ar_sec_dir, exist_ok=True)
    
    total_h = 0
    section_meta = []

    for kid in sorted(sections.keys()):
        recs = sections[kid]
        rows = []
        for r in recs:
            hn = r["hadees_number"]
            arabic = r.get("arabic", "")
            # Mustadrak format: hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro
            row = [str(hn), arabic, "", "", str(r.get("international_number", "")), "", ""]
            rows.append(row)
        
        total_h += len(recs)
        out_path = os.path.join(ar_sec_dir, f"{kid}.toon")
        header = f"hadiths[{len(rows)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:"
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header + "\n")
            for row in rows:
                f.write(",".join(escape_toon_val(v) for v in row) + "\n")
        
        # Collect for info.toon
        section_meta.append({
            "id": kid,
            "name": kitab_names[kid]["en"] or kitab_names[kid]["ur"],
            "name_ar": kitab_names[kid]["ar"],
            "name_ur": kitab_names[kid]["ur"],
            "hadith_first": recs[0]["hadees_number"],
            "hadith_last": recs[-1]["hadees_number"]
        })

    # 2. Write Urdu Translations
    ur_sec_dir = os.path.join(EDITIONS_DIR, edition_id, "translations", "ur", "sections")
    os.makedirs(ur_sec_dir, exist_ok=True)
    for kid in sorted(sections.keys()):
        recs = sections[kid]
        out_path = os.path.join(ur_sec_dir, f"{kid}.toon")
        lines = []
        for r in recs:
            text = ""
            for t in r.get("translations", []):
                if t.get("language_id") == 1: # Urdu
                    # Combine ravi + hadees + takhreej for maximum info
                    ravi = (t.get("ravi") or "").strip()
                    hadees = (t.get("hadees") or "").strip()
                    takh = (t.get("Takhreej") or "").strip()
                    
                    parts = []
                    if ravi: parts.append(ravi)
                    if hadees: parts.append(hadees)
                    if takh: parts.append(f"\n[تخریج]: {takh}")
                    
                    text = "\n".join(parts)
                    break
            lines.append(json.dumps({"hadithnumber": str(r["hadees_number"]), "text": text}, ensure_ascii=False))
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # 3. Write Translation Metadata
    ur_meta_path = os.path.join(EDITIONS_DIR, edition_id, "translations", "ur", "metadata.toon")
    ur_meta = {
        "metadata": {
            "language": "ur",
            "language_name": "Urdu",
            "script": "Arabic",
            "total_hadiths": total_h,
            "source": "takhreej"
        }
    }
    with open(ur_meta_path, "w", encoding="utf-8") as f:
        f.write(yaml_like(ur_meta) + "\n")

    # 4. Update info.toon
    info_path = os.path.join(EDITIONS_DIR, edition_id, "info.toon")
    # We'll just overwrite it to ensure it's correct
    book_name = edition_id.replace("-", " ").title()
    info_content = [
        "metadata:",
        f"  book_id: {edition_id}",
        f'  book_name: "{book_name}"',
        f"  total_hadiths: {total_h}",
        f'  available_languages: "ar,ur"',
        '  intro: ""',
        "",
        f"sections[{len(section_meta)}]{{id,name,name_ar,name_ur,hadith_first,hadith_last}}:"
    ]
    for s in section_meta:
        info_content.append(f'  {s["id"]},{escape_toon_val(s["name"])},{escape_toon_val(s["name_ar"])},{escape_toon_val(s["name_ur"])},{s["hadith_first"]},{s["hadith_last"]}')
    
    with open(info_path, "w", encoding="utf-8") as f:
        f.write("\n".join(info_content) + "\n")

if __name__ == "__main__":
    for k, v in BOOK_MAP.items():
        process_book(k, v)
