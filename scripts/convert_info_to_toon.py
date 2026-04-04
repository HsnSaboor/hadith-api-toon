"""
Convert info.json to info.toon and grades.toon

Reads the master info.json containing book metadata, sections, and hadith skeletons.
Outputs:
  - info.toon: Global index with books and per-book sections
  - grades.toon: Hadith grading reference data
"""

import json
import os
import sys


def escape_toon_value(value):
    """Escape a value for toon CSV format."""
    if value is None:
        return "null"
    s = str(value)
    needs_quoting = any(c in s for c in [",", '"', ":", "\n", "\r"])
    if needs_quoting:
        s = s.replace('"', '""').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{s}"'
    return s


def convert_info_to_toon(info_path: str, output_dir: str):
    with open(info_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    # --- info.toon ---
    lines = []

    # Books section
    books = []
    for book_key, book_data in data.items():
        meta = book_data["metadata"]
        books.append((book_key, meta["name"], meta["last_hadithnumber"]))

    lines.append(f"books[{len(books)}]{{id,name,total_hadiths}}:")
    for book_key, name, total in books:
        lines.append(f"{book_key},{escape_toon_value(name)},{total}")
    lines.append("")

    # Per-book sections
    for book_key, book_data in data.items():
        meta = book_data["metadata"]
        sections = meta["sections"]
        section_details = meta["section_details"]

        section_rows = []
        for sec_id_str in sorted(sections.keys(), key=lambda x: int(x)):
            sec_id = int(sec_id_str)
            sec_name = sections[sec_id_str]
            detail = section_details.get(sec_id_str, {})
            hf = detail.get("hadithnumber_first", 0)
            hl = detail.get("hadithnumber_last", 0)
            af = detail.get("arabicnumber_first", 0)
            al_ = detail.get("arabicnumber_last", 0)
            section_rows.append((sec_id, sec_name, hf, hl, af, al_))

        lines.append(
            f"sections_{book_key}[{len(section_rows)}]{{id,name,hadith_first,hadith_last,arabic_first,arabic_last}}:"
        )
        for sec_id, name, hf, hl, af, al_ in section_rows:
            lines.append(f"{sec_id},{escape_toon_value(name)},{hf},{hl},{af},{al_}")
        lines.append("")

    info_toon_path = os.path.join(output_dir, "info.toon")
    with open(info_toon_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Written: {info_toon_path}")

    # --- grades.toon ---
    grade_lines = []
    for book_key, book_data in data.items():
        for hadith in book_data["hadiths"]:
            hn = hadith["hadithnumber"]
            for grade_entry in hadith.get("grades", []):
                grader = grade_entry["name"]
                grade = grade_entry["grade"]
                grade_lines.append(
                    f"{book_key},{hn},{escape_toon_value(grader)},{escape_toon_value(grade)}"
                )

    grades_toon_path = os.path.join(output_dir, "grades.toon")
    with open(grades_toon_path, "w", encoding="utf-8") as f:
        f.write(f"grades[{len(grade_lines)}]{{book,hadithnumber,grader,grade}}:\n")
        f.write("\n".join(grade_lines))
        f.write("\n")

    print(f"Written: {grades_toon_path} ({len(grade_lines)} grade entries)")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    info_path = os.path.join(base_dir, "hadith-api-1", "info.json")
    output_dir = base_dir

    if len(sys.argv) > 1:
        info_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    convert_info_to_toon(info_path, output_dir)
