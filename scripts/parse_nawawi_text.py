#!/usr/bin/env python3
"""
Parse hadith data from sunnah.com HTML that was already fetched.
Extract Arabic and English text for nawawi40.
"""

import re
import json
import os


# The HTML content from webfetch (I'll parse the text version)
def parse_nawawi_from_text(text):
    """Parse hadiths from the text content."""
    hadiths = []

    # Pattern to match hadith entries
    # Hadith X, 40 Hadith an-Nawawi...English text...[Bukhari & Muslim]...Arabic text

    # Split by hadith markers
    pattern = r"Hadith (\d+), 40 Hadith an-Nawawi"
    parts = re.split(pattern, text)

    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            hadith_num = parts[i]
            content = parts[i + 1] if i + 1 < len(parts) else ""

            # Extract English text (between hadith marker and Arabic)
            # Look for the pattern where Arabic starts
            arabic_start = content.find("عَنْ")
            if arabic_start == -1:
                arabic_start = content.find("الحمد لله")  # For intro

            if arabic_start > 0:
                english = content[:arabic_start].strip()
                arabic = content[arabic_start:].strip()

                # Clean up English - remove reference lines
                english = re.sub(r"Reference.*?Copy ▼", "", english, flags=re.DOTALL)
                english = re.sub(r"\[.*?\]", "", english)  # Remove [Bukhari & Muslim]
                english = english.strip()

                # Clean up Arabic - stop at next hadith or end
                arabic = arabic.split("Reference")[0].strip()

                hadiths.append(
                    {"hadithnumber": hadith_num, "arabic": arabic, "english": english}
                )

    return hadiths


def main():
    # Read the text file that was saved from webfetch
    text_file = (
        "/home/saboor/.local/share/opencode/tool-output/tool_d8f3a0fcb001qxIwYYFSpU6WLs"
    )

    if not os.path.exists(text_file):
        print(f"Text file not found: {text_file}")
        return

    with open(text_file, "r", encoding="utf-8") as f:
        text = f.read()

    hadiths = parse_nawawi_from_text(text)

    print(f"Found {len(hadiths)} hadiths")

    if hadiths:
        print("\nFirst hadith:")
        print(json.dumps(hadiths[0], indent=2, ensure_ascii=False))

        print("\nSecond hadith:")
        print(json.dumps(hadiths[1], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
