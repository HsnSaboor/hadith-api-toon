import os
import csv
import re
import io

REPO_ROOT = '/home/saboor/code/hadith-api-toon'
TSV_PATH = f'{REPO_ROOT}/scratch/darimi.tsv'
AR_SECTIONS_DIR = f'{REPO_ROOT}/editions/sunan-darmi/sections'
EN_TRANS_DIR = f'{REPO_ROOT}/editions/sunan-darmi/translations/en/sections'

def load_tsv():
    data = {}
    with open(TSV_PATH, 'r', encoding='utf-8') as f:
        # The TSV has many columns. We need 'num' (55) and 'body_en' (62)
        # Column indices are 0-based, so 54 and 61
        reader = csv.reader(f, delimiter='\t')
        headers = next(reader)
        for row in reader:
            if len(row) < 62: continue
            num = row[54].strip()
            text = row[61].strip()
            # Clean machine prefix
            text = text.replace('[Machine] ', '')
            if num:
                data[num] = text
    return data

def process_section(fname, en_data):
    src_path = os.path.join(AR_SECTIONS_DIR, fname)
    dest_path = os.path.join(EN_TRANS_DIR, fname)
    
    with open(src_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Extract metadata if possible or useful
    h_numbers = []
    in_data = False
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('hadiths['):
            in_data = True
            continue
        if in_data:
            # First column is hadithnumber
            parts = line.split(',', 1)
            h_numbers.append(parts[0].strip())
    
    if not h_numbers: return
    
    sec_id = fname.replace('.toon', '')
    h_first = h_numbers[0]
    h_last = h_numbers[-1]
    count = len(h_numbers)
    
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write('metadata:\n')
        f.write(f'  section_id: {sec_id}\n')
        f.write(f'  hadith_first: {h_first}\n')
        f.write(f'  hadith_last: {h_last}\n\n')
        f.write(f'hadiths[{count}]{{hadithnumber,text,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
        
        for hn in h_numbers:
            text = en_data.get(hn, '')
            # Standard columns: hadithnumber,text,grades,reference,international_number,narrator_chain,chapter_intro
            row = [hn, text, '', '', '', '', '']
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='')
            writer.writerow(row)
            f.write(output.getvalue() + '\n')

def main():
    print("Loading TSV...")
    en_data = load_tsv()
    print(f"Loaded {len(en_data)} translations.")
    
    os.makedirs(EN_TRANS_DIR, exist_ok=True)
    
    files = sorted([f for f in os.listdir(AR_SECTIONS_DIR) if f.endswith('.toon')], 
                   key=lambda x: int(x.split('.')[0]))
    
    for f in files:
        # Special case: 0.toon seems to have weird numbering in Darimi
        # We'll see if it maps
        print(f"Processing {f}...")
        process_section(f, en_data)
    
    print("Done.")

if __name__ == "__main__":
    main()
