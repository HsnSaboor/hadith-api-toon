#!/usr/bin/env python3
import csv
import io
import re
from pathlib import Path

def fix_file_properly(filepath):
    """Ensure each CSV record is on its own line"""
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
        
        # Rebuild file - one record per line
        fixed_lines = [lines[header_idx]]
        
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip().rstrip(',')
            if not line:
                continue
            
            # Parse and split any concatenated records
            try:
                reader = csv.reader(io.StringIO(line))
                vals = next(reader)
                
                # Split into individual records
                while len(vals) >= expected_cols:
                    record = vals[:expected_cols]
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(record)
                    fixed_lines.append(output.getvalue().strip())
                    vals = vals[expected_cols:]
                    
            except (csv.Error, StopIteration):
                continue
        
        new_content = '\n'.join(fixed_lines)
        if new_content != content:
            filepath.write_text(new_content, encoding='utf-8')
            return True
            
    except Exception as e:
        print(f"Error: {filepath}: {e}")
        return False
    
    return False

def main():
    # Fix the files that still have multiple records per line
    files_to_fix = [
        'grades.toon',
        'references.toon',
    ]
    
    for filepath_str in files_to_fix:
        filepath = Path(filepath_str)
        if filepath.exists():
            print(f"Fixing {filepath}...")
            if fix_file_properly(filepath):
                print(f"  Fixed")
            else:
                print(f"  No changes needed")

if __name__ == '__main__':
    main()
