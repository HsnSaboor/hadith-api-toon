#!/usr/bin/env python3
import os
import re

BASE_DIR = os.getcwd()
INFO_PATH = os.path.join(BASE_DIR, "info.toon")
EDITIONS_DIR = os.path.join(BASE_DIR, "editions")

def get_book_info(book_id):
    info_path = os.path.join(EDITIONS_DIR, book_id, "info.toon")
    if not os.path.exists(info_path):
        return None
    
    with open(info_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    total_hadiths = 0
    m = re.search(r"total_hadiths:\s*(\d+)", content)
    if m: total_hadiths = int(m.group(1))
    
    available_languages = ""
    m = re.search(r'available_languages:\s*"([^"]+)"', content)
    if m: available_languages = m.group(1)
    
    # name
    name = book_id.replace("-", " ").title()
    m = re.search(r'book_name:\s*"([^"]+)"', content)
    if m: name = m.group(1)

    return {
        "total": total_hadiths,
        "langs": available_languages,
        "name": name
    }

def main():
    if not os.path.exists(INFO_PATH):
        print("info.toon not found")
        return

    with open(INFO_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    in_books = False
    for line in lines:
        if line.startswith("books["):
            in_books = True
            new_lines.append(line)
            continue
        
        if in_books:
            if not line.strip():
                in_books = False
                new_lines.append(line)
                continue
            
            # Parse CSV-like line: id,name,total,langs,path
            parts = []
            current = ""
            in_q = False
            for ch in line.strip():
                if ch == '"': in_q = not in_q; current += ch
                elif ch == "," and not in_q: parts.append(current); current = ""
                else: current += ch
            parts.append(current)
            
            if len(parts) >= 5:
                book_id = parts[0].strip()
                info = get_book_info(book_id)
                if info:
                    # Update name, total, langs
                    parts[1] = f'"{info["name"]}"'
                    parts[2] = str(info["total"])
                    parts[3] = f'"{info["langs"]}"'
                    new_lines.append("  " + ",".join(parts) + "\n")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(INFO_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("info.toon updated successfully.")

if __name__ == "__main__":
    main()
