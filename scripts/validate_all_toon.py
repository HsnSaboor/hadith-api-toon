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
        
        # Find all header lines - must match pattern: word[N]{cols}:
        # Not just any {..}: which could be in data (e.g. Quranic verses)
        headers = []
        for i, line in enumerate(lines):
            # Header must start with word[count]{...}:
            if re.match(r'^\s*\w+\[\d+\]\{[^}]+\}:', line):
                match = re.search(r'\{([^}]+)\}', line)
                if match:
                    cols = [c.strip() for c in match.group(1).split(',')]
                    headers.append((i, len(cols), line))
        
        if not headers:
            return errors
        
        # Validate each section between headers
        for idx, (header_idx, expected_cols, header_line) in enumerate(headers):
            # Determine end of this section (next header or end of file)
            if idx + 1 < len(headers):
                section_end = headers[idx + 1][0]
            else:
                section_end = len(lines)
            
            # Validate data rows in this section
            for i in range(header_idx + 1, section_end):
                line = lines[i]
                if not line.strip():
                    continue
                
                # Check for trailing commas
                if line.rstrip().endswith(','):
                    errors.append(f"Line {i + 1}: Trailing comma")
                
                # Parse CSV and check column count
                try:
                    reader = csv.reader(io.StringIO(line))
                    vals = next(reader)
                    if len(vals) != expected_cols:
                        errors.append(f"Line {i + 1}: Expected {expected_cols} columns, got {len(vals)}")
                except csv.Error as e:
                    errors.append(f"Line {i + 1}: CSV parse error - {e}")
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
            for err in errors[:5]:
                print(f"   {err}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more errors")
            print()
    
    print(f"\n{'='*60}")
    print(f"Validation complete: {total_files} files checked")
    print(f"✅ Valid: {total_files - error_count}")
    print(f"❌ Errors: {error_count}")
    
    return 0 if error_count == 0 else 1

if __name__ == '__main__':
    exit(main())
