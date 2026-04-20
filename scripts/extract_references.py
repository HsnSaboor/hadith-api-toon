#!/usr/bin/env python3
"""
Extract Takhreej (cross-references) from all takhreej JSONL files,
verify against existing data, and write a new references.toon file.

WHAT THIS DOES:
  1. Reads Takhreej field from every takhreej JSONL book
  2. Maps takhreej book names → our edition names
  3. Verifies hadith number alignment
  4. Writes references.toon with format:
       references[N]{book,hadithnumber,source,takhreej}:
       abudawud,1,takhreej,تخریج دارالدعوہ: سنن الترمذی...
  5. Generates REFERENCES_REPORT.md with coverage stats

BOOK MAPPING (takhreej → our edition name):
  abu_dawood  → abudawud
  maja        → ibnmajah
  muwatta     → malik
  nasai       → nasai
  tirmazi     → tirmidhi
  bukhari     → bukhari
  muslim      → muslim
  beyhaqi     → bayhaqi
  darmi       → sunan-darmi
  khuzaymah   → sahih-ibn-khuzaymah
  mishkat     → mishkat
  silsila     → silsila-sahih
  alzawaid    → alzawaid  (no matching edition, kept as-is)
  musnad      → musnad-ahmed

Usage:
    python3 scripts/extract_references.py
"""

import json
import os
import re

# ─────────────────────────────────────────────────────
REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_SOURCE    = "/home/saboor/takhreej-source/hadith"
REFS_OUT    = os.path.join(REPO_ROOT, "references.toon")
REPORT_OUT  = os.path.join(REPO_ROOT, "REFERENCES_REPORT.md")
# ─────────────────────────────────────────────────────

# takhreej JSONL filename (without .jsonl) → our edition book_id
BOOK_MAP = {
    "abu_dawood":  "abudawud",
    "maja":        "ibnmajah",
    "muwatta":     "malik",
    "nasai":       "nasai",
    "tirmazi":     "tirmidhi",
    "bukhari":     "bukhari",
    "muslim":      "muslim",
    "beyhaqi":     "bayhaqi",
    "darmi":       "sunan-darmi",
    "khuzaymah":   "sahih-ibn-khuzaymah",
    "mishkat":     "mishkat",
    "silsila":     "silsila-sahih",
    "alzawaid":    "alzawaid",
    "musnad":      "musnad-ahmed",
    "mustadrak":   "mustadrak",
    "shaybah":     "musannaf-ibn-abi-shaybah",
    "Shaybah":     None,   # duplicate — skip
}

# Books already covered by grades.toon (with full grader stacks)
GRADE_BOOKS = {"abudawud", "ibnmajah", "malik", "nasai", "tirmidhi"}


