# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///

"""
Test ALL Python code snippets from README.md and USAGE.md against the live CDN.
"""

import csv
import io
import re
import urllib.request

print("=" * 60)
print("TEST 1: README.md — Python Example: fetch_section (requests)")
print("=" * 60)

import requests

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

# Usage
cols, hadiths = fetch_section('bukhari', '1')
print(f"✅ Loaded {len(hadiths)} hadiths from bukhari/sections/1")
print(f"   Columns: {cols}")
print(f"   hadiths[0]['arabic'][:80]: {hadiths[0]['arabic'][:80]}")
print()

print("=" * 60)
print("TEST 2: USAGE.md — Python Example: parse_toon_url (urllib)")
print("=" * 60)

def parse_toon_url(url):
    # Fetch content with custom User-Agent to avoid blocks
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

# Example Usage:
block_name, hadiths2 = parse_toon_url("https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/sections/1.toon")
print(f"✅ Loaded {len(hadiths2)} hadiths from block '{block_name}'")
print(f"   First Hadith arabic[:80]: {hadiths2[0]['arabic'][:80]}")
print()

# Also test a translation file
print("=" * 60)
print("TEST 3: Translation file parsing (nawawi urdu)")
print("=" * 60)
block_name3, hadiths3 = parse_toon_url("https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/nawawi/translations/ur/sections/1.toon")
print(f"✅ Loaded {len(hadiths3)} records from nawawi/ur block '{block_name3}'")
print(f"   Fields: {list(hadiths3[0].keys())}")
print(f"   First text[:80]: {hadiths3[0].get('text', 'N/A')[:80]}")
print()

# Test info.toon root index
print("=" * 60)
print("TEST 4: Root info.toon parsing")
print("=" * 60)
req = urllib.request.Request(
    "https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon",
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req) as resp:
    info_text = resp.read().decode('utf-8')

info_lines = [l for l in info_text.split('\n') if l.strip()]
header_line = info_lines[0]
info_cols = header_line[header_line.index('{')+1:header_line.index('}')].split(',')
info_cols = [c.strip() for c in info_cols]

reader = csv.reader(io.StringIO('\n'.join(info_lines[1:])))
all_books = []
for row in reader:
    if not row:
        continue
    if len(row) < len(info_cols):
        row += [''] * (len(info_cols) - len(row))
    all_books.append(dict(zip(info_cols, row)))

print(f"✅ Loaded {len(all_books)} books from root info.toon")
print(f"   First book: {all_books[0]}")
print()

print("🎉 ALL PYTHON TESTS PASSED!")
