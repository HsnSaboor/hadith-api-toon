#!/usr/bin/env python3
"""
Extract data from takhreej abudawud.jsonl:
  1. Hindi translation → editions/abudawud/translations/hi/sections/N.toon
  2. Roman Urdu translation → editions/abudawud/translations/ro/sections/N.toon
  3. References (Takhreej) comparison report
  4. Grades comparison report (takhreej Urdu Takhreej grade vs grades.toon)

Usage:
    python3 scripts/extract_takhreej_abudawud.py

Outputs:
    editions/abudawud/translations/hi/  ← Hindi sections
    editions/abudawud/translations/ro/  ← Roman Urdu sections
    RAW_SOURCE_ABUDAWUD_REPORT.md         ← Comparison of refs & grades
"""

import json
import os
import re
import sys

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_SOURCE_JSONL = "/home/saboor/takhreej-source/hadith/abu_dawood.jsonl"
ABUDAWUD_DIR   = os.path.join(REPO_ROOT, "editions", "abudawud")
GRADES_TOON    = os.path.join(REPO_ROOT, "grades.toon")
REPORT_PATH    = os.path.join(REPO_ROOT, "RAW_SOURCE_ABUDAWUD_REPORT.md")

# Known Urdu grade keywords (to detect grade vs reference number in Takhreej)
URDU_GRADES = {
    "صحیح",          # Sahih
    "حسن",           # Hasan
    "حسن صحیح",      # Hasan Sahih
    "ضعیف",          # Daif
    "موضوع",         # Maudu
    "شاذ",           # Shadh
    "منکر",          # Munkar
    "صحیح لغیرہ",    # Sahih Lighairihi
    "حسن لغیرہ",     # Hasan Lighairihi
    "مقطوع",         # Maqtu
    "مرسل",          # Mursal
    "معضل",          # Mu'dal
    "ضعیف جدا",      # Very Daif
    "موقوف",         # Mawquf
}


def extract_grade_from_takhreej(takhreej: str) -> str:
    """
    Parse the last parenthetical from a Takhreej string.
    Only return it if it's a recognisable grade keyword, not a reference number.
    Example:
      "...سنن الدارمی/الطھارة ۴ (۶۸۶) (حسن صحیح)"  → "حسن صحیح"
      "...مسند احمد (۴/۳۹۶، ۳۹۹، ۴۱۴)"              → ""
    """
    if not takhreej:
        return ""
    # Grab the last parenthetical
    matches = re.findall(r'\(([^)]+)\)\s*$', takhreej.strip())
    if not matches:
        return ""
    candidate = matches[0].strip()
    # Accept only if it's a grade keyword
    if candidate in URDU_GRADES:
        return candidate
    return ""


def load_grades_toon(path: str) -> dict:
    """
    Returns { hadithnumber_str: [(grader, grade), ...] }
    for abudawud entries in grades.toon.
    """
    grades: dict = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("abudawud,"):
                continue
            parts = line.split(",", 3)
            if len(parts) < 4:
                continue
            _, num, grader, grade = parts
            grades.setdefault(num, []).append((grader, grade.strip()))
    return grades


