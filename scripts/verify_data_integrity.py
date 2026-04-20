#!/usr/bin/env python3
import csv
import io
import re
from pathlib import Path
from collections import defaultdict

def count_records(filepath):
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Find header
        for i, line in enumerate(lines):
            if '{' in line and '}:' in line:
                return len([l for l in lines[i+1:] if l.strip()])
        return 0
    except:
        return 0

def main():
    root = Path('.')
    toon_files = list(root.rglob('*.toon'))
    
    stats = defaultdict(int)
    
    for filepath in toon_files:
        count = count_records(filepath)
        stats['total_files'] += 1
        stats['total_records'] += count
        
        if 'translations' in str(filepath):
            stats['translation_records'] += count
        elif 'sections' in str(filepath):
            stats['section_records'] += count
        elif filepath.name == 'grades.toon':
            stats['grade_records'] = count
        elif filepath.name == 'references.toon':
            stats['reference_records'] = count
    
    print("Data Integrity Report")
    print("=" * 60)
    print(f"Total .toon files: {stats['total_files']:,}")
    print(f"Total records: {stats['total_records']:,}")
    print(f"  - Section records: {stats['section_records']:,}")
    print(f"  - Translation records: {stats['translation_records']:,}")
    print(f"  - Grade records: {stats['grade_records']:,}")
    print(f"  - Reference records: {stats['reference_records']:,}")

if __name__ == '__main__':
    main()
