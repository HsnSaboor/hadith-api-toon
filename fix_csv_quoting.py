#!/usr/bin/env python3
import csv
import io
import re
from pathlib import Path

def fix_csv_quoting(filepath):
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
        
        # Extract expected columns
        match = re.search(r'\{([^}]+)\}', lines[header_idx])
        if not match:
            return False
        
        cols = [c.strip() for c in match.group(1).split(',')]
        expected_cols = len(cols)
        
        # Rebuild data rows with proper quoting
        fixed_lines = lines[:header_idx + 1]
        i = header_idx + 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                fixed_lines.append('')
                i += 1
                continue
            
            # Try parsing as CSV
            try:
                reader = csv.reader(io.StringIO(line))
                vals = next(reader)
                
                # If correct column count, keep as is
                if len(vals) == expected_cols:
                    fixed_lines.append(lines[i])
                    i += 1
                    continue
                
                # If too few columns, might be continuation of previous line
                if len(vals) < expected_cols:
                    # Merge with previous data line
                    if fixed_lines and fixed_lines[-1].strip():
                        fixed_lines[-1] = fixed_lines[-1].rstrip() + ' ' + line
                    i += 1
                    continue
                
                # If too many columns, need to re-quote
                # Parse manually and re-write with proper quoting
                fixed_lines.append(lines[i])
                i += 1
                
            except (csv.Error, StopIteration):
                # Malformed CSV - likely continuation
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines[-1] = fixed_lines[-1].rstrip() + ' ' + line
                i += 1
        
        new_content = '\n'.join(fixed_lines)
        if new_content != content:
            filepath.write_text(new_content, encoding='utf-8')
            return True
            
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
    
    return False

def main():
    root = Path('.')
    toon_files = list(root.rglob('*.toon'))
    
    fixed_count = 0
    
    print(f"Fixing CSV quoting in {len(toon_files)} .toon files...\n")
    
    for filepath in toon_files:
        if fix_csv_quoting(filepath):
            fixed_count += 1
            if fixed_count <= 50:
                print(f"✅ Fixed: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
