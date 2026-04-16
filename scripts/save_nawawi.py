#!/usr/bin/env python3
"""
Parse and save hadith data from sunnah.com for nawawi40, dehlawi, and qudsi.
"""

import re
import json
import os

BASE_PATH = "/home/saboor/code/hadith-api-toon/editions"


def parse_hadiths_from_text(text, book_name):
    """Parse hadiths from text content."""
    hadiths = []

    if book_name == "nawawi":
        # Pattern for nawawi40
        pattern = r"Hadith (\d+), 40 Hadith an-Nawawi"
        parts = re.split(pattern, text)

        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                hadith_num = parts[i]
                content = parts[i + 1] if i + 1 < len(parts) else ""

                # Find Arabic start
                arabic_start = content.find("عَنْ")
                if arabic_start == -1:
                    arabic_start = content.find("الحمد لله")

                if arabic_start > 0:
                    english = content[:arabic_start].strip()
                    arabic = content[arabic_start:].strip()

                    # Clean English
                    english = re.sub(
                        r"Reference.*?Copy ▼", "", english, flags=re.DOTALL
                    )
                    english = re.sub(r"\[.*?\]", "", english)
                    english = english.strip()

                    # Clean Arabic
                    arabic = arabic.split("Reference")[0].strip()

                    hadiths.append(
                        {
                            "hadithnumber": hadith_num,
                            "arabic": arabic,
                            "english": english,
                        }
                    )

    return hadiths


def save_hadiths(book_name, hadiths):
    """Save hadiths to toon format files."""
    book_path = os.path.join(BASE_PATH, book_name)

    # Create translations/en/sections/1.toon for English
    en_dir = os.path.join(book_path, "translations", "en", "sections")
    os.makedirs(en_dir, exist_ok=True)

    en_path = os.path.join(en_dir, "1.toon")
    with open(en_path, "w", encoding="utf-8") as f:
        for h in hadiths:
            if "english" in h and h["english"]:
                json_line = json.dumps(
                    {"hadithnumber": h["hadithnumber"], "text": h["english"]},
                    ensure_ascii=False,
                )
                f.write(json_line + "\n")

    print(f"  Saved English to {en_path}")

    # Create translations/ar/sections/1.toon for Arabic
    ar_dir = os.path.join(book_path, "translations", "ar", "sections")
    os.makedirs(ar_dir, exist_ok=True)

    ar_path = os.path.join(ar_dir, "1.toon")
    with open(ar_path, "w", encoding="utf-8") as f:
        for h in hadiths:
            if "arabic" in h and h["arabic"]:
                json_line = json.dumps(
                    {"hadithnumber": h["hadithnumber"], "text": h["arabic"]},
                    ensure_ascii=False,
                )
                f.write(json_line + "\n")

    print(f"  Saved Arabic to {ar_path}")


def main():
    # Read nawawi text
    text_file = (
        "/home/saboor/.local/share/opencode/tool-output/tool_d8f3a0fcb001qxIwYYFSpU6WLs"
    )

    if os.path.exists(text_file):
        with open(text_file, "r", encoding="utf-8") as f:
            text = f.read()

        print("=== Processing nawawi ===")
        hadiths = parse_hadiths_from_text(text, "nawawi")
        print(f"  Found {len(hadiths)} hadiths")

        if hadiths:
            save_hadiths("nawawi", hadiths)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
