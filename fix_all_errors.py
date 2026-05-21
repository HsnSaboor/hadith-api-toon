#!/usr/bin/env python3
"""Fix all validation errors in .toon files."""
import re
import csv
import io
from pathlib import Path

def fix_csv_quotes_in_line(line, expected_cols):
    """Fix unescaped quotes within CSV fields."""
    # Count quotes - should be even (2 per field)
    quote_count = line.count('"')
    if quote_count % 2 == 0:
        return line
    
    # Odd number of quotes means unescaped internal quotes
    # Strategy: parse character by character, escape internal quotes
    result = []
    in_quotes = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == '"':
            if not in_quotes:
                # Starting a quoted field
                in_quotes = True
                result.append(c)
            else:
                # Inside a quoted field - check if this is end of field
                # Look ahead: if next non-space char is comma or end, this is end of field
                j = i + 1
                while j < len(line) and line[j] == ' ':
                    j += 1
                if j >= len(line) or line[j] == ',':
                    # End of field
                    in_quotes = False
                    result.append(c)
                else:
                    # Internal quote - escape it
                    result.append('""')
        else:
            result.append(c)
        i += 1
    
    return ''.join(result)


def fix_info_toon(filepath):
    """Fix info.toon files to handle multiple tables."""
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Find all header lines
    header_indices = []
    for i, line in enumerate(lines):
        if '{' in line and '}:' in line:
            header_indices.append(i)
    
    if len(header_indices) <= 1:
        return False  # No multi-table issue
    
    # The validator uses the first header for all lines
    # Fix: ensure each table section is properly separated
    # by adding a comment or marker that validator can skip
    
    # Actually, the best fix is to update the validator
    # But for now, let's ensure the file structure is correct
    
    # Check if there's a metadata block missing
    first_header_idx = header_indices[0]
    
    # If first line is empty and first header is translations, that's fine
    # The issue is the validator doesn't handle multiple tables
    # Let's just ensure the file is well-formed
    
    return False  # info.toon files are structurally correct, validator needs fix


def fix_section_file(filepath):
    """Fix a section file with CSV issues."""
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Find header
    header_line = None
    header_idx = -1
    for i, line in enumerate(lines):
        if '{' in line and '}:' in line:
            header_line = line
            header_idx = i
            break
    
    if not header_line:
        return False
    
    match = re.search(r'\{([^}]+)\}', header_line)
    if not match:
        return False
    
    expected_cols = len([c.strip() for c in match.group(1).split(',')])
    
    fixed = False
    new_lines = lines[:header_idx + 1]
    
    for i, line in enumerate(lines[header_idx + 1:], start=header_idx + 1):
        if not line.strip():
            new_lines.append(line)
            continue
        
        # Try to parse
        try:
            reader = csv.reader(io.StringIO(line))
            vals = next(reader)
            if len(vals) == expected_cols:
                new_lines.append(line)
                continue
            
            # Column mismatch - try fixing quotes
            fixed_line = fix_csv_quotes_in_line(line, expected_cols)
            reader = csv.reader(io.StringIO(fixed_line))
            vals = next(reader)
            
            if len(vals) == expected_cols:
                new_lines.append(fixed_line)
                fixed = True
            else:
                # Still wrong - try adding missing empty columns
                if len(vals) < expected_cols:
                    # Add missing columns
                    while len(vals) < expected_cols:
                        vals.append('')
                    # Reconstruct line
                    writer = csv.writer(io.StringIO())
                    writer.writerow(vals)
                    new_lines.append(writer.getvalue().strip())
                    fixed = True
                else:
                    new_lines.append(line)
        except Exception:
            new_lines.append(line)
    
    if fixed:
        filepath.write_text('\n'.join(new_lines), encoding='utf-8')
    
    return fixed


def fix_translation_file(filepath):
    """Fix a translation file with multiline text issues."""
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Find header
    header_line = None
    header_idx = -1
    for i, line in enumerate(lines):
        if '{' in line and '}:' in line:
            header_line = line
            header_idx = i
            break
    
    if not header_line:
        return False
    
    match = re.search(r'\{([^}]+)\}', header_line)
    if not match:
        return False
    
    expected_cols = len([c.strip() for c in match.group(1).split(',')])
    
    # Translation files should have 2 columns: hadithnumber, text
    # Multiline text should be escaped as \n within the field
    
    fixed = False
    new_lines = lines[:header_idx + 1]
    
    i = header_idx + 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            new_lines.append(line)
            i += 1
            continue
        
        # Check if line starts with a quote (new record)
        if line.strip().startswith('"'):
            # Try to parse as complete record
            try:
                reader = csv.reader(io.StringIO(line))
                vals = next(reader)
                if len(vals) == expected_cols:
                    new_lines.append(line)
                    i += 1
                    continue
            except Exception:
                pass
            
            # Might be multiline - collect lines until we have a valid CSV record
            accumulated = line
            j = i + 1
            while j < len(lines):
                accumulated += '\n' + lines[j]
                try:
                    reader = csv.reader(io.StringIO(accumulated))
                    vals = next(reader)
                    if len(vals) == expected_cols:
                        # Found complete record - escape newlines
                        # Replace actual newlines with \n in text fields
                        fixed_line = accumulated.replace('\n', '\\n')
                        new_lines.append(fixed_line)
                        fixed = True
                        i = j + 1
                        break
                except Exception:
                    pass
                j += 1
            else:
                # Couldn't parse - keep original
                new_lines.append(line)
                i += 1
        else:
            # Continuation of previous line - should have been handled above
            new_lines.append(line)
            i += 1
    
    if fixed:
        filepath.write_text('\n'.join(new_lines), encoding='utf-8')
    
    return fixed


def main():
    root = Path('.')
    
    # Get all failing files
    import subprocess
    result = subprocess.run(
        ['python3', 'scripts/validate_all_toon.py'],
        capture_output=True, text=True, timeout=300
    )
    
    failing_files = []
    for line in result.stdout.split('\n'):
        if line.startswith('❌ editions/'):
            filepath = line.replace('❌ ', '')
            failing_files.append(Path(filepath))
    
    print(f"Found {len(failing_files)} failing files in editions/\n")
    
    fixed_count = 0
    for filepath in failing_files:
        if not filepath.exists():
            continue
        
        print(f"Fixing: {filepath}")
        
        if filepath.name == 'info.toon':
            # info.toon files need validator fix, not data fix
            print(f"  Skipping (validator issue)")
            continue
        
        # Check if it's a translation file
        if 'translations' in str(filepath):
            if fix_translation_file(filepath):
                print(f"  Fixed translation file")
                fixed_count += 1
            else:
                if fix_section_file(filepath):
                    print(f"  Fixed as section file")
                    fixed_count += 1
                else:
                    print(f"  Could not fix")
        else:
            # Section file
            if fix_section_file(filepath):
                print(f"  Fixed section file")
                fixed_count += 1
            else:
                print(f"  Could not fix")
    
    print(f"\nFixed {fixed_count} files")


if __name__ == '__main__':
    main()
