#!/usr/bin/env python3
"""Scrape takhreej/conclusion data for lulu-wal-marjan from al-hadees.com.

Reads existing section files, scrapes grades/reference data,
and writes updated section files.
"""
import json, os, re, sys, time
from urllib.request import urlopen, Request
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

BASE = os.path.dirname(os.path.dirname(__file__))
EDITION_DIR = os.path.join(BASE, "editions", "lulu-wal-marjan")
SECTIONS_DIR = os.path.join(EDITION_DIR, "sections")
CACHE_FILE = os.path.join(BASE, "scraped_data", "lulu_takhreej_cache.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
}

# Load existing cache
cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r') as f:
        cache = json.load(f)
    print(f"Loaded {len(cache)} cached entries")

lock = Lock()

def fetch_takhreej(hadith_num):
    if str(hadith_num) in cache:
        return str(hadith_num), cache[str(hadith_num)]
    
    url = f"https://al-hadees.com/lulu-wal-marjan/{hadith_num}"
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        # Extract takhreej (أخرجه ...)
        takhreej_match = re.search(r'أخرجه[^<]*', html)
        takhreej = takhreej_match.group(0).strip() if takhreej_match else ""
        
        # Extract status (Sahih)
        status = "Sahih"  # All are Sahih in this book
        
        # Extract international number
        intl_match = re.search(r'International:\s*(\d+)', html)
        international = intl_match.group(1) if intl_match else str(hadith_num)
        
        result = {
            'grades': f"Default: {status}",
            'reference': takhreej,
            'international': international
        }
        
        with lock:
            cache[str(hadith_num)] = result
            # Save cache periodically
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, ensure_ascii=False)
        
        return str(hadith_num), result
    except Exception as e:
        print(f"  Error fetching {hadith_num}: {e}")
        return str(hadith_num), None

def update_section_file(ch_id, hadiths_with_data):
    """Rewrite a section TOON file with updated grades/reference/intl."""
    filename = os.path.join(SECTIONS_DIR, f"{ch_id}.toon")
    
    # First re-read the existing hadith lines to preserve arabic text
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    header, rest = content.split('\n', 1)
    lines = [l for l in rest.split('\n') if l.strip()]
    
    new_lines = []
    for line in lines:
        # Extract hadith number from line
        parts = line.split(',', 1)
        if not parts[0].strip().isdigit():
            new_lines.append(line)
            continue
        hnum = parts[0].strip()
        rest_of_line = parts[1] if len(parts) > 1 else ""
        
        if hnum in hadiths_with_data:
            data = hadiths_with_data[hnum]
            grades = data.get('grades', '')
            reference = data.get('reference', '')
            international = data.get('international', '')
            
            # Reconstruct line: number,arabic,grades,reference,international,narrator,chapter_intro
            # The existing line is: number,arabic,,,,,
            # We need to replace commas after arabic with our data
            arabic_end = rest_of_line
            # Find the arabic text - it's between the first comma and the 5 commas
            # Format: arabic,,,,,
            # We want: number,arabic,grades,reference,international,narrator,chapter_intro
            
            # Count commas to separate fields
            # Original has: number,arabic,,,,,
            # So we need to find the first 5 commas after arabic
            
            # Parse original fields carefully
            # Split by comma but handle quoted arabic
            fields = rest_of_line.rsplit(',', 5)  # split into arabic + 5 empty fields
            arabic = fields[0] if len(fields) > 0 else ""
            # The arabic might be quoted
            
            new_line = f"{hnum},{arabic},{grades},{reference},{international},,"
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(header + '\n')
        for l in new_lines:
            f.write(l + '\n')

def main():
    global cache
    
    print("Step 1: Collect all hadith numbers from section files")
    all_hadiths = []
    for fname in sorted(os.listdir(SECTIONS_DIR), key=lambda x: int(x.split('.')[0])):
        fpath = os.path.join(SECTIONS_DIR, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('hadiths['):
                    hnum = line.split(',')[0].strip()
                    if hnum.isdigit():
                        all_hadiths.append(int(hnum))
    
    print(f"Total hadiths to scrape: {len(all_hadiths)} ({len(cache)} cached)")
    
    # Fetch only uncached
    to_fetch = [h for h in all_hadiths if str(h) not in cache]
    print(f"Need to fetch: {len(to_fetch)} hadiths")
    
    if to_fetch:
        # Use ThreadPoolExecutor for parallel fetching
        batch_size = 10  # Fetch 10 at a time to be polite
        for i in range(0, len(to_fetch), batch_size):
            batch = to_fetch[i:i+batch_size]
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fetch_takhreej, h): h for h in batch}
                for future in as_completed(futures):
                    hnum, result = future.result()
                    if result:
                        pass  # Already cached in fetch_takhreej
            # Progress update
            pct = min(100, (i + batch_size) / len(to_fetch) * 100)
            print(f"  Progress: {min(i+batch_size, len(to_fetch))}/{len(to_fetch)} ({pct:.0f}%)")
            time.sleep(0.5)  # Small delay between batches
    
    # Reload cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
    
    print(f"\nStep 2: Update section files with scraped data")
    
    # Group hadiths by chapter
    ch_hadiths = {}
    for fname in sorted(os.listdir(SECTIONS_DIR), key=lambda x: int(x.split('.')[0])):
        ch_id = int(fname.split('.')[0])
        ch_hadiths[ch_id] = []
        fpath = os.path.join(SECTIONS_DIR, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('hadiths['):
                    hnum = line.split(',')[0].strip()
                    if hnum.isdigit():
                        ch_hadiths[ch_id].append(hnum)
    
    # Update each section
    for ch_id in sorted(ch_hadiths.keys()):
        hadiths_in_ch = ch_hadiths[ch_id]
        data_for_ch = {}
        for hnum in hadiths_in_ch:
            if hnum in cache:
                data_for_ch[hnum] = cache[hnum]
        
        if data_for_ch:
            update_section_file(ch_id, data_for_ch)
        
        matched = len(data_for_ch)
        total = len(hadiths_in_ch)
        star = " ✓" if matched == total else f" ({matched}/{total})"
        print(f"  Chapter {ch_id}: {total} hadiths updated{star}")
    
    # Save final cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f"\nDone! Cache saved to {CACHE_FILE}")
    print(f"Total cached: {len(cache)}")

if __name__ == '__main__':
    main()
