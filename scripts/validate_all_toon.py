#!/usr/bin/env python3
import re
import csv
import io
from pathlib import Path

def validate_toon_file(filepath):
    errors = []
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Find header line
        header_line = None
        header_idx = -1
        for i, line in enumerate(lines):
            if '{' in line and '}:' in line:
                header_line = line
                header_idx = i
                break
        
        if not header_line:
            return errors
        
        # Extract column names from header
        match = re.search(r'\{([^}]+)\}', header_line)
        if not match:
            errors.append(f"Invalid header format: {header_line}")
            return errors
        
        cols = [c.strip() for c in match.group(1).split(',')]
        expected_cols = len(cols)
        
        # Validate data rows
        for i, line in enumerate(lines[header_idx + 1:], start=header_idx + 2):
            if not line.strip():
                continue
            
            # Check for trailing commas
            if line.rstrip().endswith(','):
                errors.append(f"Line {i}: Trailing comma")
            
            # Parse CSV and check column count
            try:
                reader = csv.reader(io.StringIO(line))
                vals = next(reader)
                if len(vals) != expected_cols:
                    errors.append(f"Line {i}: Expected {expected_cols} columns, got {len(vals)}")
            except csv.Error as e:
                errors.append(f"Line {i}: CSV parse error - {e}")
            except StopIteration:
                pass
    
    except Exception as e:
        errors.append(f"File read error: {e}")
    
    return errors

def main():
    root = Path('.')
    toon_files = list(root.rglob('*.toon'))
    
    total_files = len(toon_files)
    error_count = 0
    
    print(f"Validating {total_files} .toon files...\n")
    
    for filepath in toon_files:
        errors = validate_toon_file(filepath)
        if errors:
            error_count += 1
            print(f"❌ {filepath}")
            for err in errors:
                print(f"   {err}")
            print()
    
    print(f"\n{'='*60}")
    print(f"Validation complete: {total_files} files checked")
    print(f"✅ Valid: {total_files - error_count}")
    print(f"❌ Errors: {error_count}")
    
    return 0 if error_count == 0 else 1

if __name__ == '__main__':
    exit(main())
