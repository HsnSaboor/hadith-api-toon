#!/usr/bin/env python3
import csv
import io
import re
from pathlib import Path

def fix_csv_file(filepath):
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
        
        # Rebuild file with proper CSV formatting
        fixed_lines = [lines[header_idx]]
        
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            
            # Check if line has concatenated entries (multiple records on one line)
            # Pattern: ends with a value, then immediately starts with a new record
            parts = []
            current = line
            
            while current:
                # Try to parse as CSV
                try:
                    reader = csv.reader(io.StringIO(current))
                    vals = next(reader)
                    
                    if len(vals) == expected_cols:
                        # Properly quote fields with commas
                        output = io.StringIO()
                        writer = csv.writer(output)
                        writer.writerow(vals)
                        fixed_lines.append(output.getvalue().strip())
                        break
                    elif len(vals) > expected_cols:
                        # Too many columns - likely concatenated or unquoted commas
                        # Try to split into proper records
                        
                        # First, try to extract one proper record
                        proper_vals = vals[:expected_cols]
                        output = io.StringIO()
                        writer = csv.writer(output)
                        writer.writerow(proper_vals)
                        fixed_lines.append(output.getvalue().strip())
                        
                        # Reconstruct remaining as new line
                        remaining_vals = vals[expected_cols:]
                        if remaining_vals:
                            output = io.StringIO()
                            writer = csv.writer(output)
                            writer.writerow(remaining_vals)
                            current = output.getvalue().strip()
                        else:
                            break
                    else:
                        # Too few columns - skip or merge
                        break
                        
                except (csv.Error, StopIteration):
                    break
        
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
    
    print(f"Fixing all CSV issues in {len(toon_files)} .toon files...\n")
    
    for filepath in toon_files:
        if fix_csv_file(filepath):
            fixed_count += 1
            if fixed_count <= 50:
                print(f"✅ Fixed: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
