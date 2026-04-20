#!/usr/bin/env python3
import subprocess
import csv
import io
import re
from pathlib import Path

def get_record_count(content):
    """Count data records in a toon file"""
    lines = content.split('\n')
    count = 0
    for line in lines:
        if line.strip() and not ('{' in line and '}:' in line):
            count += 1
    return count

def analyze_file_changes(filepath):
    """Analyze before/after changes for a file"""
    try:
        # Get before version (from commit a80a541dd0)
        result_before = subprocess.run(
            ['git', 'show', f'a80a541dd0:{filepath}'],
            capture_output=True, text=True, check=True
        )
        before_content = result_before.stdout
        
        # Get after version (current)
        after_content = Path(filepath).read_text(encoding='utf-8')
        
        before_count = get_record_count(before_content)
        after_count = get_record_count(after_content)
        
        return {
            'file': filepath,
            'before_records': before_count,
            'after_records': after_count,
            'diff': after_count - before_count,
            'before_content': before_content,
            'after_content': after_content
        }
    except Exception as e:
        return {'file': filepath, 'error': str(e)}

def show_sample_diff(filepath, num_samples=3):
    """Show sample before/after records"""
    try:
        result = subprocess.run(
            ['git', 'diff', 'a80a541dd0..HEAD', '--', filepath],
            capture_output=True, text=True, check=True
        )
        
        diff_output = result.stdout
        if not diff_output:
            return None
        
        # Extract a few changed lines
        lines = diff_output.split('\n')
        changes = []
        for i, line in enumerate(lines[:100]):  # First 100 lines of diff
            if line.startswith('-') and not line.startswith('---'):
                changes.append(('REMOVED', line[1:]))
            elif line.startswith('+') and not line.startswith('+++'):
                changes.append(('ADDED', line[1:]))
        
        return changes[:num_samples * 2]
    except Exception as e:
        return None

def main():
    # Files to check
    test_files = [
        'grades.toon',
        'references.toon',
        'editions/mishkat/sections/3.toon',
        'editions/aladab-almufrad/sections/42.toon',
        'editions/mustadrak/translations/ur/sections/27.toon'
    ]
    
    print("=" * 70)
    print("DATA INTEGRITY VERIFICATION REPORT")
    print("=" * 70)
    print()
    
    total_before = 0
    total_after = 0
    
    for filepath in test_files:
        if not Path(filepath).exists():
            print(f"File not found: {filepath}")
            continue
        
        print(f"\n{filepath}")
        print("-" * 70)
        
        analysis = analyze_file_changes(filepath)
        
        if 'error' in analysis:
            print(f"   Error: {analysis['error']}")
            continue
        
        before = analysis['before_records']
        after = analysis['after_records']
        diff = analysis['diff']
        
        total_before += before
        total_after += after
        
        status = "OK" if diff == 0 else ("WARNING" if diff < 0 else "INCREASED")
        print(f"   {status}: Records: {before} -> {after} (diff: {diff:+d})")
        
        # Show sample changes
        samples = show_sample_diff(filepath, num_samples=2)
        if samples:
            print(f"\n   Sample changes:")
            for change_type, content in samples[:4]:
                if content.strip():
                    preview = content[:80] + '...' if len(content) > 80 else content
                    print(f"   {change_type:8s}: {preview}")
    
    print("\n" + "=" * 70)
    print(f"SUMMARY")
    print("=" * 70)
    print(f"Total records before: {total_before}")
    print(f"Total records after:  {total_after}")
    print(f"Net change:           {total_after - total_before:+d}")
    
    if total_after < total_before:
        print("\nWARNING: Record count decreased - possible data loss!")
    elif total_after > total_before:
        print("\nRecord count increased - likely split concatenated records")
    else:
        print("\nRecord count unchanged - data preserved")

if __name__ == '__main__':
    main()
