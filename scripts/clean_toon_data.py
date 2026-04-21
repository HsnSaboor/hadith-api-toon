#!/usr/bin/env python3
"""
Comprehensive .toon file cleaning utility.
Fixes common CSV formatting issues in .toon files including:
- Trailing commas
- Unquoted fields with embedded commas/newlines
- Concatenated records on single lines
- Improper CSV escaping
"""
import csv
import io
import re
from pathlib import Path
from typing import List, Optional

def fix_toon_file(filepath: Path) -> bool:
    """Fix all CSV issues in a .toon file."""
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Find header line
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
        
        # Rebuild file with proper CSV formatting
        fixed_lines = [lines[header_idx]]
        buffer = []
        
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip().rstrip(',')
            if not line:
                continue
            
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
                    if vals:
                        buffer = vals
                elif len(vals) < expected_cols:
                    # Merge with buffer
                    if buffer:
                        buffer.extend(vals)
                        if len(buffer) >= expected_cols:
                            output = io.StringIO()
                            writer = csv.writer(output)
                            writer.writerow(buffer[:expected_cols])
                            fixed_lines.append(output.getvalue().strip())
                            buffer = buffer[expected_cols:]
                    else:
                        buffer = vals
                        
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
    """Clean all .toon files in the repository."""
    import sys
    
    if len(sys.argv) > 1:
        # Clean specific files
        files = [Path(f) for f in sys.argv[1:]]
    else:
        # Clean all .toon files
        root = Path('.')
        files = list(root.rglob('*.toon'))
    
    fixed = 0
    for filepath in files:
        if filepath.exists() and fix_toon_file(filepath):
            fixed += 1
            print(f"Fixed: {filepath}")
    
    print(f"\nCleaned {fixed} files")

if __name__ == '__main__':
    main()
