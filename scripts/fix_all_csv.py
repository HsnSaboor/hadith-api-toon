#!/usr/bin/env python3
"""
fix_all_csv.py — Fix CSV quoting and structure across all .toon files.

Fixes:
  1. Unquoted commas in text fields (re-quote with csv.writer)
  2. Unescaped double quotes inside fields ("" escape per RFC 4180)
  3. Trailing commas (strip excess empty fields after last populated)
  4. Column count mismatches (pad with empty fields or trim)
  5. aladab-almufrad info.toon empty section rows

Usage: python3 scripts/fix_all_csv.py
"""

import csv
import io
import re
from pathlib import Path

def fix_block(data_lines, expected_cols, start_line_num):
    """Fix CSV rows for a single data block. Returns (fixed_lines, stats, fixed_ok)."""
    fixed = []
    trailing = 0
    col_mismatch = 0
    requoted = 0
    ok = True
    
    for i, line in enumerate(data_lines):
        line_num = start_line_num + i
        
        # Skip blank lines
        if not line.strip():
            fixed.append(line)
            continue
        
        # Detect if line starts a NEW block (sections[...]{...}: or similar)
        if re.match(r'^(hadiths|sections|books|translations)\[\d+\]\{', line):
            fixed.append(line)
            continue
        
        # Also detect lines that are clearly headers (ends with : and no data comma pattern)
        if re.match(r'^\w+\[?\w*\]?\{.+\}:$', line.strip()):
            fixed.append(line)
            continue
        
        trimmed = line.rstrip('\r\n ')
        
        # Add a sentinel to preserve trailing empty fields in CSV read
        trail_count = 0
        if trimmed.endswith(','):
            trail_count = len(trimmed) - len(trimmed.rstrip(','))
        
        working_line = trimmed
        need_sentinel = trail_count > 0
        if need_sentinel:
            working_line = trimmed + '##SENTINEL##'
        
        try:
            reader = csv.reader(io.StringIO(working_line))
            vals = next(reader)
        except (csv.Error, StopIteration):
            fixed.append(line)
            ok = False
            continue
        
        # Remove sentinel
        if need_sentinel and vals and vals[-1] == '##SENTINEL##':
            vals = vals[:-1]
        
        # Remove sentinel if consumed inside a quoted field
        if need_sentinel and (not vals or vals[-1] != '##SENTINEL##'):
            pass  # sentinel was consumed by csv.reader, which is fine
        
        actual = len(vals)
        
        if actual != expected_cols:
            col_mismatch += 1
            if actual < expected_cols:
                vals.extend([''] * (expected_cols - actual))
            elif actual > expected_cols:
                vals = vals[:expected_cols]
                # Check if we just chopped off real data
                excess = [v for v in vals[expected_cols:] if v]
                if excess and expected_cols < 5:
                    ok = False  # Significant data loss
        
        if trail_count > 0:
            trailing += 1
        
        # Determine if re-quoting is needed
        needs_quote = any(',' in v or '\n' in v or v.startswith(' ') or v.endswith(' ') for v in vals)
        has_bad_quotes = any('"' in v for v in vals)
        if needs_quote or has_bad_quotes:
            requoted += 1
        
        # Re-serialize with proper CSV quoting
        out = io.StringIO()
        writer = csv.writer(out, quoting=csv.QUOTE_ALL)
        writer.writerow(vals)
        serialized = out.getvalue().rstrip('\r\n')
        
        # Check if the new line differs from original (ignoring whitespace)
        if serialized != trimmed:
            fixed.append(serialized)
        else:
            fixed.append(line)
    
    return fixed, {
        'trailing': trailing,
        'col_mismatch': col_mismatch,
        'requoted': requoted,
        'ok': ok
    }


