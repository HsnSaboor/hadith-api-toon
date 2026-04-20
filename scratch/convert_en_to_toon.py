import os
import json
import csv
import io

REPO_ROOT = '/home/saboor/code/hadith-api-toon'
editions_dir = f'{REPO_ROOT}/editions'

# Books skipped because they were already migrated to TOON or are special
exclude_books = [
    'aladab-almufrad', 'bulugh-al-maram', 'mishkat', 
    'musnad-ahmed', 'shamail-tirmazi', 'eng-aladab-almufrad',
    'eng-bulugh-al-maram', 'eng-mishkat', 'eng-musnad-ahmed',
    'eng-shamail-tirmazi', 'eng-sunan-darmi'
]

def convert_jsonl_to_toon(src_file, dest_file, section_id):
    if not os.path.exists(src_file): return False
    
    hadiths = []
    with open(src_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                hadiths.append(data)
            except:
                continue
    
    if not hadiths: return False
    
    hadith_first = hadiths[0].get('hadithnumber', '0')
    hadith_last = hadiths[-1].get('hadithnumber', '0')
    count = len(hadiths)
    
    with open(dest_file, 'w', encoding='utf-8') as f:
        f.write('metadata:\n')
        f.write(f'  section_id: {section_id}\n')
        f.write(f'  hadith_first: {hadith_first}\n')
        f.write(f'  hadith_last: {hadith_last}\n\n')
        f.write(f'hadiths[{count}]{{hadithnumber,text,grades,reference,international_number,narrator_chain,chapter_intro}}:\n')
        
        # Write lines in CSV-like format
        for h in hadiths:
            # Use CSV writer to handle quotes and commas properly
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='')
            
            # Columns: hadithnumber, text, grades, reference, international_number, narrator_chain, chapter_intro
            row = [
                h.get('hadithnumber', ''),
                h.get('text', ''),
                '', # grades
                '', # reference
                h.get('international_number', ''),
                h.get('narrator_chain', ''),
                ''  # chapter_intro
            ]
            writer.writerow(row)
            f.write(output.getvalue() + '\n')
    return True

all_books = [d for d in os.listdir(editions_dir) if os.path.isdir(os.path.join(editions_dir, d)) and d not in exclude_books]

for book_id in all_books:
    sections_path = os.path.join(editions_dir, book_id, 'translations', 'en', 'sections')
    if not os.path.exists(sections_path): continue
    
    print(f'Converting {book_id}...')
    temp_dir = sections_path + '_tmp'
    os.makedirs(temp_dir, exist_ok=True)
    
    converted_count = 0
    for f in sorted(os.listdir(sections_path)):
        if f.endswith('.toon'):
            # Double check if it's already TOON (has "metadata:")
            with open(os.path.join(sections_path, f), 'r') as check_f:
                first_line = check_f.read(10)
                if 'metadata:' in first_line or 'hadiths[' in first_line:
                    print(f'  Skipping {f}, already TOON')
                    continue
            
            section_id = f.replace('.toon', '')
            if convert_jsonl_to_toon(os.path.join(sections_path, f), os.path.join(temp_dir, f), section_id):
                converted_count += 1
    
    if converted_count > 0:
        # Swap dirs
        shutil_backup = sections_path + '_backup'
        if os.path.exists(shutil_backup):
            import shutil
            shutil.rmtree(shutil_backup)
        os.rename(sections_path, shutil_backup)
        os.rename(temp_dir, sections_path)
        print(f'  Successfully converted {converted_count} sections for {book_id}')
    else:
        import shutil
        shutil.rmtree(temp_dir)
        print(f'  No sections needed conversion for {book_id}')
