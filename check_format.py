import os, re

# Check section 1 structure for several books to understand format diversity
books_to_check = [
    ('mustadrak', '/home/saboor/code/hadith-api-toon/editions/mustadrak/sections/1.toon'),
    ('sahih-ibn-khuzaymah', '/home/saboor/code/hadith-api-toon/editions/sahih-ibn-khuzaymah/sections/1.toon'),
    ('muajam-tabarani-saghir', '/home/saboor/code/hadith-api-toon/editions/muajam-tabarani-saghir/sections/1.toon'),
    ('silsila-sahih', '/home/saboor/code/hadith-api-toon/editions/silsila-sahih/sections/1.toon'),
    ('fatah-alrabani', '/home/saboor/code/hadith-api-toon/editions/fatah-alrabani/sections/1.toon'),
    ('shamail-tirmazi', '/home/saboor/code/hadith-api-toon/editions/shamail-tirmazi/sections/1.toon'),
    ('bulugh-al-maram', '/home/saboor/code/hadith-api-toon/editions/bulugh-al-maram/sections/1.toon'),
    ('musnad-ahmed', '/home/saboor/code/hadith-api-toon/editions/musnad-ahmed/sections/1.toon'),
    ('aladab-almufrad', '/home/saboor/code/hadith-api-toon/editions/aladab-almufrad/sections/1.toon'),
]

for name, fp in books_to_check:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    header = lines[0]
    
    # Get declared count
    m = re.search(r'hadiths\[(\d+)\]', header)
    decl = int(m.group(1)) if m else 0
    
    data_lines = [l for l in lines[1:] if l.strip()]
    num_data_lines = len(data_lines)
    
    # Count lines where first field is digit AND second field has Arabic text
    arabic_count = 0
    other_count = 0
    line_samples = []
    for i, line in enumerate(lines[1:11]):
        line = line.strip()
        if not line:
            continue
        parts = line.split(',', 1)
        if parts[0].strip().isdigit():
            rest = parts[1].strip() if len(parts) > 1 else ''
            has_arabic = bool(rest.strip().strip('"').strip("'"))
            if has_arabic:
                arabic_count += 1
            else:
                other_count += 1
            if i < 5:
                line_samples.append(f"  line {i+2}: num={parts[0]}, has_content={has_arabic}, preview={rest[:50]}")
    
    # Total across all lines
    total_content = 0
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',', 1)
        if parts[0].strip().isdigit() and len(parts) > 1:
            rest = parts[1].strip().strip('"').strip("'")
            if rest:
                total_content += 1

    print(f"{name}:")
    print(f"  Header: {decl} hadiths")
    print(f"  Data lines: {num_data_lines}")
    print(f"  Lines with content: {total_content}")
    print(f"  First 5 lines:")
    for s in line_samples:
        print(s)
    print()
