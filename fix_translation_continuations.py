#!/usr/bin/env python3
"""Fix translation files where continuation lines need to be merged into previous records."""
import csv
import io
import re
from pathlib import Path

def fix_translation_file(filepath):
    """Fix a translation file with continuation lines."""
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Find header
    header_line = None
    header_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^\s*\w+\[\d+\]\{[^}]+\}:', line):
            header_line = line
            header_idx = i
            break
    
    if not header_line:
        return False
    
    # Process lines after header
    new_lines = []
    current_record = None
    
    def save_record(rec):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(rec)
        new_lines.append(buf.getvalue().strip())
    
    for i, line in enumerate(lines[header_idx + 1:], start=header_idx + 2):
        if not line.strip():
            continue
        
        # Try to parse as CSV
        try:
            reader = csv.reader(io.StringIO(line))
            vals = next(reader)
        except Exception:
            # If can't parse, treat as continuation
            if current_record is not None:
                current_record[-1] += line
            continue
        
        if len(vals) == 2:
            # Valid record - save previous if exists
            if current_record is not None:
                save_record(current_record)
            current_record = vals
        elif len(vals) == 1:
            # Continuation line - append to current record's text
            if current_record is not None:
                current_record[-1] += line
            # else: orphan continuation line, skip
        else:
            # Unexpected column count - save current and keep this line
            if current_record is not None:
                save_record(current_record)
                current_record = None
            # Try to handle as best we can
            if len(vals) > 2:
                # Might be a record with commas in text - reconstruct
                hadith_num = vals[0]
                text = ','.join(vals[1:])
                current_record = [hadith_num, text]
            else:
                new_lines.append(line)
    
    # Save last record
    if current_record is not None:
        save_record(current_record)
    
    # Reconstruct file with header count updated
    record_count = len(new_lines)
    new_header = re.sub(r'\[\d+\]', f'[{record_count}]', header_line)
    
    final_content = new_header + '\n' + '\n'.join(new_lines) + '\n'
    
    if final_content != content:
        filepath.write_text(final_content, encoding='utf-8')
        return True
    
    return False


def main():
    import sys
    files = sys.argv[1:]
    
    fixed = 0
    skipped = 0
    
    for f in files:
        filepath = Path(f)
        if not filepath.exists():
            continue
        
        print(f"Fixing: {filepath}")
        if fix_translation_file(filepath):
            print(f"  Fixed")
            fixed += 1
        else:
            print(f"  No changes needed")
            skipped += 1
    
    print(f"\nFixed: {fixed}, Skipped: {skipped}")


if __name__ == '__main__':
    main()
