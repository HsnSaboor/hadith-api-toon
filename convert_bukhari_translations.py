import os
import json
import csv
import re

bukhari_dir = "/home/saboor/code/hadith-api-toon/sunnah.com-download/bukhari"
translations_dir = os.path.join(bukhari_dir, "translations")
template_file = os.path.join(bukhari_dir, "en.json")

def parse_toon_file(filepath):
    hadiths = {}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    # The format starts with hadiths[count]{hadithnumber,text}:
    # followed by lines like "1","some text..."
    
    # Let's split by newline and parse each line that starts with a quote
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line.startswith('"'):
            continue
            
        # We can use csv reader to parse the single line
        reader = csv.reader([line])
        try:
            row = next(reader)
            if len(row) >= 2:
                num = row[0]
                text = row[1]
                hadiths[num] = text
        except Exception as e:
            print(f"Error parsing line in {filepath}: {line[:50]}... Error: {e}")
            
    return hadiths

def main():
    print("Loading en.json template...")
    with open(template_file, "r", encoding="utf-8") as f:
        template_data = json.load(f)
        
    expected_count = len(template_data)
    print(f"Template has {expected_count} hadiths.")
    
    langs = [d for d in os.listdir(translations_dir) if os.path.isdir(os.path.join(translations_dir, d))]
    langs = [l for l in langs if l not in ("ar", "bn", "en", "ur")]
    print(f"Found languages to convert: {langs}")
    
    for lang in langs:
        print(f"\nProcessing language: {lang}")
        lang_dir = os.path.join(translations_dir, lang, "sections")
        
        if not os.path.exists(lang_dir):
            print(f"  Warning: No sections directory for {lang}")
            continue
            
        lang_hadiths = {}
        toon_files = [f for f in os.listdir(lang_dir) if f.endswith(".toon")]
        for tfile in toon_files:
            filepath = os.path.join(lang_dir, tfile)
            parsed = parse_toon_file(filepath)
            lang_hadiths.update(parsed)
            
        print(f"  Extracted {len(lang_hadiths)} hadiths from .toon files.")
        
        # Verify
        missing = 0
        lang_json_data = []
        for item in template_data:
            num = str(item["hadithnumber"]).strip()
            new_item = dict(item)
            
            # Helper to fetch text, ignoring "b" suffixes if not exactly present
            def get_text(n):
                if n in lang_hadiths:
                    return lang_hadiths[n]
                # Sometimes en.json has "402b", but toon has "402".
                if n.endswith("b") and n[:-1] in lang_hadiths:
                    return "" # Skip duplicate text for the 'b' part
                if n.endswith("a") and n[:-1] in lang_hadiths:
                    return lang_hadiths[n[:-1]]
                return None
                
            text = get_text(num)
            if text is not None:
                new_item["text"] = text
            else:
                # check composite e.g., "272, 273"
                if ", " in num:
                    parts = num.split(", ")
                    text_parts = []
                    found_all = True
                    for p in parts:
                        t = get_text(p)
                        if t is None:
                            found_all = False
                            break
                        if t: text_parts.append(t)
                        
                    if found_all:
                        new_item["text"] = " ".join(text_parts)
                    else:
                        new_item["text"] = ""
                        missing += 1
                else:
                    new_item["text"] = ""
                    missing += 1
                    
            lang_json_data.append(new_item)
            
        if missing > 0:
            print(f"  Verification Warning: {missing} hadiths missing in {lang} translations.")
        else:
            print(f"  Verification Success: All {expected_count} hadiths found for {lang}.")
            
        # Save to json
        out_filepath = os.path.join(bukhari_dir, f"{lang}.json")
        with open(out_filepath, "w", encoding="utf-8") as f:
            json.dump(lang_json_data, f, ensure_ascii=False, indent=2)
            
        print(f"  Saved to {lang}.json")

if __name__ == "__main__":
    main()
