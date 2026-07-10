#!/usr/bin/env python3
import os
import re
from pathlib import Path

BASE_DIR = Path("/home/saboor/code/hadith-api-toon/editions")
ZW = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]')

def fix_zero_width():
    print("Fixing ZERO_WIDTH characters in all toon files...")
    fixed_count = 0
    file_count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            if f.endswith(".toon"):
                path = Path(root) / f
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                if ZW.search(content):
                    cleaned = ZW.sub("", content)
                    with open(path, "w", encoding="utf-8") as file:
                        file.write(cleaned)
                    fixed_count += 1
                    print(f"  [FIXED ZW] {path.relative_to(BASE_DIR)}")
                file_count += 1
    print(f"Done! Cleaned zero-width characters in {fixed_count} files (scanned {file_count} files).")

if __name__ == "__main__":
    fix_zero_width()
