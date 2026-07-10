#!/usr/bin/env python3
"""Script to fully repair and align fatah-alrabani using scraped JSON data."""

import os
import re
import csv
import json

BASE_DIR = "/home/saboor/code/hadith-api-toon/editions/fatah-alrabani"
SCRAPED_JSON = "/home/saboor/code/hadith-api-toon/scraped_data/fatah-alrabani/scrape_result.json"

def clean_arabic(text):
    if not text:
        return ""
    # Strip leading Urdu digits and punctuation like "۔ (۱۶۶)۔ "
    cleaned = re.sub(r'^[۔\s]*\([\d\u06f0-\u06f9\s]+\)[۔\s]*', '', text.strip())
    return cleaned.strip()

def main():
    if not os.path.exists(SCRAPED_JSON):
        print(f"Scraped JSON not found at {SCRAPED_JSON}")
        return

    with open(SCRAPED_JSON, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)
    
    results = scraped_data.get("results", [])
    scraped_map = {}
    for entry in results:
        hn = str(entry.get("hadith_num", ""))
        if hn:
            scraped_map[hn] = {
                "arabic": clean_arabic(entry.get("arabic", "")),
                "urdu": entry.get("urdu", "").strip(),
                "english": entry.get("english", "").strip()
            }
            
    print(f"Loaded {len(scraped_map)} entries from scrape_result.json")

    # 1. Update main sections: 1.toon, 2.toon, 3.toon
    sections_dir = os.path.join(BASE_DIR, "sections")
    for sec_file in sorted(os.listdir(sections_dir)):
        if not sec_file.endswith(".toon"):
            continue
        path = os.path.join(sections_dir, sec_file)
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        lines = content.split('\n')
        header = lines[0]
        rows_content = []
        
        # Parse rows using csv reader
        reader = csv.reader(lines[1:])
        updated_count = 0
        for row in reader:
            if not row:
                continue
            hn = row[0]
            if hn in scraped_map:
                # If arabic is empty, populate it
                if not row[1].strip():
                    row[1] = scraped_map[hn]["arabic"]
                    updated_count += 1
                # If other fields are placeholder empty, populate them
                # reference: row[3]
                if not row[3].strip():
                    row[3] = f"Fatah Al-Rabani {hn}"
                # international_number: row[4]
                if not row[4].strip():
                    row[4] = hn
            rows_content.append(row)
            
        # Write back
        new_content = [header]

        for row in rows_content:
            # write row to buffer
            import io
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator='')
            w.writerow(row)
            new_content.append(buf.getvalue())
            
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_content) + "\n")
        print(f"Updated main section {sec_file}: filled {updated_count} empty Arabic entries.")

    # 2. Update/create translations: ur, en, ar
    langs = ["ur", "en", "ar"]
    for lang in langs:
        lang_sections_dir = os.path.join(BASE_DIR, "translations", lang, "sections")
        os.makedirs(lang_sections_dir, exist_ok=True)
        
        # We want to create 1.toon, 2.toon, 3.toon to match main sections
        for sec_file in sorted(os.listdir(sections_dir)):
            if not sec_file.endswith(".toon"):
                continue
            
            # Read main section to get hadith numbers in this section
            main_sec_path = os.path.join(sections_dir, sec_file)
            with open(main_sec_path, "r", encoding="utf-8") as f:
                main_lines = f.read().split('\n')
            
            hns = []
            reader = csv.reader(main_lines[1:])
            for row in reader:
                if row:
                    hns.append(row[0])
            
            # Rebuild translation toon slice
            header = f"hadiths[{len(hns)}]{{hadithnumber,text}}:"
            new_lines = [header]
            
            for hn in hns:
                text = ""
                if hn in scraped_map:
                    if lang == "ur":
                        text = scraped_map[hn]["urdu"]
                    elif lang == "en":
                        text = scraped_map[hn]["english"]
                    elif lang == "ar":
                        text = scraped_map[hn]["arabic"]
                
                # Format to CSV
                buf = io.StringIO()
                w = csv.writer(buf, lineterminator='')
                w.writerow([hn, text])
                new_lines.append(buf.getvalue())
                
            lang_sec_path = os.path.join(lang_sections_dir, sec_file)
            with open(lang_sec_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")
            print(f"Wrote translation slice: {lang}/sections/{sec_file}")

    # 3. Synchronize fatah-alrabani/info.toon metadata and tables
    info_path = os.path.join(BASE_DIR, "info.toon")
    with open(info_path, "r", encoding="utf-8") as f:
        info_content = f.read()
        
    lines = info_content.split('\n')
    # Update total_hadiths in metadata block to 89 (which is correct)
    for i, line in enumerate(lines):
        if line.strip().startswith("total_hadiths:"):
            lines[i] = "  total_hadiths: 89"
        elif line.strip().startswith("available_languages:"):
            lines[i] = '  available_languages: "ar,en,ur"'
            
    # Update translations block to match 3 sections
    trans_start = -1
    trans_end = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("translations["):
            trans_start = i
            break
            
    if trans_start != -1:
        for i in range(trans_start + 1, len(lines)):
            if not lines[i].strip() or 'sections[' in lines[i]:
                trans_end = i
                break
        if trans_end == -1:
            trans_end = len(lines)
            
        trans_block = [
            'translations[3]{language,sections,path}:',
            '"ar","3","translations/ar"',
            '"en","3","translations/en"',
            '"ur","3","translations/ur"'
        ]
        lines[trans_start:trans_end] = trans_block
        
    with open(info_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Updated fatah-alrabani/info.toon with synchronized translations block.")

if __name__ == "__main__":
    import io
    main()
