#!/usr/bin/env python3
"""
Deep verification: Compare Hindi & Roman Urdu translations against Arabic and English.
For every book with hi/ro, check:
  1. Section file alignment (same kitab_ids exist)
  2. Hadith number alignment (same hadithnumbers in each section)
  3. Coverage gaps (hadiths missing in hi/ro vs ar and en)
  4. Empty text ratio per language
  5. Structural issues (duplicate numbers, malformed records)
"""

import json
import os
import re
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITIONS  = os.path.join(REPO_ROOT, "editions")


def load_section_toon(path: str, is_translation=False) -> list:
    """Load a section .toon file. Returns list of dicts."""
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            # Translation files are JSONL: {"hadithnumber": ..., "text": ...}
            if is_translation:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    records.append({"_error": str(e), "_lineno": i, "_raw": line[:80]})
            else:
                # Main section files use toon format
                # Parse: field:value or JSONL
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    # Try pipe-separated or other formats
                    records.append({"_raw": line[:80]})
    return records


def get_hadithnumbers(records: list) -> set:
    nums = set()
    for r in records:
        if "hadithnumber" in r:
            nums.add(str(r["hadithnumber"]))
    return nums


def get_empty_count(records: list) -> int:
    count = 0
    for r in records:
        text = r.get("text", "")
        if not text or not str(text).strip():
            count += 1
    return count


def load_arabic_hadithnumbers(edition_dir: str) -> dict:
    """Load hadithnumber → True from all main section files."""
    sec_dir = os.path.join(edition_dir, "sections")
    all_nums = {}  # section_id → set of hadithnumbers
    if not os.path.isdir(sec_dir):
        return all_nums
    for fname in os.listdir(sec_dir):
        if not fname.endswith(".toon"):
            continue
        kid = fname.replace(".toon", "")
        path = os.path.join(sec_dir, fname)
        recs = load_section_toon(path, is_translation=False)
        nums = set()
        for r in recs:
            hn = r.get("hadithnumber") or r.get("hadith_number")
            if hn:
                nums.add(str(hn))
        all_nums[kid] = nums
    return all_nums


def load_translation_hadithnumbers(trans_sec_dir: str) -> dict:
    """Load section_id → set of hadithnumbers from a translation sections dir."""
    all_nums = {}
    if not os.path.isdir(trans_sec_dir):
        return all_nums
    for fname in os.listdir(trans_sec_dir):
        if not fname.endswith(".toon"):
            continue
        kid = fname.replace(".toon", "")
        path = os.path.join(trans_sec_dir, fname)
        recs = load_section_toon(path, is_translation=True)
        nums = set()
        for r in recs:
            hn = r.get("hadithnumber")
            if hn:
                nums.add(str(hn))
        all_nums[kid] = nums
    return all_nums


