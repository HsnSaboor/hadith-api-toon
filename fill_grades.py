import os
import re
import sys

EDITIONS = "/home/saboor/code/hadith-api-toon/editions"

PROGRAMMATIC_SAHIH = {
    "muslim": "Default: Sahih",
    "dehlawi": "Sahih",
}

NAWAWI_GRADES = {
    1: "Sahih", 2: "Sahih", 3: "Sahih", 4: "Sahih", 5: "Sahih",
    6: "Sahih", 7: "Sahih", 8: "Sahih", 9: "Sahih", 10: "Sahih",
    11: "Tirmidhi: Hasan Sahih", 12: "Tirmidhi: Hasan", 13: "Sahih", 14: "Sahih",
    15: "Sahih", 16: "Sahih", 17: "Sahih", 18: "Tirmidhi: Hasan",
    19: "Tirmidhi: Hasan Sahih", 20: "Sahih", 21: "Sahih", 22: "Sahih",
    23: "Sahih", 24: "Sahih", 25: "Sahih", 26: "Sahih", 27: "Hasan",
    28: "Hasan Sahih", 29: "Tirmidhi: Hasan Sahih", 30: "Hasan",
    31: "Hasan", 32: "Hasan", 33: "Hasan", 34: "Sahih", 35: "Sahih",
    36: "Sahih", 37: "Sahih", 38: "Sahih", 39: "Hasan", 40: "Sahih",
    41: "Hasan Sahih", 42: "Tirmidhi: Hasan Sahih",
}

def parse_toon_fields(line):
    """Parse a toon record line, correctly handling embedded quotes in Arabic text.
    Uses the approach: split on '","' to get fields, since that delimiter
    cannot appear within Arabic text normally."""
    line = line.strip()
    if line.startswith('hadiths['):
        return None
    if not line:
        return None
    # Remove leading and trailing quotes
    if line.startswith('"'):
        line = line[1:]
    if line.endswith('"'):
        line = line[:-1]
    # Now split on '","' — but limit splits
    fields = line.split('","')
    return fields

def make_toon_line(fields):
    """Join fields back into a toon record line."""
    return '"' + '","'.join(fields) + '"'

def read_section(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write_section(path, header, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for line in lines:
            f.write(line.strip() + "\n")

def process_books(updater_func, description=""):
    for book in sorted(os.listdir(EDITIONS)):
        bdir = os.path.join(EDITIONS, book)
        if not os.path.isdir(bdir):
            continue
        sdir = os.path.join(bdir, "sections")
        if not os.path.isdir(sdir):
            continue
        total = 0
        changed = 0
        for fn in sorted(os.listdir(sdir), key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else 0):
            if not fn.endswith(".toon"):
                continue
            fpath = os.path.join(sdir, fn)
            content = read_section(fpath)
            lines = content.strip().split("\n")
            if not lines:
                continue
            header = lines[0]
            out_lines = []
            for raw_line in lines[1:]:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                fields = parse_toon_fields(raw_line)
                if fields is None:
                    out_lines.append(raw_line)
                    continue
                total += 1
                if updater_func(book, fn, fields):
                    changed += 1
                out_lines.append(make_toon_line(fields))
            write_section(fpath, header, out_lines)
        if total > 0:
            print(f"  {book}: {changed}/{total} updated" + (f" ({description})" if description else ""))

def fill_sahih():
    def updater(book, fn, fields):
        grade = PROGRAMMATIC_SAHIH.get(book)
        if grade is None:
            return False
        if len(fields) >= 3 and not fields[2].strip():
            fields[2] = grade
            return True
        return False

    print("1. Programmatic Sahih fills (muslim, dehlawi)...")
    process_books(updater, "Sahih")

def fill_nawawi():
    def updater(book, fn, fields):
        if book != "nawawi":
            return False
        if len(fields) >= 3:
            try:
                hnum = int(fields[0])
                grade = NAWAWI_GRADES.get(hnum)
                if grade and not fields[2].strip():
                    fields[2] = grade
                    return True
            except ValueError:
                pass
        return False

    print("2. Nawawi grades...")
    process_books(updater)

def fill_qudsi():
    def updater(book, fn, fields):
        if book != "qudsi":
            return False
        if len(fields) >= 3 and not fields[2].strip():
            fields[2] = "Sahih"
            return True
        return False

    print("3. Qudsi grades...")
    process_books(updater)

def fill_international():
    def updater(book, fn, fields):
        if len(fields) >= 5 and not fields[4].strip() and fields[0].strip():
            fields[4] = fields[0]
            return True
        return False

    print("4. International number fill...")
    process_books(updater)

if __name__ == "__main__":
    fill_sahih()
    fill_nawawi()
    fill_qudsi()
    fill_international()
    print("\nDone")
