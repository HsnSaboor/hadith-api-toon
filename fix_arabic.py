import csv
import io
import os
import re

sections_dir = "editions/sahih-ibn-khuzaymah/sections"
total_hadiths = 0

for i in range(2, 82):
    fpath = os.path.join(sections_dir, f"{i}.toon")
    if not os.path.exists(fpath):
        continue

    with open(fpath, encoding="utf-8") as f:
        content = f.read()

    m = re.search(r"hadiths\[(\d+)\]", content)
    expected = int(m.group(1))

    header_end = content.index("}: ")
    data = content[header_end + 3:]

    reader = csv.reader(io.StringIO(data))
    fields = next(reader)

    # Reconstruct hadith records from the single CSV row.
    # Record 1: 5 fields (number, arabic, grades, takhreej, intl_number)
    # Records 2+: 4 fields each (arabic, grades, takhreej, intl_number)
    records = []
    if len(fields) >= 5:
        records.append(fields[0:5])
        idx = 5
        while idx + 4 <= len(fields):
            records.append(fields[idx:idx + 4])
            idx += 4

    valid = []
    for j, rec in enumerate(records):
        if j == 0:
            number = rec[0]
            arabic = rec[1]
            grades = rec[2]
            takhreej = rec[3]
            intl_num = rec[4]
        else:
            prev_intl = records[j - 1][-1]
            parts = prev_intl.split()
            number = parts[1] if len(parts) >= 2 else ""
            arabic = rec[0]
            grades = rec[1]
            takhreej = rec[2]
            intl_num = rec[3]

        if number.isdigit() and arabic.strip():
            valid.append([number, arabic, grades, takhreej, intl_num, "", ""])

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"hadiths[{len(valid)}]{{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}}:\n")
        writer = csv.writer(f)
        writer.writerows(valid)

    total_hadiths += len(valid)
    print(f"  {i}.toon: {len(valid)} hadiths (expected {expected})")

print(f"\nTotal hadiths: {total_hadiths}")
