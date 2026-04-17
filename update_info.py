#!/usr/bin/env python3
import os

TOON = "/home/saboor/code/hadith-api-toon"

for book in os.listdir(os.path.join(TOON, "editions")):
    trans_path = os.path.join(TOON, "editions", book, "translations")
    info_path = os.path.join(TOON, "editions", book, "info.toon")
    
    if not os.path.exists(trans_path):
        continue
    
    langs = [l for l in os.listdir(trans_path) if os.path.isdir(os.path.join(trans_path, l))]
    
    if not langs:
        continue
    
    print(f"{book}: {langs}")
    
    if os.path.exists(info_path):
        with open(info_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if 'available_languages:' in line:
                lang_str = ','.join(langs)
                new_lines.append(f"  available_languages: \"{lang_str}\"\n")
            else:
                new_lines.append(line)
        
        with open(info_path, 'w') as f:
            f.writelines(new_lines)

print("\nDone!")