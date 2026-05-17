import os, re, csv, io

def analyze_format(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    idx = content.find(':')
    header = content[:idx]
    data = content[idx+1:]
    
    # Parse header
    m = re.search(r'hadiths\[(\d+)\]\{([^}]+)\}', header)
    if m:
        decl = int(m.group(1))
        fields = m.group(2).split(',')
    else:
        return None
    
    # Look for ASCII commas in specific contexts
    ascii_commas = [i for i, c in enumerate(data) if c == ',']
    
    # Check a window around each ASCII comma to see context
    print(f"File: {os.path.basename(filepath)}")
    print(f"  Declared: {decl}, Fields: {len(fields)}")
    print(f"  Data length: {len(data)}")
    print(f"  ASCII commas count: {len(ascii_commas)}")
    
    # Show first few segments separated by ASCII comma
    segments = data.split(',')
    print(f"  Segments on ASCII comma split: {len(segments)}")
    
    # Expected number of segments for N records with F fields: N*F
    expected_segments = decl * len(fields)
    print(f"  Expected segments ({decl}*{len(fields)}): {expected_segments}")
    
    # Check: are segments uniformly sized?
    # Count how many segments start with a digit (potential hadith numbers)
    digit_starts = sum(1 for s in segments[:50] if s.strip().isdigit())
    print(f"  Segments starting with digit (first 50): {digit_starts}")
    
    # Show a few segments
    for i in range(min(10, len(segments))):
        snippet = segments[i].strip()[:60]
        print(f"    Segment[{i}]: {repr(snippet)}")
    
    # Check: if it's a proper record structure, field 0, field 7, field 14, etc. should be numbers
    print("  Checking periodic structure...")
    for offset in [0, 1, 2, 3, 4, 5, 6]:
        values_at = []
        for i in range(offset, min(len(segments), expected_segments), 7):
            v = segments[i].strip()[:40]
            values_at.append(v)
        # Show first 3 values at this offset
        is_all_digits = all(s.strip().isdigit() for s in values_at[:10])
        print(f"    Offset {offset} ({fields[offset] if offset < len(fields) else '?'}): first={values_at[:3]}, all_digits={is_all_digits}")
    
    return segments, fields, decl

# Check sahih section 2
print("=" * 60)
analyze_format('/home/saboor/code/hadith-api-toon/editions/sahih-ibn-khuzaymah/sections/2.toon')

print()
print("=" * 60)
analyze_format('/home/saboor/code/hadith-api-toon/editions/sahih-ibn-khuzaymah/sections/1.toon')
