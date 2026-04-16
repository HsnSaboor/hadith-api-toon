#!/usr/bin/env python3
"""
Scrape all language versions of nawawi40 from sunnah.com
"""

import subprocess
import json
import os
import re

BASE_PATH = "/home/saboor/code/hadith-api-toon/editions/nawawi"


def run_playwright(language):
    """Use playwright to get page content for a specific language."""
    code = f'''
await state.page.goto("https://sunnah.com/nawawi40", {{ waitUntil: "domcontentloaded" }});
await waitForPageLoad({{ page: state.page, timeout: 5000 }});

// Click language if not English
if ("{language}" !== "english") {{
  await state.page.locator("#ch_{language}").click();
  await state.page.waitForTimeout(3000);
}}

// Get text content
const text = await state.page.evaluate(() => document.body.innerText);
console.log(text);
'''

    result = subprocess.run(
        ["playwriter", "-s", "1", "-e", code],
        capture_output=True,
        text=True,
        timeout=60000,
    )

    return result.stdout


def parse_hadiths_from_text(text, language):
    """Parse hadiths from text content."""
    hadiths = []

    # Pattern to match hadith entries
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
                translation = content[:arabic_start].strip()
                arabic = content[arabic_start:].strip()

                # Clean translation
                translation = re.sub(
                    r"Reference.*?Copy ▼", "", translation, flags=re.DOTALL
                )
                translation = re.sub(r"\[.*?\]", "", translation)
                translation = translation.strip()

                # Clean Arabic
                arabic = arabic.split("Reference")[0].strip()

                hadiths.append(
                    {"hadithnumber": hadith_num, "arabic": arabic, "text": translation}
                )

    return hadiths


def save_language(lang_code, hadiths):
    """Save hadiths for a specific language."""
    lang_dir = os.path.join(BASE_PATH, "translations", lang_code, "sections")
    os.makedirs(lang_dir, exist_ok=True)

    output_path = os.path.join(lang_dir, "1.toon")
    with open(output_path, "w", encoding="utf-8") as f:
        for h in hadiths:
            if "text" in h and h["text"]:
                json_line = json.dumps(
                    {"hadithnumber": h["hadithnumber"], "text": h["text"]},
                    ensure_ascii=False,
                )
                f.write(json_line + "\n")

    print(f"  Saved {lang_code}: {len(hadiths)} hadiths to {output_path}")


def main():
    languages = [("english", "en"), ("bangla", "bn"), ("bosnian", "bs")]

    for lang_name, lang_code in languages:
        print(f"\n=== Fetching {lang_name} ===")
        try:
            text = run_playwright(lang_name)
            hadiths = parse_hadiths_from_text(text, lang_name)

            if hadiths:
                save_language(lang_code, hadiths)
            else:
                print(f"  No hadiths found for {lang_name}")

        except Exception as e:
            print(f"  Error: {e}")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
