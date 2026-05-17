#!/usr/bin/env python3
import csv
import io
import os
import re

SECTIONS_DIR = "editions/silsila-sahih/sections"

def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.match(r'^(hadiths\[[^\]]*\]\{[^}]*\}:\s*)(.*)', content, re.DOTALL)
    if not m:
        print(f"  SKIP: cannot parse header in {filepath}")
        return 0

    header_prefix = m.group(1)
    data = m.group(2).strip()

    reader = csv.reader(io.StringIO(data))
    fields = next(reader)
    fields = [f.strip() for f in fields]

    # Find boundary fields that match "N M" (two ints space-separated).
    # These were created by merging the last field of one record with
    # the first field of the next.
    boundaries = []
    for idx, f in enumerate(fields):
        m2 = re.match(r'^(\d+)\s+(\d+)$', f)
        if m2:
            boundaries.append((idx, m2.group(1), m2.group(2)))

    records = []

    if not boundaries:
        # Single record — no corruption
        records.append(fields)
    else:
        # Record 1: from start to first boundary (inclusive), N replaces "N M"
        first = boundaries[0]
        rec = []
        for idx in range(0, first[0] + 1):
            if idx == first[0]:
                rec.append(first[1])
            else:
                rec.append(fields[idx])
        records.append(rec)

        # Records 2+ : each has a hadith-number prefix (the M from previous boundary),
        # then fields from after the previous boundary to the next boundary,
        # with boundary fields replaced by their first number only.
        for k in range(len(boundaries)):
            hadith = boundaries[k][2]
            start_idx = boundaries[k][0] + 1

            if k + 1 < len(boundaries):
                end_idx = boundaries[k + 1][0]
            else:
                end_idx = len(fields) - 1

            rec = [hadith]
            for idx in range(start_idx, end_idx + 1):
                if idx == end_idx and k + 1 < len(boundaries):
                    rec.append(boundaries[k + 1][1])
                else:
                    rec.append(fields[idx])
            records.append(rec)

    # Filter: keep only records with a valid hadith number and non-empty Arabic
    valid = []
    for rec in records:
        if len(rec) < 2:
            continue
        try:
            int(rec[0].split()[0])
        except (ValueError, IndexError):
            continue
        arabic = rec[1].strip()
        if not arabic:
            continue
        valid.append(rec)

    # Write output: header with correct count, one hadith per line
    out = io.StringIO()
    w = csv.writer(out)
    # The schema: hadithnumber,arabic,grades,reference,international_number
    # (narrator_chain and chapter_intro omitted when empty)
    lines = []
    for rec in valid:
        line_out = io.StringIO()
        cw = csv.writer(line_out)
        cw.writerow(rec)
        lines.append(line_out.getvalue().strip())

    new_header = f"hadiths[{len(valid)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}: "
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_header + "\n")
        for line in lines:
            f.write(line + "\n")

    return len(valid)


def main():
    total = 0

    section_files = sorted(
        [f for f in os.listdir(SECTIONS_DIR) if f.endswith(".toon")],
        key=lambda x: int(x.split(".")[0]),
    )

    for sf in section_files:
        fp = os.path.join(SECTIONS_DIR, sf)
        n = fix_file(fp)
        print(f"{sf}: {n} hadiths")
        total += n

    print(f"\nTotal hadiths across all sections: {total}")


if __name__ == "__main__":
    main()
