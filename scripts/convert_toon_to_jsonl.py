"""
Convert .toon files from broken CSV-like format to JSON Lines format.

Old format (broken by multiline/misquoted text in CSV):
  hadiths[N]{field1,field2,...}:
  1,"arabic with
  newlines",,"english",,,,,,,,

New format (JSON Lines - one JSON object per hadith):
  hadiths[N]{field1,field2,...}:
  {"hadithnumber":"1","arabic":"arabic text","english":"english",...}

This solves:
- Multiline Arabic/English text breaking CSV parsing
- Embedded quotes and commas in text fields
- Column count mismatches
"""

import json
import os
import re
import sys


def parse_toon_header(line):
    line = line.strip()
    if not line.endswith(":"):
        return None
    line = line[:-1]
    bracket_open = line.index("[")
    bracket_close = line.index("]")
    brace_open = line.index("{")
    brace_close = line.index("}")
    name = line[:bracket_open]
    count = int(line[bracket_open + 1 : bracket_close])
    fields = line[brace_open + 1 : brace_close].split(",")
    return name, count, fields


def split_csv_row(text):
    fields = []
    current = []
    in_quotes = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            if in_quotes:
                if i + 1 < len(text) and text[i + 1] == '"':
                    current.append('"')
                    i += 2
                    continue
                else:
                    in_quotes = False
            else:
                in_quotes = True
            i += 1
            continue
        if ch == "," and not in_quotes:
            fields.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    fields.append("".join(current))
    return fields


def parse_old_toon(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    metadata_lines = []
    header_info = None
    data_start = 0

    in_metadata = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "metadata:":
            in_metadata = True
            metadata_lines.append(line)
            continue
        if in_metadata and stripped.startswith("  "):
            metadata_lines.append(line)
            continue
        if in_metadata:
            in_metadata = False
        if "[" in stripped and "{" in stripped and stripped.endswith(":"):
            try:
                header_info = parse_toon_header(stripped)
                data_start = i + 1
                break
            except Exception:
                continue

    if header_info is None:
        return None

    name, expected_count, fields = header_info

    hadith_start_re = re.compile(r'^\d+[,"]')
    hadith_records = []
    current_lines = []

    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if hadith_start_re.match(stripped) and current_lines:
            hadith_records.append(" ".join(current_lines))
            current_lines = []
        current_lines.append(stripped)

    if current_lines:
        hadith_records.append(" ".join(current_lines))

    hadiths = []
    for rec in hadith_records:
        parts = split_csv_row(rec)
        hadith = {}
        for j, field in enumerate(fields):
            if j < len(parts):
                val = parts[j]
            else:
                val = ""
            hadith[field] = val
        hadiths.append(hadith)

    return {
        "metadata_lines": metadata_lines,
        "fields": fields,
        "expected_count": expected_count,
        "hadiths": hadiths,
    }


def write_new_toon(filepath, parsed):
    metadata_lines = parsed["metadata_lines"]
    fields = parsed["fields"]
    hadiths = parsed["hadiths"]

    with open(filepath, "w", encoding="utf-8") as f:
        for line in metadata_lines:
            f.write(line + "\n")
        f.write("\n")
        f.write(f"hadiths[{len(hadiths)}]{{{','.join(fields)}}}:\n")
        for hadith in hadiths:
            ordered = {field: hadith.get(field, "") for field in fields}
            f.write(json.dumps(ordered, ensure_ascii=False) + "\n")


def convert_file(filepath):
    try:
        parsed = parse_old_toon(filepath)
        if parsed is None:
            return False, "Could not parse header"
        write_new_toon(filepath, parsed)
        actual = len(parsed["hadiths"])
        expected = parsed["expected_count"]
        if actual != expected:
            return True, f"Converted (header={expected}, actual={actual})"
        return True, f"OK ({actual})"
    except Exception as e:
        return False, str(e)


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    editions_dir = os.path.join(base, "editions")

    if not os.path.isdir(editions_dir):
        print(f"ERROR: {editions_dir} not found")
        sys.exit(1)

    total = 0
    success = 0
    count_mismatches = 0
    failures = []

    for book in sorted(os.listdir(editions_dir)):
        sec_dir = os.path.join(editions_dir, book, "sections")
        if not os.path.isdir(sec_dir):
            continue
        for fname in sorted(os.listdir(sec_dir)):
            if not fname.endswith(".toon"):
                continue
            total += 1
            fpath = os.path.join(sec_dir, fname)
            ok, msg = convert_file(fpath)
            if ok:
                success += 1
                if "header=" in msg:
                    count_mismatches += 1
            else:
                failures.append((f"{book}/{fname}", msg))
                print(f"  FAIL {book}/{fname}: {msg}")

    print(f"\n{'=' * 60}")
    print(f"Conversion: {success}/{total} succeeded, {len(failures)} failed")
    print(f"Count mismatches (header != actual): {count_mismatches}")
    if failures:
        print("Failures:")
        for f, m in failures:
            print(f"  {f}: {m}")


if __name__ == "__main__":
    main()
