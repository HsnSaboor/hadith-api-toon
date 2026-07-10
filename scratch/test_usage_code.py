import csv
import io
import urllib.request
import re

def parse_toon_url(url):
    # Fetch content
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        text = response.read().decode('utf-8')
    
    # 1. Parse header block structure: hadiths[count]{fields}:
    header_match = re.search(r'^([A-Za-z_]+)\[(?:count|\d+)\]\{(.*?)\}\s*:', text, re.DOTALL)
    if not header_match:
        raise ValueError("Invalid .toon format header")
        
    block_name = header_match.group(1)
    fields = [f.strip() for f in header_match.group(2).split(',')]
    rest_data = text[header_match.end():]
    
    # 2. Parse data rows statefully using csv.reader
    reader = csv.reader(io.StringIO(rest_data))
    records = []
    for row in reader:
        if not row:
            continue
        # Align rows with schema fields
        if len(row) < len(fields):
            row += [''] * (len(fields) - len(row))
        records.append(dict(zip(fields, row)))
        
    return block_name, records

# Test Usage
block_name, hadiths = parse_toon_url("https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/sections/1.toon")
print(f"Loaded {len(hadiths)} hadiths from block '{block_name}'")
print("First Hadith:", hadiths[0]['arabic'][:80])
