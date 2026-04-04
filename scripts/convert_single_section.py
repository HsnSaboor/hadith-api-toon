"""
Convert a single section JSON to toon, then compress with gzip/brotli to measure sizes.
"""

import json
import os
import gzip
import sys

SANDBOX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sandbox"
)


def escape_val(value):
    if value is None:
        return "null"
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def convert_section_to_toon(json_path, output_dir):
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

    # Check if arabicnumber differs from hadithnumber
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

    os.makedirs(output_dir, exist_ok=True)
    toon_path = os.path.join(output_dir, "section.toon")
    content = "\n".join(lines) + "\n"

    with open(toon_path, "w", encoding="utf-8") as f:
        f.write(content)

    content_bytes = content.encode("utf-8")

    # gzip
    gz_path = toon_path + ".gz"
    with open(gz_path, "wb") as f:
        f.write(gzip.compress(content_bytes, compresslevel=9))
    gz_size = os.path.getsize(gz_path)

    # brotli
    try:
        import brotli

        br_path = toon_path + ".br"
        with open(br_path, "wb") as f:
            f.write(brotli.compress(content_bytes, quality=11))
        br_size = os.path.getsize(br_path)
        br_available = True
    except ImportError:
        br_size = None
        br_available = False

    json_size = os.path.getsize(json_path)
    toon_size = os.path.getsize(toon_path)

    print(f"Source JSON:        {json_size:>10,} bytes  ({json_size / 1024:>8.1f} KB)")
    print(f"Toon (raw):         {toon_size:>10,} bytes  ({toon_size / 1024:>8.1f} KB)")
    print(f"Toon (gzip):        {gz_size:>10,} bytes  ({gz_size / 1024:>8.1f} KB)")
    if br_available:
        print(f"Toon (brotli):      {br_size:>10,} bytes  ({br_size / 1024:>8.1f} KB)")
    else:
        print("Toon (brotli):      brotli not installed (pip install brotli)")
    print(f"Reduction JSON→Toon: {(1 - toon_size / json_size) * 100:.1f}%")
    print(f"Reduction JSON→Gzip: {(1 - gz_size / json_size) * 100:.1f}%")
    if br_available:
        print(f"Reduction JSON→Brotli: {(1 - br_size / json_size) * 100:.1f}%")

    return toon_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_single_section.py <path_to_section.json>")
        sys.exit(1)
    json_path = sys.argv[1]
    output_dir = SANDBOX
    convert_section_to_toon(json_path, output_dir)
