"""
Convert editions.json to editions.toon

Reads the edition index JSON and produces a flat toon registry of all editions.
"""

import json
import os
import sys


def escape_toon_value(value):
    if value is None:
        return "null"
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def convert_editions_to_toon(editions_path: str, output_dir: str):
    with open(editions_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    editions = []
    for book_key, book_data in data.items():
        for edition in book_data.get("collection", []):
            editions.append(
                {
                    "id": edition["name"],
                    "book": edition["book"],
                    "author": edition.get("author", ""),
                    "language": edition.get("language", ""),
                    "has_sections": edition.get("has_sections", False),
                    "dir": edition.get("direction", "ltr"),
                    "comments": edition.get("comments", ""),
                    "path": f"editions/{edition['name']}",
                }
            )

    lines = []
    lines.append(
        f"editions[{len(editions)}]{{id,book,author,language,has_sections,dir,comments,path}}:"
    )
    for ed in editions:
        has_sec = str(ed["has_sections"]).lower()
        lines.append(
            f"{ed['id']},{ed['book']},{escape_toon_value(ed['author'])},{escape_toon_value(ed['language'])},{has_sec},{ed['dir']},{escape_toon_value(ed['comments'])},{ed['path']}"
        )

    output_path = os.path.join(output_dir, "editions.toon")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")

    print(f"Written: {output_path} ({len(editions)} editions)")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    editions_path = os.path.join(base_dir, "hadith-api-1", "editions.json")
    output_dir = os.path.join(base_dir, "output")

    if len(sys.argv) > 1:
        editions_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    convert_editions_to_toon(editions_path, output_dir)
