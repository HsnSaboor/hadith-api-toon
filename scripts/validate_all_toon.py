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
        
        # Stateful line accumulation to handle newlines inside quotes
        rebuilt_lines = []
        accumulated = []
        in_quote = False
        start_line = 1
        
        for i, line in enumerate(lines):
            if not in_quote:
                start_line = i + 1
                accumulated = [line]
            else:
                accumulated.append(line)
            
            # Count double-quotes that are not escaped (double-double quotes like "")
            # We can simplify by removing escaped quotes and counting the remaining single double-quotes
            cleaned = line.replace('""', '')
            quotes_count = cleaned.count('"')
            if quotes_count % 2 == 1:
                in_quote = not in_quote
            
            if not in_quote:
                rebuilt_lines.append(("\n".join(accumulated), start_line))
        
        # Parse headers first
        headers = []
        for idx, (line_content, orig_line_num) in enumerate(rebuilt_lines):
            if re.match(r'^\s*\w+\[\d+\]\{[^}]+\}:', line_content):
                match = re.search(r'\{([^}]+)\}', line_content)
                if match:
                    cols = [c.strip() for c in match.group(1).split(',')]
                    headers.append((idx, len(cols), line_content, orig_line_num))
        
        if not headers:
            return errors
            
        # Validate sections
        for idx, (header_idx, expected_cols, header_line, orig_line_num) in enumerate(headers):
            if idx + 1 < len(headers):
                section_end = headers[idx + 1][0]
            else:
                section_end = len(rebuilt_lines)
                
            for i in range(header_idx + 1, section_end):
                line_content, line_num = rebuilt_lines[i]
                if not line_content.strip():
                    continue
                
                try:
                    reader = csv.reader(io.StringIO(line_content))
                    vals = next(reader)
                    if len(vals) != expected_cols:
                        errors.append(f"Line {line_num}: Expected {expected_cols} columns, got {len(vals)}")
                except csv.Error as e:
                    errors.append(f"Line {line_num}: CSV parse error - {e}")
                except StopIteration:
                    pass
                    
    except Exception as e:
        errors.append(f"File read error: {e}")
        
    return errors

def main():
    root = Path('.')
    toon_files = list(root.glob('editions/**/*.toon'))
    
    total_files = len(toon_files)
    error_count = 0
    
    print(f"Validating {total_files} active .toon files...\n")
    
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
