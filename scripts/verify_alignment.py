#!/usr/bin/env python3
"""
Verify alignment between grades.toon/references.toon and section files.
Check that the hadith numbers match before injecting.
"""

import re
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/saboor/code/hadith-api-toon")
GRADES_FILE = ROOT / "grades.toon"
REFERENCES_FILE = ROOT / "references.toon"
EDITIONS_DIR = ROOT / "editions"


def get_section_hadith_numbers(book_dir):
    """Get all hadith numbers from a book's section files."""
    hadith_numbers = set()
    sections_dir = book_dir / "sections"
    
    if not sections_dir.exists():
        return hadith_numbers
    
    for section_file in sections_dir.glob("*.toon"):
        try:
            content = section_file.read_text(encoding="utf-8")
        except:
            continue
        
        lines = content.strip().split("\n")
        if not lines:
            continue
        
        # Skip header
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Parse CSV
            reader = csv.reader([line], quotechar='"', doublequote=True)
            try:
                row = list(next(reader))
            except StopIteration:
                continue
            
            if row:
                hadith_numbers.add(row[0].strip())
    
    return hadith_numbers


def get_grades_hadith_numbers():
    """Get hadith numbers from grades.toon."""
    hadith_numbers = defaultdict(set)
    
    try:
        content = GRADES_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return hadith_numbers
    
    lines = content.strip().split("\n")
    if not lines:
        return hadith_numbers
    
    # Skip header
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        parts = line.split(",", 3)
        if len(parts) >= 2:
            book = parts[0].strip()
            hnum = parts[1].strip()
            if book and hnum:
                hadith_numbers[book].add(hnum)
    
    return hadith_numbers


def get_references_hadith_numbers():
    """Get hadith numbers from references.toon."""
    hadith_numbers = defaultdict(set)
    
    try:
        content = REFERENCES_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return hadith_numbers
    
    lines = content.strip().split("\n")
    if not lines:
        return hadith_numbers
    
    # Skip header
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        parts = line.split(",", 3)
        if len(parts) >= 2:
            book = parts[0].strip()
            hnum = parts[1].strip()
            if book and hnum:
                hadith_numbers[book].add(hnum)
    
    return hadith_numbers


def main():
    print("=== VERIFYING ALIGNMENT ===\n")
    
    # Get data from grades/references
    print("Loading grades.toon...")
    grades_hnums = get_grades_hadith_numbers()
    print(f"  Found {sum(len(v) for v in grades_hnums.values())} entries across {len(grades_hnums)} books")
    
    print("Loading references.toon...")
    refs_hnums = get_references_hadith_numbers()
    print(f"  Found {sum(len(v) for v in refs_hnums.values())} entries across {len(refs_hnums)} books")
    
    print("\n=== CHECKING EACH BOOK ===\n")
    
    total_section = 0
    total_grades_match = 0
    total_refs_match = 0
    issues = []
    
    for book_dir in sorted(EDITIONS_DIR.iterdir()):
        if not book_dir.is_dir():
            continue
        
        book_id = book_dir.name
        
        # Get section hadith numbers
        section_hnums = get_section_hadith_numbers(book_dir)
        total_section += len(section_hnums)
        
        if not section_hnums:
            print(f"{book_id}: NO SECTION FILES")
            continue
        
        # Get grades hadith numbers
        grades_book = grades_hnums.get(book_id, set())
        grades_match = grades_book & section_hnums
        grades_extra = grades_book - section_hnums
        
        # Get references hadith numbers  
        refs_book = refs_hnums.get(book_id, set())
        refs_match = refs_book & section_hnums
        refs_extra = refs_book - section_hnums
        
        total_grades_match += len(grades_match)
        total_refs_match += len(refs_match)
        
        # Report
        status = "✓"
        if len(grades_extra) > 100 or len(refs_extra) > 100:
            status = "⚠"
        if len(grades_extra) > 1000 or len(refs_extra) > 1000:
            status = "✗"
        
        print(f"{status} {book_id}:")
        print(f"    Section hadiths: {len(section_hnums)}")
        print(f"    Grades match: {len(grades_match)} / {len(grades_book)} (missing: {len(grades_extra)})")
        print(f"    Refs match:  {len(refs_match)} / {len(refs_book)} (missing: {len(refs_extra)})")
        
        if len(grades_extra) > 10:
            issues.append(f"{book_id}: {len(grades_extra)} extra grades entries")
        if len(refs_extra) > 10:
            issues.append(f"{book_id}: {len(refs_extra)} extra refs entries")
    
    print("\n=== SUMMARY ===")
    print(f"Total section hadiths: {total_section}")
    print(f"Grades aligned: {total_grades_match}")
    print(f"References aligned: {total_refs_match}")
    
    if issues:
        print("\n=== ISSUES ===")
        for issue in issues[:10]:
            print(f"  {issue}")
    else:
        print("\n✓ All books aligned!")


if __name__ == "__main__":
    main()