#!/usr/bin/env python3
"""
Toon Format Validator
Validates the structure and data integrity of hadith-api-toon files.
"""

import csv
import os
import re
import sys
from pathlib import Path


class ToonValidator:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.errors = []
        self.warnings = []
        self.stats = {
            "books_checked": 0,
            "sections_checked": 0,
            "errors": 0,
            "warnings": 0,
        }

    def log_error(self, book, message):
        self.errors.append(f"[ERROR] {book}: {message}")
        self.stats["errors"] += 1

    def log_warning(self, book, message):
        self.warnings.append(f"[WARN] {book}: {message}")
        self.stats["warnings"] += 1

    def validate_root_info(self):
        """Validate root info.toon file"""
        info_path = self.base_path / "info.toon"
        if not info_path.exists():
            self.log_error("root", "info.toon not found")
            return

        with open(info_path, "r") as f:
            content = f.read()

        # Check required fields
        required = ["version:", "total_books:", "books["]
        for field in required:
            if field not in content:
                self.log_error("root", f"Missing field: {field}")

    def validate_book_info(self, book_id):
        """Validate per-book info.toon file"""
        info_path = self.base_path / "editions" / book_id / "info.toon"
        if not info_path.exists():
            self.log_error(book_id, "info.toon not found")
            return

        with open(info_path, "r") as f:
            content = f.read()

        # Check metadata fields
        required_meta = [
            "book_id:",
            "book_name:",
            "total_hadiths:",
            "available_languages:",
        ]
        for field in required_meta:
            if field not in content:
                self.log_error(book_id, f"Missing metadata: {field}")

        # Check sections header
        sections_match = re.search(r"sections\[(\d+)\]\{([^}]+)\}:", content)
        if not sections_match:
            self.log_error(book_id, "Missing sections header")
            return

        expected_cols = [
            "id",
            "name",
            "name_ar",
            "name_bn",
            "name_en",
            "name_fr",
            "name_id",
            "name_ru",
            "name_tr",
            "name_ur",
            "hadith_first",
            "hadith_last",
            "arabic_first",
            "arabic_last",
        ]
        header_cols = sections_match.group(2).split(",")

        if header_cols != expected_cols:
            self.log_error(
                book_id,
                f"Invalid columns. Expected {len(expected_cols)}, got {len(header_cols)}",
            )

        # Validate section rows
        self.validate_section_rows(book_id, content, len(expected_cols))

    def validate_section_rows(self, book_id, content, expected_cols):
        """Validate individual section rows"""
        lines = content.split("\n")
        in_sections = False

        for line_num, line in enumerate(lines, 1):
            if "sections[" in line:
                in_sections = True
                continue

            if not in_sections:
                continue

            # Check if this is a section row
            if not re.match(r"^  \d+,", line):
                continue

            self.stats["sections_checked"] += 1

            # Parse as CSV to handle quoted commas
            try:
                reader = csv.reader([line])
                parts = next(reader)
            except Exception as e:
                self.log_error(book_id, f"Line {line_num}: CSV parse error - {e}")
                continue

            if len(parts) != expected_cols:
                self.log_error(
                    book_id,
                    f"Line {line_num}: Expected {expected_cols} columns, got {len(parts)}",
                )
                continue

            # Check for empty values in mandatory columns
            # parts[0] = id, parts[1] = name, parts[2] = name_ar, parts[4] = name_en
            if parts[1] == "" or parts[1] == "":
                self.log_error(book_id, f"Line {line_num}: Empty name")
            if parts[2] == "" or parts[2] == "":
                self.log_error(book_id, f"Line {line_num}: Empty name_ar")
            if parts[4] == "" or parts[4] == "":
                self.log_error(book_id, f"Line {line_num}: Empty name_en")

            # Check for placeholder names
            sec_id = parts[0].strip()
            name = parts[1].strip()
            if re.match(r"^Section \d+$", name, re.IGNORECASE):
                self.log_error(book_id, f'Section {sec_id}: Placeholder name "{name}"')

            # Check for Bengali numerals in Arabic column
            name_ar = parts[2].strip()
            if re.search(r"[০১২৩৪৫৬৭৮৯]", name_ar):
                self.log_error(book_id, f"Section {sec_id}: Bengali numerals in Arabic")

    def validate_section_file(self, book_id, section_file):
        """Validate individual section hadith file"""
        file_path = self.base_path / "editions" / book_id / "sections" / section_file

        with open(file_path, "r") as f:
            content = f.read()

        # Should start with hadiths header (no metadata)
        if content.strip().startswith("metadata:"):
            self.log_warning(book_id, f"{section_file}: Still has metadata block")

        if not content.strip().startswith("hadiths["):
            self.log_error(book_id, f"{section_file}: Missing hadiths header")

    def validate_all(self):
        """Run all validations"""
        print("=" * 60)
        print("TOON FORMAT VALIDATOR v2.0")
        print("=" * 60)
        print()

        # Validate root info.toon
        print("Validating root info.toon...")
        self.validate_root_info()

        # Get list of books
        editions_dir = self.base_path / "editions"
        books = [d.name for d in editions_dir.iterdir() if d.is_dir()]

        print(f"Found {len(books)} books to validate")
        print()

        # Validate each book
        for book_id in sorted(books):
            self.stats["books_checked"] += 1
            self.validate_book_info(book_id)

        # Print results
        print()
        print("=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        print(f"Books checked: {self.stats['books_checked']}")
        print(f"Sections checked: {self.stats['sections_checked']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Warnings: {self.stats['warnings']}")
        print()

        if self.errors:
            print("ERRORS:")
            for error in self.errors[:20]:  # Show first 20
                print(f"  {error}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more errors")
            print()

        if self.warnings:
            print("WARNINGS:")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"  {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more warnings")
            print()

        if self.stats["errors"] == 0:
            print("✓ ALL CHECKS PASSED")
            return 0
        else:
            print(f"✗ {self.stats['errors']} ERRORS FOUND")
            return 1


if __name__ == "__main__":
    base_path = sys.argv[1] if len(sys.argv) > 1 else "."
    validator = ToonValidator(base_path)
    exit_code = validator.validate_all()
    sys.exit(exit_code)