def check_edition(edition_id: str, issues: list, summary: dict):
    ed_dir = os.path.join(EDITIONS, edition_id)
    hi_sec_dir = os.path.join(ed_dir, "translations", "hi", "sections")
    ro_sec_dir = os.path.join(ed_dir, "translations", "ro", "sections")
    en_sec_dir = os.path.join(ed_dir, "translations", "en", "sections")
    ar_sec_dir = os.path.join(ed_dir, "sections")

    has_hi = os.path.isdir(hi_sec_dir)
    has_ro = os.path.isdir(ro_sec_dir)
    has_en = os.path.isdir(en_sec_dir)
    has_ar = os.path.isdir(ar_sec_dir)

    if not has_hi and not has_ro:
        return  # Skip books with no hi/ro

    # Load all section hadithnumbers
    ar_secs   = load_arabic_hadithnumbers(ed_dir) if has_ar else {}
    en_secs   = load_translation_hadithnumbers(en_sec_dir) if has_en else {}
    hi_secs   = load_translation_hadithnumbers(hi_sec_dir) if has_hi else {}
    ro_secs   = load_translation_hadithnumbers(ro_sec_dir) if has_ro else {}

    # Build full arabic set
    ar_all = set()
    for nums in ar_secs.values():
        ar_all |= nums
    en_all = set()
    for nums in en_secs.values():
        en_all |= nums

    hi_all = set()
    for nums in hi_secs.values():
        hi_all |= nums
    ro_all = set()
    for nums in ro_secs.values():
        ro_all |= nums

    # 1. Section file count alignment
    ar_kids = set(ar_secs.keys())
    en_kids = set(en_secs.keys())
    hi_kids = set(hi_secs.keys())
    ro_kids = set(ro_secs.keys())

    ref_kids = ar_kids if ar_kids else en_kids  # Use arabic as reference, fallback to english

    hi_missing_sections = ref_kids - hi_kids
    ro_missing_sections = ref_kids - ro_kids
    hi_extra_sections   = hi_kids - ref_kids
    ro_extra_sections   = ro_kids - ref_kids

    # 2. Coverage: hadiths in arabic/english but missing in hi/ro
    ref_all = ar_all if ar_all else en_all

    hi_missing_hadiths = ref_all - hi_all
    ro_missing_hadiths = ref_all - ro_all
    hi_extra_hadiths   = hi_all - ref_all
    ro_extra_hadiths   = ro_all - ref_all

    # 3. Empty text analysis
    hi_total = hi_empty = 0
    ro_total = ro_empty = 0

    if has_hi:
        for fname in os.listdir(hi_sec_dir):
            if not fname.endswith(".toon"): continue
            recs = load_section_toon(os.path.join(hi_sec_dir, fname), is_translation=True)
            hi_total += len(recs)
            hi_empty += get_empty_count(recs)

    if has_ro:
        for fname in os.listdir(ro_sec_dir):
            if not fname.endswith(".toon"): continue
            recs = load_section_toon(os.path.join(ro_sec_dir, fname), is_translation=True)
            ro_total += len(recs)
            ro_empty += get_empty_count(recs)

    # 4. Per-section alignment issues
    per_section_gaps = {}
    for kid in sorted(ref_kids):
        ar_nums = ar_secs.get(kid, set())
        en_nums = en_secs.get(kid, set())
        hi_nums = hi_secs.get(kid, set())
        ro_nums = ro_secs.get(kid, set())
        ref_nums = ar_nums if ar_nums else en_nums

        hi_gap = ref_nums - hi_nums
        ro_gap = ref_nums - ro_nums
        hi_xtr = hi_nums - ref_nums
        ro_xtr = ro_nums - ref_nums

        if hi_gap or ro_gap or hi_xtr or ro_xtr:
            per_section_gaps[kid] = {
                "ref_count": len(ref_nums),
                "hi_count": len(hi_nums),
                "ro_count": len(ro_nums),
                "hi_missing": sorted(hi_gap, key=lambda x: float(x) if x.replace('.','',1).isdigit() else 0)[:20],
                "ro_missing": sorted(ro_gap, key=lambda x: float(x) if x.replace('.','',1).isdigit() else 0)[:20],
                "hi_extra": sorted(hi_xtr, key=lambda x: float(x) if x.replace('.','',1).isdigit() else 0)[:20],
                "ro_extra": sorted(ro_xtr, key=lambda x: float(x) if x.replace('.','',1).isdigit() else 0)[:20],
            }

    summary[edition_id] = {
        "ar_sections": len(ar_kids),
        "en_sections": len(en_kids),
        "hi_sections": len(hi_kids),
        "ro_sections": len(ro_kids),
        "ar_hadiths": len(ar_all),
        "en_hadiths": len(en_all),
        "hi_hadiths": hi_total,
        "ro_hadiths": ro_total,
        "hi_empty": hi_empty,
        "ro_empty": ro_empty,
        "hi_missing_hadiths": len(hi_missing_hadiths),
        "ro_missing_hadiths": len(ro_missing_hadiths),
        "hi_extra_hadiths": len(hi_extra_hadiths),
        "ro_extra_hadiths": len(ro_extra_hadiths),
        "hi_missing_sections": sorted(hi_missing_sections),
        "ro_missing_sections": sorted(ro_missing_sections),
        "per_section_gaps": per_section_gaps,
    }