def read_takhreej(path: str) -> list:
    """
    Load all records from the JSONL file, returning a list of dicts.
    Each dict retains: hadees_number, kitab_id, kitab, kitab_eng,
    book_number, volume, status, arabic, plus per-language translation data.
    """
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_toon_sections(records: list, lang_id: int, lang_code: str, lang_label: str):
    """
    Write one section file per kitab_id for the given language.
    Each line is a JSON object: {"hadithnumber": "N", "text": "..."}
    Mirrors the structure of existing ur/en section files.
    """
    out_dir = os.path.join(ABUDAWUD_DIR, "translations", lang_code, "sections")
    metadata_dir = os.path.join(ABUDAWUD_DIR, "translations", lang_code)
    os.makedirs(out_dir, exist_ok=True)

    # Write metadata.toon
    meta_path = os.path.join(metadata_dir, "metadata.toon")
    meta = {
        "metadata": {
            "language": lang_code,
            "language_name": lang_label,
            "total_hadiths": len(records),
            "source": "takhreej-source",
        }
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(yaml_like(meta))

    # Group records by kitab_id
    kitab_groups: dict = {}
    for rec in records:
        kid = rec["kitab_id"]
        kitab_groups.setdefault(kid, []).append(rec)

    written = 0
    empty_count = 0

    for kid in sorted(kitab_groups.keys()):
        section_recs = kitab_groups[kid]
        section_lines = []

        for rec in section_recs:
            text = ""
            for t in rec.get("translations", []):
                if t["language_id"] == lang_id:
                    text = t.get("hadees", "").strip()
                    break
            entry = {
                "hadithnumber": str(rec["hadees_number"]),
                "text": text,
            }
            section_lines.append(json.dumps(entry, ensure_ascii=False))
            written += 1
            if not text:
                empty_count += 1

        out_path = os.path.join(out_dir, f"{kid}.toon")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(section_lines) + "\n")

    print(f"  [{lang_code}] Written {len(kitab_groups)} section files | "
          f"{written} hadiths | {empty_count} empty texts")
    return written, empty_count


def yaml_like(d: dict, indent: int = 0) -> str:
    """Minimal YAML-like serialiser matching the existing metadata.toon format."""
    lines = []
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{k}:")
            lines.append(yaml_like(v, indent + 1))
        else:
            lines.append(f'{prefix}{k}: "{v}"')
    return "\n".join(lines) + "\n"