def load_edition_hadith_numbers(edition_id: str) -> set:
    """Read all hadithnumbers present in ur or en translations for a given edition."""
    nums: set = set()
    edition_path = os.path.join(REPO_ROOT, "editions", edition_id)
    if not os.path.isdir(edition_path):
        return nums
    # Try ur first, then en
    for lang in ("ur", "en"):
        sections_path = os.path.join(edition_path, "translations", lang, "sections")
        if not os.path.isdir(sections_path):
            continue
        for fname in os.listdir(sections_path):
            if not fname.endswith(".toon"):
                continue
            with open(os.path.join(sections_path, fname), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            nums.add(str(obj.get("hadithnumber", "")))
                        except json.JSONDecodeError:
                            pass
        if nums:
            break
    return nums


def extract_book(jsonl_path: str, edition_id: str) -> dict:
    """
    Extract {hadithnumber_str: takhreej_str} from one JSONL file.
    Returns only entries where Takhreej is non-empty.
    """
    result = {}
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            num = str(obj.get("hadees_number", ""))
            for t in obj.get("translations", []):
                lang = t.get("language") or ""
                if lang == "urdu":
                    tak = (t.get("Takhreej") or "").strip()
                    # Skip NULL, empty, or very short non-meaningful values
                    if tak and tak.upper() != "NULL" and len(tak) >= 5:
                        result[num] = tak
                    break
    return result


def build_references():
    print("=" * 60)
    print("References Extractor — takhreej → references.toon")
    print("=" * 60)

    all_entries: list[tuple] = []  # (edition_id, hadith_num, takhreej)
    stats: dict = {}

    files = sorted([f for f in os.listdir(RAW_SOURCE) if f.endswith(".jsonl")])

    for fname in files:
        key = fname.replace(".jsonl", "")
        edition_id = BOOK_MAP.get(key)
        if edition_id is None:
            print(f"\n  Skipping {fname} (no mapping or duplicate)")
            continue

        jsonl_path = os.path.join(RAW_SOURCE, fname)
        print(f"\n[{key}] → edition '{edition_id}'")

        # Extract Takhreej
        takhreej_map = extract_book(jsonl_path, edition_id)
        print(f"  Extracted Takhreej: {len(takhreej_map)} entries")

        if not takhreej_map:
            stats[edition_id] = {
                "extracted": 0, "verified": 0, "added": 0, "skipped": 0,
                "in_grades": edition_id in GRADE_BOOKS,
            }
            continue

        # Verify against our edition (if it exists)
        our_nums = load_edition_hadith_numbers(edition_id)
        verified = 0
        skipped = 0
        added = 0

        for num, tak in sorted(takhreej_map.items(), key=lambda x: _sort_key(x[0])):
            if our_nums and num not in our_nums:
                skipped += 1
                continue
            all_entries.append((edition_id, num, tak))
            added += 1
            verified += 1 if our_nums else 0

        print(f"  Our edition hadiths: {len(our_nums)}")
        print(f"  Verified (num in our edition): {verified}")
        print(f"  Skipped (not in our edition):  {skipped}")
        print(f"  Written to references.toon:    {added}")

        stats[edition_id] = {
            "extracted": len(takhreej_map),
            "verified": verified,
            "added": added,
            "skipped": skipped,
            "in_grades": edition_id in GRADE_BOOKS,
        }

    # ── Write references.toon ────────────────────────────────
    print(f"\n[Writing] {REFS_OUT}")
    total = len(all_entries)
    with open(REFS_OUT, "w", encoding="utf-8") as f:
        f.write(f"references[{total}]{{book,hadithnumber,source,takhreej}}:\n")
        for edition_id, num, tak in all_entries:
            # Escape any commas in Takhreej (use tab-safe writing; commas in Arabic are fine)
            safe_tak = tak.replace("\n", " ").replace("\r", " ")
            f.write(f"{edition_id},{num},takhreej,{safe_tak}\n")
    print(f"  → {total} reference entries written")

    # ── Write report ─────────────────────────────────────────
    _write_report(stats, total)
    print(f"\n[Report] {REPORT_OUT}")
    print("\n✅ Done!")
    return stats


def _sort_key(num_str: str):
    """Natural sort for hadith numbers like '1', '10', '1132.2'."""
    try:
        return (int(num_str.split(".")[0]), int(num_str.split(".")[1]) if "." in num_str else 0)
    except ValueError:
        return (999999, 0)


def _write_report(stats: dict, total: int):
    lines = [
        "# References Extraction Report",
        "",
        f"Source: `takhreej-source/hadith/*.jsonl`  ",
        f"Output: `references.toon` ({total:,} entries)",
        "",
        "---",
        "",
        "## Coverage Summary",
        "",
        "| Edition | Extracted | Added to refs.toon | Skipped (not in edition) | Already in grades.toon? |",
        "|---------|-----------|-------------------|--------------------------|------------------------|",
    ]

    for edition_id, s in sorted(stats.items()):
        grade_flag = "✅ Yes" if s["in_grades"] else "—"
        lines.append(
            f"| {edition_id} | {s['extracted']:,} | {s['added']:,} | {s['skipped']:,} | {grade_flag} |"
        )

    lines += [
        "",
        "---",
        "",
        "## What Is a Takhreej?",
        "",
        "**Takhreej** (تخریج) is a cross-reference field in Islamic hadith scholarship.",
        "It lists where the same hadith appears in other major collections, along with",
        "the grade/authenticity ruling at the end (e.g., `(حسن صحیح)` = Hasan Sahih).",
        "",
        "Example:",
        "```",
        "تخریج دارالدعوہ: سنن الترمذی/الطھارة ۱۶ (۲۰)، سنن النسائی/الطھارة ۱۶ (۱۷)،",
        "سنن ابن ماجہ/الطھارة ۲۲ (۳۳۱)، (تحفة الأشراف: ۱۱۵۴۰)،",
        "وقد أخرجہ: مسند احمد (۴/۲۴۴)، سنن الدارمی/الطھارة ۴ (۶۸۶) (حسن صحیح)",
        "```",
        "",
        "## File Format — references.toon",
        "",
        "```",
        "references[N]{book,hadithnumber,source,takhreej}:",
        "abudawud,1,takhreej,تخریج دارالدعوہ: ...",
        "abudawud,2,takhreej,تخریج دارالدعوہ: ...",
        "```",
        "",
        "## Relationship to grades.toon",
        "",
        "| File | Content | Books covered |",
        "|------|---------|---------------|",
        "| `grades.toon` | Structured `grader: grade` pairs (Al-Albani, Shuaib Al Arnaut, etc.) | abudawud, ibnmajah, malik, nasai, tirmidhi |",
        "| `references.toon` | Free-text Urdu Takhreej (cross-references + embedded grade) | All books with non-zero Takhreej in takhreej |",
        "",
        "These are **complementary** — `grades.toon` has machine-readable English grades,",
        "`references.toon` has rich Urdu scholarly cross-reference text.",
        "",
        "## Books With Zero Takhreej (takhreej gaps)",
        "",
        "| Book | Reason |",
        "|------|--------|",
        "| muslim | Only 5/7564 hadiths have Takhreej in takhreej |",
        "| musnad | No Takhreej available |",
        "| mustadrak | No Takhreej available |",
        "| shaybah | No Takhreej available |",
    ]

    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    build_references()
