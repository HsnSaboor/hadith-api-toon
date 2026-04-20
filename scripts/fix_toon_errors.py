#!/usr/bin/env python3
import re
import csv
import io
from pathlib import Path

def fix_toon_file(filepath):
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Find header
        header_idx = -1
        for i, line in enumerate(lines):
            if '{' in line and '}:' in line:
                header_idx = i
                break
        
        if header_idx == -1:
            return False
        
        # Extract expected column count
        match = re.search(r'\{([^}]+)\}', lines[header_idx])
        if not match:
            return False
        
        cols = [c.strip() for c in match.group(1).split(',')]
        expected_cols = len(cols)
        
        # Fix data rows
        fixed = False
        for i in range(header_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            
            # Remove trailing comma
            if line.rstrip().endswith(','):
                lines[i] = line.rstrip()[:-1]
                fixed = True
        
        if fixed:
            filepath.write_text('\n'.join(lines), encoding='utf-8')
            return True
    
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
    
    return False

def main():
    root = Path('.')
    toon_files = list(root.rglob('*.toon'))
    
    fixed_count = 0
    
    print(f"Fixing {len(toon_files)} .toon files...\n")
    
    for filepath in toon_files:
        if fix_toon_file(filepath):
            fixed_count += 1
            print(f"✅ Fixed: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
