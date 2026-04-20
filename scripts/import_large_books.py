import os
import csv
import io

REPO_ROOT = '/home/saboor/code/hadith-api-toon'

def import_book(book_id, tsv_filename):
    tsv_path = f'{REPO_ROOT}/scratch/{tsv_filename}'
    ar_sections_dir = f'{REPO_ROOT}/editions/{book_id}/sections'
    en_trans_dir = f'{REPO_ROOT}/editions/{book_id}/translations/en/sections'
    
    if not os.path.exists(tsv_path):
        print(f"Error: {tsv_path} not found")
        return False
    
    print(f"Loading TSV for {book_id}...")
    en_data = {}
    with open(tsv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        headers = next(reader)
        for row in reader:
            if len(row) < 62: continue
            num = row[54].strip()
            text = row[61].strip()
            # Clean machine prefix
            text = text.replace('[Machine] ', '')
            if num:
                en_data[num] = text
    
    print(f"Loaded {len(en_data)} translations.")
    os.makedirs(en_trans_dir, exist_ok=True)
    
    files = sorted([f for f in os.listdir(ar_sections_dir) if f.endswith('.toon')], 
                   key=lambda x: int(x.split('.')[0]))
    
    for f in files:
        src_path = os.path.join(ar_sections_dir, f)
        dest_path = os.path.join(en_trans_dir, f)
        
        with open(src_path, 'r', encoding='utf-8') as fobj:
            lines = fobj.readlines()
        
        h_numbers = []
        in_data = False
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith('hadiths['):
                in_data = True
                continue
            if in_data:
                parts = line.split(',', 1)
                h_numbers.append(parts[0].strip())
        
        if not h_numbers: continue
        
        sec_id = f.replace('.toon', '')
        h_first = h_numbers[0]
        h_last = h_numbers[-1]
        count = len(h_numbers)
        
        with open(dest_path, 'w', encoding='utf-8') as fobj:
            fobj.write('metadata:\n')
            fobj.write(f'  section_id: {sec_id}\n')
            fobj.write(f'  hadith_first: {h_first}\n')
            fobj.write(f'  hadith_last: {h_last}\n\n')
            fobj.write(f'hadiths[{count}]{{hadithnumber,text,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
            
            for hn in h_numbers:
                text = en_data.get(hn, '')
                # Row format: hadithnumber,text,grades,reference,international_number,narrator_chain,chapter_intro
                row = [hn, text, '', '', '', '', '']
                output = io.StringIO()
                writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='')
                writer.writerow(row)
                fobj.write(output.getvalue() + '\n')
    
    print(f"Completed integration for {book_id}")
    return True

if __name__ == "__main__":
    import_book('mustadrak', 'mustadrak.tsv')
    import_book('bayhaqi', 'bayhaqi.tsv')
