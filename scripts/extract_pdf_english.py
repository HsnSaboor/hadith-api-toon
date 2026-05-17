#!/usr/bin/env python3
"""Extract English hadiths from Dar-us-Salam PDFs and create lulu English sections."""
import fitz, re, os, json

BASE = os.path.dirname(os.path.dirname(__file__))

def fix_ocr(text):
    text = text.replace('All0h', 'Allah').replace('All6h', 'Allah')
    text = text.replace('Isl6m', 'Islam').replace('Qur\'6n', 'Qur\'an')
    text = text.replace('Ahddfth', 'Hadith').replace('Hadtth', 'Hadith')
    text = text.replace('Abt', 'Abu').replace('Ab0', 'Abu')
    text = text.replace('l;', '').replace(';,', '').replace('.,', '')
    text = text.replace('drr', '').replace('or ', '').replace('er ', '')
    # Remove Arabic-script fragments
    text = re.sub(r'[\u0600-\u06FF]{2,}', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = []
    for i in range(len(doc)):
        page = doc[i]
        rect = page.rect
        left_rect = fitz.Rect(0, 0, rect.width/2, rect.height)
        text = page.get_text('text', clip=left_rect)
        all_text.append(text)
    full = '\n'.join(all_text)
    
    # Parse hadiths
    hadiths = {}
    for m in re.finditer(r'^(\d+)\.\s*(.*)', full, re.MULTILINE):
        num = m.group(1)
        rest = m.group(2).strip()
        if rest.startswith('Narrated') or rest.startswith('narrated'):
            # Collect text until next hadith number
            start = m.end()
            next_m = re.search(r'^\d+\.\s*(?:Narrated|narrated)', full[m.end():], re.MULTILINE)
            if next_m:
                hadith_text = full[m.start():m.end()+next_m.start()]
            else:
                hadith_text = full[m.start():]
            # Clean up
            hadith_text = fix_ocr(hadith_text)
            hadiths[num] = hadith_text
    
    return hadiths

print("Extracting Volume 1...")
v1 = extract_from_pdf('/tmp/lulu_vol1.pdf')
print(f"  {len(v1)} hadiths")

print("Extracting Volume 2...")
v2 = extract_from_pdf('/tmp/lulu_vol2.pdf')
print(f"  {len(v2)} hadiths")

all_en = {**v1, **v2}
print(f"Total: {len(all_en)} hadiths")

# Write to English sections
SECTIONS_DIR = os.path.join(BASE, "editions", "lulu-wal-marjan", "sections")
EN_DIR = os.path.join(BASE, "editions", "lulu-wal-marjan", "translations", "en", "sections")
os.makedirs(EN_DIR, exist_ok=True)
for f in os.listdir(EN_DIR):
    os.remove(os.path.join(EN_DIR, f))

total = matched = 0
for fn in sorted(os.listdir(SECTIONS_DIR), key=lambda x: int(x.split('.')[0])):
    ch = int(fn.split('.')[0])
    nums = []
    with open(os.path.join(SECTIONS_DIR, fn)) as f:
        for line in f:
            if line.strip() and not line.startswith('hadiths['):
                p = line.split(',',1)
                if p[0].strip().isdigit():
                    nums.append(p[0].strip())
    
    entries = []
    cm = 0
    for n in nums:
        total += 1
        if n in all_en:
            entries.append((n, all_en[n]))
            cm += 1
            matched += 1
        else:
            entries.append((n, ""))
    
    with open(os.path.join(EN_DIR, f"{ch}.toon"), 'w') as f:
        f.write(f"hadiths[{len(entries)}]{{hadithnumber,text}}:\n")
        for n, t in entries:
            if t:
                f.write(f'{n},"{t}"\n')
            else:
                f.write(f'{n},\n')
    print(f"  Ch {ch}: {cm}/{len(nums)}")

print(f"\nMatched: {matched}/{total} ({100*matched//total}%)")
