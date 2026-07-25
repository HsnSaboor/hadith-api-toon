#!/usr/bin/env python3
"""Mechanical tool: replace a book's metadata block (book_id, book_name,
total_hadiths, available_languages, intro + intro_<lang> fields) in its
info.toon with hand-authored content from /tmp/<book>_intros.json.

This tool does NOT generate or translate any text. It only:
  1. Reads a JSON file the author has manually written with keys:
     {"book_id", "book_name", "total_hadiths", "available_languages",
      "en": "...", "ar": "...", "ur": "...", "bn": "...", ...}
  2. Properly escapes each string for the .toon quoted-field format
     (backslash, double-quote, and literal newline all escaped).
  3. Replaces the existing metadata: block (from 'metadata:' up to the
     first line that starts a new top-level block, e.g. 'translations['
     or 'sections[') with the freshly rebuilt block.
  4. Leaves everything else in the file (translations index, sections
     index, hadith data) completely untouched.

Usage: python3 apply_intro.py <book_id>
Reads: /tmp/<book_id>_intros.json
Writes: editions/<book_id>/info.toon (in place, with a .bak backup)
"""
import json
import re
import sys
import os

ED = "/home/saboor/code/hadith-api-toon/editions"

LANG_KEY_ORDER = [
    "ar", "en", "bn", "fr", "id", "ru", "tr", "ur",
    "hi", "ta", "roman-ur", "de", "es", "bs", "sw", "te",
]


def escape_toon_string(s: str) -> str:
    """Escape a string for embedding in a double-quoted .toon field.
    Order matters: backslash first, then quote, then real newlines -> \\n."""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "\\n")
    return s


def build_metadata_block(data: dict) -> str:
    lines = ["metadata:"]
    lines.append(f'  book_id: "{escape_toon_string(data["book_id"])}"')
    lines.append(f'  book_name: "{escape_toon_string(data["book_name"])}"')
    lines.append(f'  total_hadiths: "{escape_toon_string(str(data["total_hadiths"]))}"')
    lines.append(f'  available_languages: "{escape_toon_string(data["available_languages"])}"')

    # intro (bare) + intro_en are both English per existing convention
    if "en" not in data:
        raise ValueError("Missing required 'en' key")
    lines.append(f'  intro: "{escape_toon_string(data["en"])}"')

    for lang in LANG_KEY_ORDER:
        if lang not in data:
            continue
        key = "intro_en" if lang == "en" else f"intro_{lang}"
        lines.append(f'  {key}: "{escape_toon_string(data[lang])}"')

    # any extra languages not in our known order (future-proofing)
    for lang, val in data.items():
        if lang in ("book_id", "book_name", "total_hadiths", "available_languages", "en"):
            continue
        if lang in LANG_KEY_ORDER:
            continue
        lines.append(f'  intro_{lang}: "{escape_toon_string(val)}"')

    return "\n".join(lines) + "\n"


def replace_metadata_block(book_id: str, new_block: str):
    info_path = f"{ED}/{book_id}/info.toon"
    with open(info_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    m = re.search(r"(?m)^metadata:\s*$", text)
    if not m:
        raise ValueError(f"No 'metadata:' block found in {info_path}")
    start = m.start()

    # find the end: next top-level block header (translations[ or sections[)
    end_m = re.search(r"(?m)^(translations\[|sections\[)", text[start:])
    if not end_m:
        raise ValueError(f"No trailing translations[/sections[ block found in {info_path}")
    end = start + end_m.start()

    # trim trailing blank lines before end, we'll add exactly one blank line separator
    before = text[:start]
    after = text[end:]

    new_text = before + new_block + "\n" + after

    backup_path = info_path + ".bak"
    if not os.path.exists(backup_path):
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(text)

    with open(info_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"[{book_id}] metadata block replaced ({len(new_block)} chars). Backup: {backup_path}")


def verify_roundtrip(book_id: str, data: dict):
    """Re-read the file and confirm each intro string comes back byte-identical
    (after unescaping) to what we wrote."""
    info_path = f"{ED}/{book_id}/info.toon"
    with open(info_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    def unescape(s):
        # reverse of escape_toon_string ordering
        out = []
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                nxt = s[i + 1]
                if nxt == "n":
                    out.append("\n")
                    i += 2
                    continue
                elif nxt == '"':
                    out.append('"')
                    i += 2
                    continue
                elif nxt == "\\":
                    out.append("\\")
                    i += 2
                    continue
            out.append(s[i])
            i += 1
        return "".join(out)

    m = re.search(r"(?m)^metadata:\s*$", text)
    end_m = re.search(r"(?m)^(translations\[|sections\[)", text[m.start():])
    block = text[m.start(): m.start() + end_m.start()]

    ok = True
    checks = [("en", data["en"])]
    for lang in LANG_KEY_ORDER:
        if lang in data and lang != "en":
            checks.append((lang, data[lang]))

    for lang, expected in checks:
        key = "intro_en" if lang == "en" else f"intro_{lang}"
        fm = re.search(rf'{re.escape(key)}:\s*"((?:[^"\\]|\\.)*)"', block)
        if not fm:
            print(f"  [{book_id}] MISSING key {key} after write!")
            ok = False
            continue
        got = unescape(fm.group(1))
        if got != expected:
            print(f"  [{book_id}] MISMATCH {key}: len(expected)={len(expected)} len(got)={len(got)}")
            # show first diff position
            for i, (a, b) in enumerate(zip(expected, got)):
                if a != b:
                    print(f"    first diff at char {i}: expected {a!r} got {b!r}")
                    break
            ok = False

    if ok:
        print(f"[{book_id}] round-trip verify OK ({len(checks)} language fields)")
    return ok


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 apply_intro.py <book_id>")
        sys.exit(1)
    book_id = sys.argv[1]
    json_path = f"/tmp/{book_id}_intros.json"
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found")
        sys.exit(1)
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    block = build_metadata_block(data)
    replace_metadata_block(book_id, block)
    ok = verify_roundtrip(book_id, data)
    if not ok:
        print(f"[{book_id}] VERIFICATION FAILED - restoring from backup")
        backup_path = f"{ED}/{book_id}/info.toon.bak"
        with open(backup_path, encoding="utf-8") as f:
            original = f.read()
        with open(f"{ED}/{book_id}/info.toon", "w", encoding="utf-8") as f:
            f.write(original)
        sys.exit(1)
    print(f"[{book_id}] DONE")