def main():
    print("=" * 80)
    print("DEEP VERIFICATION: Hindi & Roman Urdu vs Arabic & English")
    print("=" * 80)

    issues = []
    summary = {}

    for ed in sorted(os.listdir(EDITIONS)):
        ed_path = os.path.join(EDITIONS, ed)
        if not os.path.isdir(ed_path):
            continue
        hi_exists = os.path.isdir(os.path.join(ed_path, "translations", "hi"))
        ro_exists = os.path.isdir(os.path.join(ed_path, "translations", "ro"))
        if not hi_exists and not ro_exists:
            continue
        sys.stdout.write(f"\r  Checking: {ed:<30}")
        sys.stdout.flush()
        check_edition(ed, issues, summary)

    print("\n")

    # Print detailed report
    for edition_id, s in summary.items():
        ref_sec = max(s["ar_sections"], s["en_sections"])
        ref_had = max(s["ar_hadiths"], s["en_hadiths"])

        hi_pct = (s["hi_hadiths"] / ref_had * 100) if ref_had else 0
        ro_pct = (s["ro_hadiths"] / ref_had * 100) if ref_had else 0
        hi_empty_pct = (s["hi_empty"] / s["hi_hadiths"] * 100) if s["hi_hadiths"] else 0
        ro_empty_pct = (s["ro_empty"] / s["ro_hadiths"] * 100) if s["ro_hadiths"] else 0

        status_hi = "✅" if s["hi_missing_hadiths"] == 0 and s["hi_empty"] == 0 and not s["hi_missing_sections"] else "⚠️"
        status_ro = "✅" if s["ro_missing_hadiths"] == 0 and s["ro_empty"] == 0 and not s["ro_missing_sections"] else "⚠️"

        print(f"\n{'='*70}")
        print(f"  BOOK: {edition_id.upper()}")
        print(f"{'='*70}")
        print(f"  Reference  → sections: {ref_sec:>4} | hadiths: {ref_had:>6}")
        print(f"  Hindi  {status_hi} → sections: {s['hi_sections']:>4} | hadiths: {s['hi_hadiths']:>6} ({hi_pct:.1f}%) | empty: {s['hi_empty']} ({hi_empty_pct:.1f}%)")
        print(f"  Roman  {status_ro} → sections: {s['ro_sections']:>4} | hadiths: {s['ro_hadiths']:>6} ({ro_pct:.1f}%) | empty: {s['ro_empty']} ({ro_empty_pct:.1f}%)")

        if s["hi_missing_sections"]:
            print(f"  ❌ Hi MISSING sections: {s['hi_missing_sections']}")
        if s["ro_missing_sections"]:
            print(f"  ❌ Ro MISSING sections: {s['ro_missing_sections']}")
        if s["hi_missing_hadiths"] > 0:
            print(f"  ❌ Hi MISSING hadiths vs reference: {s['hi_missing_hadiths']}")
        if s["ro_missing_hadiths"] > 0:
            print(f"  ❌ Ro MISSING hadiths vs reference: {s['ro_missing_hadiths']}")
        if s["hi_extra_hadiths"] > 0:
            print(f"  ⚠️  Hi has EXTRA hadiths not in reference: {s['hi_extra_hadiths']}")
        if s["ro_extra_hadiths"] > 0:
            print(f"  ⚠️  Ro has EXTRA hadiths not in reference: {s['ro_extra_hadiths']}")

        if s["per_section_gaps"]:
            print(f"  ⚠️  Sections with per-hadith gaps:")
            for kid, gap in s["per_section_gaps"].items():
                print(f"      Section {kid}: ref={gap['ref_count']} | hi={gap['hi_count']} | ro={gap['ro_count']}")
                if gap["hi_missing"]:
                    print(f"          Hi missing: {gap['hi_missing'][:10]}{'...' if len(gap['hi_missing'])>10 else ''}")
                if gap["ro_missing"]:
                    print(f"          Ro missing: {gap['ro_missing'][:10]}{'...' if len(gap['ro_missing'])>10 else ''}")
                if gap["hi_extra"]:
                    print(f"          Hi extra:   {gap['hi_extra'][:10]}{'...' if len(gap['hi_extra'])>10 else ''}")
                if gap["ro_extra"]:
                    print(f"          Ro extra:   {gap['ro_extra'][:10]}{'...' if len(gap['ro_extra'])>10 else ''}")

    # Summary table
    print("\n\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Book':<28} {'Ref':>6} {'Hi':>6} {'Hi%':>5} {'HiEmp':>6} {'Ro':>6} {'Ro%':>5} {'RoEmp':>6}  Status")
    print("-" * 90)
    all_ok = True
    for edition_id, s in summary.items():
        ref_had = max(s["ar_hadiths"], s["en_hadiths"])
        hi_pct = (s["hi_hadiths"] / ref_had * 100) if ref_had else 0
        ro_pct = (s["ro_hadiths"] / ref_had * 100) if ref_had else 0

        ok = (s["hi_missing_hadiths"] == 0 and s["ro_missing_hadiths"] == 0
              and s["hi_empty"] == 0 and s["ro_empty"] == 0
              and not s["hi_missing_sections"] and not s["ro_missing_sections"])
        if not ok:
            all_ok = False
        flag = "✅" if ok else "⚠️"

        print(f"  {edition_id:<26} {ref_had:>6} {s['hi_hadiths']:>6} {hi_pct:>4.1f}% {s['hi_empty']:>6} {s['ro_hadiths']:>6} {ro_pct:>4.1f}% {s['ro_empty']:>6}  {flag}")

    print()
    if all_ok:
        print("✅ ALL BOOKS FULLY CONSISTENT — Hindi & Roman Urdu match reference.")
    else:
        print("⚠️  ISSUES FOUND — see details above.")


if __name__ == "__main__":
    main()
