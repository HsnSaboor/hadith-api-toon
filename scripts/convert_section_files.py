"""
Convert all edition section JSON files to .toon format.

Reads editions.toon for the edition registry, then processes each edition's
sections/{n}.json files into sections/{n}.toon files.

No chunking — 1 section = 1 file always.
"""

import json
import os
import sys


def escape_val(value):
    """Escape a value for toon CSV format."""
    if value is None:
        return "null"
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def convert_section_json(json_path: str, toon_path: str) -> int:
    """Convert a single section JSON file to toon. Returns hadith count."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    sec_key = list(meta["section"].keys())[0]
    sec_name = meta["section"][sec_key]
    detail = meta.get("section_detail", {}).get(sec_key, {})
    hadiths = data["hadiths"]

    lines = []
    lines.append("metadata:")
    lines.append(f"  section_id: {sec_key}")
    lines.append(f"  section_name: {escape_val(sec_name)}")
    lines.append(f"  hadith_first: {detail.get('hadithnumber_first', '')}")
    lines.append(f"  hadith_last: {detail.get('hadithnumber_last', '')}")
    if detail.get("arabicnumber_first"):
        lines.append(f"  arabic_first: {detail['arabicnumber_first']}")
    if detail.get("arabicnumber_last"):
        lines.append(f"  arabic_last: {detail['arabicnumber_last']}")
    lines.append("")

    # Determine if arabicnumber differs from hadithnumber
    has_arabic = False
    for h in hadiths:
        an = h.get("arabicnumber")
        if an is not None and an != h["hadithnumber"]:
            has_arabic = True
            break

    if has_arabic:
        lines.append(
            f"hadiths[{len(hadiths)}]{{hadithnumber,arabicnumber,text,reference_book,reference_hadith}}:"
        )
        for h in hadiths:
            hn = h["hadithnumber"]
            an = h.get("arabicnumber", hn)
            text = escape_val(h["text"])
            rb = h["reference"]["book"]
            rh = h["reference"]["hadith"]
            lines.append(f"{hn},{an},{text},{rb},{rh}")
    else:
        lines.append(
            f"hadiths[{len(hadiths)}]{{hadithnumber,text,reference_book,reference_hadith}}:"
        )
        for h in hadiths:
            hn = h["hadithnumber"]
            text = escape_val(h["text"])
            rb = h["reference"]["book"]
            rh = h["reference"]["hadith"]
            lines.append(f"{hn},{text},{rb},{rh}")

    os.makedirs(os.path.dirname(toon_path), exist_ok=True)
    with open(toon_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return len(hadiths)


def convert_all_sections(base_dir: str, editions_path: str, output_dir: str):
    """Process all editions' section files."""
    # Parse editions registry
    editions = []
    with open(editions_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("editions[") and line.endswith(":"):
                continue
            parts = line.split(",", 7)
            if len(parts) >= 8:
                editions.append(
                    {
                        "id": parts[0],
                        "path": parts[7],
                    }
                )

    total_files = 0
    total_hadiths = 0
    errors = []

    for edition in editions:
        edition_id = edition["id"]
        src_dir = os.path.join(base_dir, "editions", edition_id, "sections")
        dst_dir = os.path.join(output_dir, edition_id, "sections")

        if not os.path.isdir(src_dir):
            errors.append(f"  {edition_id}: sections/ directory not found")
            continue

        edition_files = 0
        edition_hadiths = 0

        json_files = [
            f
            for f in os.listdir(src_dir)
            if f.endswith(".json") and not f.endswith(".min.json")
        ]
        for fname in sorted(json_files, key=lambda x: int(x.replace(".json", ""))):
            json_path = os.path.join(src_dir, fname)
            toon_name = fname.replace(".json", ".toon")
            toon_path = os.path.join(dst_dir, toon_name)

            try:
                count = convert_section_json(json_path, toon_path)
                edition_files += 1
                edition_hadiths += count
            except Exception as e:
                errors.append(f"  {edition_id}/{fname}: {e}")

        total_files += edition_files
        total_hadiths += edition_hadiths
        print(f"  {edition_id}: {edition_files} sections, {edition_hadiths} hadiths")

    print(f"\nTotal: {total_files} section files, {total_hadiths} hadiths")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hadith_api_dir = os.path.join(base, "hadith-api-1")
    editions_toon = os.path.join(base, "editions.toon")
    output_dir = os.path.join(base, "editions")

    if len(sys.argv) > 1:
        hadith_api_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    print(f"Source: {hadith_api_dir}")
    print(f"Output: {output_dir}")
    print()

    convert_all_sections(hadith_api_dir, editions_toon, output_dir)
