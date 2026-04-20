#!/usr/bin/env python3
"""Convert JSON translation files to CSV .toon format."""

import io
import csv
import json
from pathlib import Path

EDITIONS_DIR = Path("editions")


def is_already_converted(first_line: str) -> bool:
    """Check if file already uses .toon CSV format."""
    return first_line.strip().startswith("hadiths[")


def convert_json_to_toon(file_path: Path) -> int:
    """Convert JSON-Lines file to CSV .toon format. Returns row count."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    
    if not lines:
        return 0
    
    # Check if already converted
    if is_already_converted(lines[0]):
        print(f"  Skipping (already converted): {file_path.name}")
        return 0
    
    # Parse JSON and collect rows
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            rows.append([obj["hadithnumber"], obj["text"]])
        except json.JSONDecodeError:
            continue  # Skip malformed lines
    
    if not rows:
        return 0
    
    # Write as proper CSV
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, doublequote=True)
    for row in rows:
        writer.writerow(row)
    
    csv_content = output.getvalue()
    
    # Prepend header
    header = f"hadiths[{len(rows)}]{{hadithnumber,text}}:\n"
    final_content = header + csv_content
    
    file_path.write_text(final_content, encoding="utf-8")
    return len(rows)


def main():
    print("=== Finding translation files ===")
    
    # Find all translation section files
    translation_files = []
    for book_dir in EDITIONS_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        translations_dir = book_dir / "translations"
        if not translations_dir.exists():
            continue
        
        for lang_dir in translations_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            sections_dir = lang_dir / "sections"
            if not sections_dir.exists():
                continue
            
            for toon_file in sections_dir.glob("*.toon"):
                translation_files.append(toon_file)
    
    print(f"Found {len(translation_files)} translation files")
    
    total_converted = 0
    
    # Process ALL translation files
    print("\n=== Converting all files ===")
    for toon_file in translation_files:
        count = convert_json_to_toon(toon_file)
        if count > 0:
            print(f"  {toon_file.parent.parent.parent.name}/{toon_file.parent.name}: {count} rows")
            total_converted += count
    
    print(f"\n=== COMPLETE: {total_converted} rows converted across {len(translation_files)} files ===")


if __name__ == "__main__":
    main()