#!/usr/bin/env python3
import csv
import io
import re
from pathlib import Path

def fix_file(filepath):
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
        
        # Rebuild file
        fixed_lines = [lines[header_idx]]
        
        for i in range(header_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            
            # Remove trailing comma
            line = line.rstrip(',').rstrip()
            
            if not line:
                continue
            
            # Parse and rewrite with proper quoting
            try:
                reader = csv.reader(io.StringIO(line))
                vals = next(reader)
                
                if len(vals) == expected_cols:
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(vals)
                    fixed_lines.append(output.getvalue().strip())
                elif len(vals) > expected_cols:
                    # Split concatenated records
                    while len(vals) >= expected_cols:
                        output = io.StringIO()
                        writer = csv.writer(output)
                        writer.writerow(vals[:expected_cols])
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
    with open('/tmp/error_files2.txt', 'r') as f:
        error_files = [line.strip() for line in f if line.strip()]
    
    fixed = 0
    
    for filepath_str in error_files:
        filepath = Path(filepath_str)
        if filepath.exists() and fix_file(filepath):
            fixed += 1
            print(f"✅ {filepath}")
    
    print(f"\nFixed {fixed} files")

if __name__ == '__main__':
    main()