def generate_report(records: list, grades_toon: dict) -> str:
    """
    Build a Markdown report comparing:
      1. Takhreej Takhreej grades vs grades.toon (first 30 hadiths)
      2. Full reference (Takhreej) comparison for first 30 hadiths
    """
    lines = [
        "# Takhreej AbuDawud — References & Grades Comparison Report",
        "",
        "Source: `takhreej-source/hadith/abu_dawood.jsonl`  ",
        "Compared against: `grades.toon` (Al-Albani grading shown as primary)",
        "",
        "---",
        "",
        "## Grade Comparison (First 50 Hadiths)",
        "",
        "| # | Takhreej Takhreej Grade (Urdu) | grades.toon Al-Albani | grades.toon Shuaib Al Arnaut | Match? |",
        "|---|---|---|---|---|",
    ]

    for rec in records[:50]:
        num = str(rec["hadees_number"])
        takhreej = ""
        for t in rec.get("translations", []):
            if t["language"] == "urdu":
                takhreej = t.get("Takhreej", "")
                break

        i360_grade = extract_grade_from_takhreej(takhreej)
        our_grades  = grades_toon.get(num, [])
        albani      = next((g for gr, g in our_grades if "Albani"    in gr), "—")
        shuaib      = next((g for gr, g in our_grades if "Shuaib"    in gr), "—")

        match = "✅" if i360_grade and i360_grade in (albani, shuaib) else ("—" if not i360_grade else "⚠️")
        lines.append(f"| {num} | {i360_grade or '*(not parseable)*'} | {albani} | {shuaib} | {match} |")

    lines += [
        "",
        "---",
        "",
        "## Reference (Takhreej) Comparison (First 30 Hadiths)",
        "",
        "> Takhreej stores full Takhreej in Urdu. Our grades.toon does not store Takhreej/references —",
        "> only grader:grade pairs. The table below shows the full Takhreej for reference.",
        "",
        "| # | Takhreej (from Takhreej Urdu) | Notes / Our Reference Data |",
        "|---|---|---|",
    ]

    for rec in records[:30]:
        num = str(rec["hadees_number"])
        takhreej = ""
        for t in rec.get("translations", []):
            if t["language"] == "urdu":
                takhreej = t.get("Takhreej", "").strip()
                break

        our_grades = grades_toon.get(num, [])
        our_str    = " | ".join(f"{gr}: {g}" for gr, g in our_grades) if our_grades else "*(no grade)*"
        takhreej_display = takhreej[:180].replace("|", "｜") if takhreej else "*(empty)*"
        lines.append(f"| {num} | {takhreej_display} | {our_str} |")

    lines += [
        "",
        "---",
        "",
        "## Summary",
        "",
        f"- Total hadiths in takhreej Abu Dawood: **{len(records)}**",
        f"- Hadiths with parseable grade in Takhreej: "
        f"**{sum(1 for r in records for t in r['translations'] if t['language']=='urdu' and extract_grade_from_takhreej(t.get('Takhreej','')))}**",
        f"- Hadiths with grades in grades.toon: **{len(grades_toon)}**",
        "",
        "### Language Fields Available in Takhreej",
        "",
        "| language_id | Language | Fields Available |",
        "|---|---|---|",
        "| 1 | Urdu | hadees, baab, kitab, ravi, Takhreej, wazahat |",
        "| 2 | English | hadees, baab, kitab, ravi, Takhreej, wazahat |",
        "| 3 | Hindi | hadees, baab, kitab |",
        "| 4 | Roman (Urdu) | hadees, baab, kitab |",
        "",
        "### Extraction Output",
        "",
        "| Language | Folder | Section Files |",
        "|---|---|---|",
        "| Hindi | `editions/abudawud/translations/hi/` | 43 kitab-based files |",
        "| Roman Urdu | `editions/abudawud/translations/ro/` | 43 kitab-based files |",
    ]

    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Takhreej AbuDawud Extractor")
    print("=" * 60)

    # 1. Load data
    print("\n[1] Loading takhreej data …")
    records = read_takhreej(RAW_SOURCE_JSONL)
    print(f"    → {len(records)} records loaded")

    # 2. Load grades.toon
    print("\n[2] Loading grades.toon …")
    grades = load_grades_toon(GRADES_TOON)
    print(f"    → {len(grades)} abudawud hadith numbers with grades")

    # 3. Extract Hindi
    print("\n[3] Extracting Hindi (language_id=3) …")
    write_toon_sections(records, lang_id=3, lang_code="hi", lang_label="Hindi")

    # 4. Extract Roman Urdu
    print("\n[4] Extracting Roman Urdu (language_id=4) …")
    write_toon_sections(records, lang_id=4, lang_code="ro", lang_label="Roman Urdu")

    # 5. Generate comparison report
    print("\n[5] Generating comparison report …")
    report = generate_report(records, grades)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"    → Report written to {REPORT_PATH}")

    # 6. Update info.toon to list new languages
    print("\n[6] Updating editions/abudawud/info.toon …")
    info_path = os.path.join(ABUDAWUD_DIR, "info.toon")
    with open(info_path, encoding="utf-8") as f:
        info_content = f.read()

    # Add hi, ro to available_languages if not already there
    if '"hi"' not in info_content and "hi" not in info_content:
        info_content = info_content.replace(
            '"ar,bn,en,fr,id,ru,tr,ur"',
            '"ar,bn,en,fr,hi,id,ro,ru,tr,ur"'
        )
        # fallback: any available_languages line
        new_langs = "ar,bn,en,fr,hi,id,ro,ru,tr,ur"
        info_content = re.sub(
            r'available_languages:\s*"[^"]*"',
            f'available_languages: "{new_langs}"',
            info_content
        )
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)
        print("    → Updated available_languages to include hi, ro")
    else:
        print("    → hi/ro already listed in info.toon")

    print("\n✅ Done!")
    print(f"   Hindi:      editions/abudawud/translations/hi/")
    print(f"   Roman Urdu: editions/abudawud/translations/ro/")
    print(f"   Report:     RAW_SOURCE_ABUDAWUD_REPORT.md")


if __name__ == "__main__":
    main()
