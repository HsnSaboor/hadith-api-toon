#!/usr/bin/env python3
"""Audit all books and regenerate info.toon files with correct data."""

import csv
import io
from pathlib import Path

def get_actual_languages(book_path):
    """Get actual translation languages from filesystem."""
    trans_dir = book_path / "translations"
    if not trans_dir.exists():
        return []
    return sorted([d.name for d in trans_dir.iterdir() if d.is_dir()])

def count_sections(book_path):
    """Count actual section files."""
    sections_dir = book_path / "sections"
    if not sections_dir.exists():
        return 0
    return len([f for f in sections_dir.glob("*.toon")])

def count_hadiths(book_path):
    """Count total hadiths from section files."""
    sections_dir = book_path / "sections"
    if not sections_dir.exists():
        return 0
    
    total = 0
    for section_file in sections_dir.glob("*.toon"):
        content = section_file.read_text(encoding='utf-8')
        lines = [l for l in content.split('\n') if l.strip()]
        # Skip header line
        total += len(lines) - 1
    return total

# Audit all books
editions_dir = Path("editions")
books_data = []

for book_dir in sorted(editions_dir.iterdir()):
    if not book_dir.is_dir():
        continue
    
    book_id = book_dir.name
    info_file = book_dir / "info.toon"
    
    # Get actual data
    actual_langs = get_actual_languages(book_dir)
    section_count = count_sections(book_dir)
    hadith_count = count_hadiths(book_dir)
    
    # Read book name from existing info.toon if it exists
    book_name = book_id.replace("-", " ").title()
    if info_file.exists():
        content = info_file.read_text(encoding='utf-8')
        # Try to extract book name from metadata or sections header
        for line in content.split('\n'):
            if 'book_name:' in line:
                book_name = line.split(':', 1)[1].strip().strip('"')
                break
    
    # Add 'ar' to languages if not present (Arabic base always exists)
    if 'ar' not in actual_langs:
        actual_langs = ['ar'] + actual_langs
    
    books_data.append({
        'id': book_id,
        'name': book_name,
        'total_hadiths': hadith_count,
        'languages': ','.join(actual_langs),
        'path': f'editions/{book_id}',
        'section_count': section_count,
        'translation_langs': [l for l in actual_langs if l != 'ar']
    })
    
    print(f"✓ {book_id}: {len(actual_langs)} langs, {section_count} sections, {hadith_count} hadiths")

# Generate root info.toon
print("\nGenerating root info.toon...")
output = f"books[{len(books_data)}]{{id,name,total_hadiths,available_languages,path}}:\n"
for book in books_data:
    output += f"{book['id']},{book['name']},{book['total_hadiths']},\"{book['languages']}\",{book['path']}\n"

Path("info.toon").write_text(output, encoding='utf-8')
print(f"✓ Generated root info.toon with {len(books_data)} books")

# Generate per-book info.toon files
print("\nGenerating per-book info.toon files...")
for book in books_data:
    book_dir = Path(f"editions/{book['id']}")
    info_file = book_dir / "info.toon"
    
    # Build translations section
    trans_lines = []
    for lang in book['translation_langs']:
        trans_dir = book_dir / "translations" / lang / "sections"
        if trans_dir.exists():
            section_count = len(list(trans_dir.glob("*.toon")))
            trans_lines.append(f"{lang},{section_count},translations/{lang}")
    
    output = "\n"
    if trans_lines:
        output += f"translations[{len(trans_lines)}]{{language,sections,path}}:\n"
        output += "\n".join(trans_lines) + "\n"
    
    # Read existing sections data if available
    if info_file.exists():
        existing = info_file.read_text(encoding='utf-8')
        if 'sections[' in existing:
            sections_part = existing[existing.index('sections['):]
            output += "\n" + sections_part
    
    info_file.write_text(output, encoding='utf-8')
    print(f"✓ {book['id']}/info.toon")

print("\n✅ All info files regenerated with correct data")
