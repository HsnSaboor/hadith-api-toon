#!/usr/bin/env python3
"""
Extract nawawi40 Arabic and English from git history.
"""

import subprocess
import json
import os

BASE_PATH = "/home/saboor/code/hadith-api-toon/editions/nawawi"


def get_git_file(commit, path):
    """Get file content from git."""
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"], capture_output=True, text=True
    )
    return result.stdout


def parse_old_toon(content):
    """Parse old toon format with hadiths[count]{...} header."""
    hadiths = []
    lines = content.strip().split("\n")

    # Skip header lines until we find hadiths[ line
    data_started = False
    for line in lines:
        if "hadiths[" in line and "{" in line:
            data_started = True
            continue
        if not data_started:
            continue
        if not line.strip():
            continue

        # Parse CSV: hadithnumber,"text",...
        parts = []
        current = ""
        in_quotes = False
        i = 0
        while i < len(line):
            char = line[i]
            if char == '"':
                if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                    current += '"'
                    i += 2
                    continue
                in_quotes = not in_quotes
            elif char == "," and not in_quotes:
                parts.append(current)
                current = ""
            else:
                current += char
            i += 1
        parts.append(current)

        if len(parts) >= 2:
            hadithnumber = parts[0].strip()
            text = parts[1].strip().strip('"')
            # Skip header row
            if hadithnumber != "hadithnumber" and hadithnumber and text:
                hadiths.append({"hadithnumber": hadithnumber, "text": text})

    return hadiths


def save_language(lang_code, hadiths):
    """Save hadiths for a specific language."""
    lang_dir = os.path.join(BASE_PATH, "translations", lang_code, "sections")
    os.makedirs(lang_dir, exist_ok=True)

    output_path = os.path.join(lang_dir, "1.toon")
    with open(output_path, "w", encoding="utf-8") as f:
        for h in hadiths:
            json_line = json.dumps(h, ensure_ascii=False)
            f.write(json_line + "\n")

    print(f"  Saved {lang_code}: {len(hadiths)} hadiths")


def main():
    # Extract Arabic
    print("\n=== Extracting Arabic ===")
    content = get_git_file("56db4b8^", "editions/ara-nawawi/sections/1.toon")
    if content:
        hadiths = parse_old_toon(content)
        if hadiths:
            save_language("ar", hadiths)
        else:
            print("  No Arabic hadiths parsed")
    else:
        print("  Arabic file not found")

    # Extract English
    print("\n=== Extracting English ===")
    content = get_git_file("56db4b8^", "editions/eng-nawawi/sections/1.toon")
    if content:
        hadiths = parse_old_toon(content)
        if hadiths:
            save_language("en", hadiths)
        else:
            print("  No English hadiths parsed")
    else:
        print("  English file not found")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
