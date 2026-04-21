#!/usr/bin/env python3
"""Add translation index to book-level info.toon files."""

import os
from pathlib import Path

def get_translation_info(book_path):
    """Get translation metadata for a book."""
    translations_dir = book_path / "translations"
    if not translations_dir.exists():
        return []
    
    translations = []
    for lang_dir in sorted(translations_dir.iterdir()):
        if not lang_dir.is_dir():
            continue
        
        lang_code = lang_dir.name
        sections_dir = lang_dir / "sections"
        
        if sections_dir.exists():
            section_count = len(list(sections_dir.glob("*.toon")))
            translations.append({
                'language': lang_code,
                'sections': section_count,
                'path': f"translations/{lang_code}"
            })
    
    return translations

def update_book_info(book_path):
    """Update book info.toon with translation index."""
    info_file = book_path / "info.toon"
    if not info_file.exists():
        return
    
    translations = get_translation_info(book_path)
    if not translations:
        return
    
    # Read existing content
    with open(info_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find where to insert translations table
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith('sections['):
            insert_idx = i
            break
    
    if insert_idx is None:
        return
    
    # Build translations table
    trans_lines = [
        f"\ntranslations[{len(translations)}]{{language,sections,path}}:\n"
    ]
    for t in translations:
        trans_lines.append(f"{t['language']},{t['sections']},{t['path']}\n")
    trans_lines.append("\n")
    
    # Insert translations table before sections
    lines[insert_idx:insert_idx] = trans_lines
    
    # Write back
    with open(info_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✓ {book_path.name}: Added {len(translations)} translations")

def main():
    editions_dir = Path("editions")
    
    for book_dir in sorted(editions_dir.iterdir()):
        if book_dir.is_dir():
            update_book_info(book_dir)

if __name__ == "__main__":
    main()
