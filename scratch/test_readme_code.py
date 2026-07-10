import csv, io, requests, re

def fetch_section(book, section_id):
    url = f"https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/{book}/sections/{section_id}.toon"
    text = requests.get(url).text
    
    # 1. Parse header block structure: hadiths[count]{fields}:
    header_match = re.search(r'^([A-Za-z_]+)\[(?:count|\d+)\]\{(.*?)\}\s*:', text, re.DOTALL)
    if not header_match:
        raise ValueError("Invalid .toon format header")
        
    cols = [f.strip() for f in header_match.group(2).split(',')]
    rest_data = text[header_match.end():]
    
    # 2. Parse data rows statefully using csv.reader
    reader = csv.reader(io.StringIO(rest_data))
    hadiths = []
    for row in reader:
        if not row:
            continue
        # Align rows with schema fields
        if len(row) < len(cols):
            row += [''] * (len(cols) - len(row))
        hadiths.append(dict(zip(cols, row)))
        
    return cols, hadiths

# Test Usage
cols, hadiths = fetch_section('bukhari', '1')
print("Successfully loaded Bukhari section 1 hadiths:", len(hadiths))
print("First hadith Arabic:", hadiths[0]['arabic'][:80])
