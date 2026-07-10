import os
import time
from deep_translator import GoogleTranslator

# read the english intro
with open("intro_en.txt", "r", encoding="utf-8") as f:
    text = f.read().strip()

# Split text into chunks (paragraphs) to avoid api limits
paragraphs = text.split('\n')

langs = ['ar', 'bn', 'fr', 'hi', 'id', 'ro', 'ru', 'tr', 'ur']
intros = {'en': text}

print("Translating intro...")

for lang in langs:
    print(f"Translating to {lang}...")
    translator = GoogleTranslator(source='en', target=lang)
    translated_paras = []
    for p in paragraphs:
        if not p.strip():
            translated_paras.append("")
            continue
        try:
            res = translator.translate(p)
            translated_paras.append(res)
        except Exception as e:
            print(f"Error on {lang}: {e}")
            time.sleep(1)
            try:
                res = translator.translate(p)
                translated_paras.append(res)
            except:
                translated_paras.append(p)
        time.sleep(0.2)
    intros[lang] = '\n'.join(translated_paras)
    time.sleep(1)

print("Translations complete.")

# Now update info.toon
info_path = "/home/saboor/code/hadith-api-toon/editions/abudawud/info.toon"
with open(info_path, "r", encoding="utf-8") as f:
    info_content = f.read()

# Build the metadata block
# Format each intro string
formatted_intros = []
for lang, intro_text in intros.items():
    safe_text = intro_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    key = "intro" if lang == "en" else f"intro_{lang}"
    formatted_intros.append(f"  {key}: \"{safe_text}\"")

metadata_block = (
    "metadata:\n"
    "  book_id: abudawud\n"
    "  book_name: \"Sunan Abi Dawud\"\n"
    "  total_hadiths: 5274\n"
    "  available_languages: \"ar,bn,en,fr,hi,id,ro,ru,tr,ur\"\n"
) + "\n".join(formatted_intros) + "\n\n"

# Check if metadata already exists
if "metadata:" in info_content:
    print("info.toon already has metadata:, not updating automatically. Please check.")
else:
    new_content = metadata_block + info_content
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Updated info.toon with metadata block and intros.")

