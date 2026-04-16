from deep_translator import GoogleTranslator
import re


def split_text_into_chunks(text, max_chars=4000):
    if len(text) <= max_chars:
        return [text]
    chunks = []
    current_chunk = ""
    paragraphs = text.split("\n\n")
    for para in paragraphs:
        if len(para) > max_chars:
            lines = para.split("\n")
            for line in lines:
                if len(current_chunk) + len(line) + 1 <= max_chars:
                    current_chunk += line + "\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
        else:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def translate_text(text, target_lang):
    if not text or not text.strip():
        return None
    try:
        translator = GoogleTranslator(source="en", target=target_lang)
        if len(text) <= 4000:
            return translator.translate(text)
        chunks = split_text_into_chunks(text, max_chars=4000)
        translated_chunks = []
        for chunk in chunks:
            if chunk.strip():
                translated = translator.translate(chunk)
                translated_chunks.append(translated)
        return "\n\n".join(translated_chunks)
    except Exception as e:
        print(f"Error: {e}")
        return None


# Books to process
books = ["mustadrak", "nasai", "nawawi", "qudsi", "sahih-ibn-khuzaymah"]

# Languages to translate to
languages = {"es": "Spanish", "tr": "Turkish", "hi": "Hindi"}

results = {}

for book in books:
    print(f"\n{'=' * 60}")
    print(f"Processing: {book}")
    print("=" * 60)

    # Read file
    with open(f"/home/saboor/code/hadith-api-toon/editions/{book}/info.toon", "r") as f:
        content = f.read()

    # Extract English intro
    intro_match = re.search(r'intro: "(.*?)"\n', content, re.DOTALL)
    if not intro_match:
        print(f"  ERROR: Could not find intro for {book}")
        continue

    english_text = intro_match.group(1)
    english_text = english_text.replace("\\n", "\n")

    print(f"  English char count: {len(english_text)}")

    results[book] = {"en": len(english_text)}

    # Translate to each language
    for lang_code, lang_name in languages.items():
        print(f"  Translating to {lang_name}...", end=" ", flush=True)
        translated = translate_text(english_text, lang_code)
        if translated:
            results[book][lang_code] = len(translated)
            print(f"Done ({len(translated)} chars)")

            # Escape newlines for YAML
            escaped = translated.replace("\n", "\\n").replace('"', '\\"')

            # Replace existing intro field
            pattern = rf'intro_{lang_code}: "[^"]*"'
            replacement = f'intro_{lang_code}: "{escaped}"'

            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
            else:
                # Add after intro line
                content = re.sub(
                    rf'(intro: ".*?"\n)',
                    rf'\1  intro_{lang_code}: "{escaped}"\n',
                    content,
                )
        else:
            print("FAILED")

    # Write back
    with open(f"/home/saboor/code/hadith-api-toon/editions/{book}/info.toon", "w") as f:
        f.write(content)
    print(f"  Written to file")

# Print summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for book, counts in results.items():
    print(f"\n{book}:")
    for lang, count in counts.items():
        lang_name = {
            "en": "English",
            "es": "Spanish",
            "tr": "Turkish",
            "hi": "Hindi",
        }.get(lang, lang)
        print(f"  {lang_name}: {count} chars")