def fix_toon_file(filepath):
    """Fix a single .toon file. Returns (success, message)."""
    try:
        original = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return (False, f"Read error: {e}")
    
    lines = original.split('\n')
    
    # Find all data blocks: lines that declare a table header
    block_headers = []
    for i, line in enumerate(lines):
        m = re.match(r'^(hadiths|sections|books|translations)\[(\w+)\]\{([^}]+)\}:', line.strip())
        if m:
            table_type = m.group(1)
            count = m.group(2)
            col_names = [c.strip() for c in m.group(3).split(',')]
            block_headers.append({
                'line_idx': i,
                'type': table_type,
                'count': count,
                'expected_cols': len(col_names),
                'cols': col_names
            })
    
    if not block_headers:
        return (True, "No data blocks found")
    
    # Process each block separately
    changes = 0
    new_lines = list(lines)
    total_trailing = 0
    total_col_mismatch = 0
    total_requoted = 0
    had_errors = False
    
    for idx, block in enumerate(block_headers):
        start = block['line_idx'] + 1
        end = len(lines)
        
        # Find where this block ends (next block header or end of file)
        if idx + 1 < len(block_headers):
            end = block_headers[idx + 1]['line_idx']
        
        data_slice = lines[start:end]
        fixed_slice, stats = fix_block(
            data_slice,
            block['expected_cols'],
            start + 1
        )
        
        total_trailing += stats['trailing']
        total_col_mismatch += stats['col_mismatch']
        total_requoted += stats['requoted']
        if not stats['ok']:
            had_errors = True
        
        # Replace the data section
        new_lines[start:end] = fixed_slice
        changes += sum(1 for i in range(len(data_slice)) if i >= len(fixed_slice) or data_slice[i] != fixed_slice[i])
    
    new_content = '\n'.join(new_lines)
    
    if new_content != original:
        filepath.write_text(new_content, encoding='utf-8')
        details = []
        if total_trailing: details.append(f"trailing={total_trailing}")
        if total_col_mismatch: details.append(f"colmismatch={total_col_mismatch}")
        if total_requoted: details.append(f"requote={total_requoted}")
        return (not had_errors, f"Fixed: {','.join(details)}")
    else:
        return (True, "No changes")


def fix_aladab_info(filepath):
    """Remove duplicate empty section rows from aladab-almufrad info.toon."""
    try:
        original = filepath.read_text(encoding='utf-8')
    except Exception:
        return False
    
    lines = original.split('\n')
    
    # Find sections header
    section_idx = None
    for i, line in enumerate(lines):
        if line.startswith('sections['):
            section_idx = i
            break
    
    if section_idx is None:
        return False
    
    # Find where the duplicate rows start (empty name fields)
    data_start = section_idx + 1
    cutoff = data_start
    
    for i in range(data_start, len(lines)):
        line = lines[i].strip()
        if not line:
            cutoff = i
            continue
        try:
            reader = csv.reader(io.StringIO(line))
            vals = next(reader)
            if len(vals) >= 2 and vals[1] == '' and vals[0].isdigit():
                # Empty name = duplicate row, stop here
                break
        except:
            break
        cutoff = i + 1
    
    new_lines = lines[:cutoff]
    new_content = '\n'.join(new_lines)
    
    if new_content != original:
        filepath.write_text(new_content, encoding='utf-8')
        removed = len(lines) - len(new_lines)
        print(f"  ✓ Removed {removed} duplicate empty section rows")
        return True
    return False


def main():
    root = Path('.')
    toon_files = list(root.rglob('*.toon'))
    
    print(f"Found {len(toon_files)} .toon files\n")
    
    # 1. Special fix: aladab-almufrad info.toon
    aladab_info = root / 'editions' / 'aladab-almufrad' / 'info.toon'
    if aladab_info.exists():
        print("=== aladab-almufrad info.toon ===")
        fix_aladab_info(aladab_info)
    
    # 2. Generic CSV fix for all files
    print("\n=== Generic CSV Fix ===")
    
    total = 0
    fixed = 0
    errors = 0
    
    for filepath in toon_files:
        rel = filepath.relative_to(root)
        ok, msg = fix_toon_file(filepath)
        total += 1
        if not ok:
            print(f"  ❌ {rel}: {msg}")
            errors += 1
        elif msg.startswith("Fixed"):
            print(f"  ✓ {rel}: {msg}")
            fixed += 1
    
    print(f"\n{'='*60}")
    print(f"Files: {total} total, {fixed} fixed, {errors} errors/unfixable")
    print(f"\nRun 'python3 scripts/validate_all_toon.py' to verify")


if __name__ == '__main__':
    main()
