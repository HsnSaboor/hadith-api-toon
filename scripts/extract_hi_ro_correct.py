#!/usr/bin/env python3
"""
Correct Hi/Ro extractor: maps hadiths by hadees_number into existing section files.

Instead of using Takhreej's kitab_id as the output section file name (which diverges
from our section structure), this script:
  1. Reads the existing reference translation (en or ur) sections to learn which
     hadith numbers belong to which section file.
  2. Maps each Takhreej hadith by its hadees_number into the correct section file.
  3. Writes output to editions/<edition_id>/translations/hi/ and /ro/ matching exactly
     the same section files as the reference translation.

Usage:
    python3 scripts/extract_hi_ro_correct.py <takhreej_key> <edition_id> [--ref en|ur]

Examples:
    python3 scripts/extract_hi_ro_correct.py bukhari  bukhari
    python3 scripts/extract_hi_ro_correct.py maja     ibnmajah
    python3 scripts/extract_hi_ro_correct.py muwatta  malik
    python3 scripts/extract_hi_ro_correct.py mishkat  mishkat
    python3 scripts/extract_hi_ro_correct.py muslim   muslim
    python3 scripts/extract_hi_ro_correct.py nasai    nasai
    python3 scripts/extract_hi_ro_correct.py tirmazi  tirmidhi
"""

import json
import os
import re
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_SOURCE  = "/home/saboor/takhreej-source/hadith"

LANG_CONFIG = {
    "hi": {"language_id": 3, "language_name": "Hindi"},
    "ro": {"language_id": 4, "language_name": "Roman Urdu"},
}


def yaml_like(d: dict, indent: int = 0) -> str:
    lines = []
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{k}:")
            lines.append(yaml_like(v, indent + 1))
        else:
            lines.append(f'{prefix}{k}: "{v}"')
    return "\n".join(lines) + "\n"


def load_records(jsonl_path: str) -> list:
    """Load all records from Takhreej JSONL."""
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_ref_section_map(ref_sec_dir: str) -> dict:
    """
    Build a mapping: hadithnumber_str → section_file_stem
    from existing reference translation section files (en or ur).
    Returns: {hadithnumber_str: section_stem}
    """
    number_to_section = {}
    if not os.path.isdir(ref_sec_dir):
        return number_to_section

    for fname in os.listdir(ref_sec_dir):
        if not fname.endswith(".toon"):
            continue
        section_stem = fname.replace(".toon", "")
        path = os.path.join(ref_sec_dir, fname)
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    hn = str(rec.get("hadithnumber", "")).strip()
                    if hn:
                        number_to_section[hn] = section_stem
                except json.JSONDecodeError:
                    pass
    return number_to_section


def build_section_map_from_arabic(ar_sec_dir: str) -> dict:
    """
    Fall back: build hadith-number → section map from the Arabic main sections.
    Arabic sections use a custom toon format with a header line:
      hadiths[count]{hadithnumber,...}:
      1,"arabic text",...
    """
    number_to_section = {}
    if not os.path.isdir(ar_sec_dir):
        return number_to_section

    for fname in os.listdir(ar_sec_dir):
        if not fname.endswith(".toon"):
            continue
        section_stem = fname.replace(".toon", "")
        path = os.path.join(ar_sec_dir, fname)
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        # Skip header line
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            # First field before comma is hadithnumber
            # Handle quoted fields too
            # Split on first comma
            hn = line.split(",")[0].strip().strip('"')
            if hn and hn != "hadithnumber":
                number_to_section[hn] = section_stem
    return number_to_section


def write_hi_ro(records: list, edition_dir: str, number_to_section: dict, ref_sections: set,
                lang_code: str, lang_id: int, lang_name: str) -> dict:
    """
    Write Hi or Ro translation section files, mapped by hadithnumber.
    Hadiths not found in number_to_section go into a 'unmapped.toon' for debugging.
    """
    out_dir = os.path.join(edition_dir, "translations", lang_code, "sections")
    meta_dir = os.path.join(edition_dir, "translations", lang_code)
    os.makedirs(out_dir, exist_ok=True)

    # Group records by target section
    by_section = defaultdict(list)
    unmapped = []
    total = 0
    empty = 0

    for rec in records:
        hn = str(rec.get("hadees_number", "")).strip()
        text = ""
        for t in rec.get("translations", []):
            if t.get("language_id") == lang_id:
                text = (t.get("hadees") or "").strip()
                break

        entry = {"hadithnumber": hn, "text": text}
        total += 1
        if not text:
            empty += 1

        section = number_to_section.get(hn)
        if section:
            by_section[section].append(entry)
        else:
            # Try integer match (e.g., "1" matches "1.0" or vice versa)
            found = False
            # Check if it's a decimal sub-hadith like "1161.2" → might map to "1161"
            # or integer version might be in number_to_section
            hn_int = hn.split(".")[0] if "." in hn else None
            if hn_int and hn_int in number_to_section:
                by_section[number_to_section[hn_int]].append(entry)
                found = True
            if not found:
                unmapped.append(entry)

    # Write each section file
    written_sections = 0
    for sec_stem, entries in by_section.items():
        # Sort by hadithnumber
        entries.sort(key=lambda x: float(x["hadithnumber"]) if x["hadithnumber"].replace(".", "", 1).isdigit() else 0)
        lines = [json.dumps(e, ensure_ascii=False) for e in entries]
        out_path = os.path.join(out_dir, f"{sec_stem}.toon")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        written_sections += 1

    # Write empty placeholder files for sections in ref that have no hi/ro hadiths
    for ref_sec in ref_sections:
        if ref_sec not in by_section:
            out_path = os.path.join(out_dir, f"{ref_sec}.toon")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("")  # Empty section
            written_sections += 1

    # Write unmapped for debugging
    if unmapped:
        unmap_path = os.path.join(out_dir, "_unmapped.toon")
        with open(unmap_path, "w", encoding="utf-8") as f:
            for e in unmapped:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # Write metadata.toon
    meta = {"metadata": {
        "language": lang_code,
        "language_name": lang_name,
        "total_hadiths": str(total),
        "source": "takhreej-source",
    }}
    with open(os.path.join(meta_dir, "metadata.toon"), "w", encoding="utf-8") as f:
        f.write(yaml_like(meta))

    return {
        "total": total,
        "empty": empty,
        "sections": written_sections,
        "unmapped": len(unmapped),
    }


def update_info_toon(edition_dir: str, new_langs: list):
    info_path = os.path.join(edition_dir, "info.toon")
    if not os.path.exists(info_path):
        return None
    with open(info_path, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'available_languages:\s*"([^"]*)"', content)
    if not m:
        return None
    current = set(x for x in m.group(1).split(",") if x)
    updated = sorted(current | set(new_langs))
    new_val = ",".join(updated)
    content = re.sub(r'available_languages:\s*"[^"]*"', f'available_languages: "{new_val}"', content)
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(content)
    return new_val


def find_best_ref(edition_dir: str) -> tuple:
    """Find the best reference translation to use for section mapping."""
    # Prefer: en > ur > ar (main sections)
    for lang in ["en", "ur", "bn", "fr"]:
        sec_dir = os.path.join(edition_dir, "translations", lang, "sections")
        if os.path.isdir(sec_dir) and os.listdir(sec_dir):
            return lang, sec_dir
    return "ar", os.path.join(edition_dir, "sections")


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <takhreej_key> <edition_id> [--ref en|ur|ar]")
        sys.exit(1)

    takhreej_key = sys.argv[1]
    edition_id   = sys.argv[2]
    force_ref    = None
    if "--ref" in sys.argv:
        idx = sys.argv.index("--ref")
        force_ref = sys.argv[idx + 1]

    jsonl_path  = os.path.join(RAW_SOURCE, f"{takhreej_key}.jsonl")
    edition_dir = os.path.join(REPO_ROOT, "editions", edition_id)

    if not os.path.exists(jsonl_path):
        print(f"ERROR: {jsonl_path} not found")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"Extracting Hi/Ro (correct): {takhreej_key} → {edition_id}")
    print(f"{'='*60}")

    # Determine reference
    if force_ref:
        ref_lang  = force_ref
        if force_ref == "ar":
            ref_sec_dir = os.path.join(edition_dir, "sections")
        else:
            ref_sec_dir = os.path.join(edition_dir, "translations", force_ref, "sections")
    else:
        ref_lang, ref_sec_dir = find_best_ref(edition_dir)

    print(f"\n[1] Loading Takhreej records: {jsonl_path}")
    records = load_records(jsonl_path)
    print(f"    → {len(records)} records")

    print(f"\n[2] Building section map from reference ({ref_lang}) ...")
    if ref_lang == "ar":
        number_to_section = build_section_map_from_arabic(ref_sec_dir)
    else:
        number_to_section = load_ref_section_map(ref_sec_dir)
    ref_sections = set(f.replace(".toon", "") for f in os.listdir(ref_sec_dir) if f.endswith(".toon"))
    print(f"    → {len(number_to_section)} hadith numbers mapped across {len(ref_sections)} sections")

    # Check language availability
    lang_ids_found = set()
    for rec in records[:50]:
        for t in rec.get("translations", []):
            lang_ids_found.add(t.get("language_id"))

    has_hi = 3 in lang_ids_found
    has_ro = 4 in lang_ids_found

    if not has_hi and not has_ro:
        print(f"\n❌ No Hindi (lang_id=3) or Roman Urdu (lang_id=4) found in {takhreej_key}!")
        print(f"   Available language_ids: {sorted(lang_ids_found)}")
        sys.exit(1)

    # Create edition dir
    os.makedirs(edition_dir, exist_ok=True)

    langs_added = []

    if has_hi:
        print(f"\n[3] Writing Hindi (hi) ...")
        hi_stats = write_hi_ro(records, edition_dir, number_to_section, ref_sections, "hi", 3, "Hindi")
        print(f"    → {hi_stats['sections']} sections | {hi_stats['total']} hadiths | {hi_stats['empty']} empty | {hi_stats['unmapped']} unmapped")
        langs_added.append("hi")
    else:
        print(f"\n[3] Skipping Hindi — not in source")

    if has_ro:
        print(f"\n[4] Writing Roman Urdu (ro) ...")
        ro_stats = write_hi_ro(records, edition_dir, number_to_section, ref_sections, "ro", 4, "Roman Urdu")
        print(f"    → {ro_stats['sections']} sections | {ro_stats['total']} hadiths | {ro_stats['empty']} empty | {ro_stats['unmapped']} unmapped")
        langs_added.append("ro")
    else:
        print(f"\n[4] Skipping Roman Urdu — not in source")

    print(f"\n[5] Updating info.toon available_languages ...")
    new_val = update_info_toon(edition_dir, langs_added)
    if new_val:
        print(f"    → available_languages: {new_val}")
    else:
        print(f"    → info.toon not updated (not found or no available_languages field)")

    print(f"\n✅ Done: {edition_id}")
    if has_hi:
        print(f"   Hindi:      editions/{edition_id}/translations/hi/ ({hi_stats['total']} hadiths, {hi_stats['unmapped']} unmapped)")
    if has_ro:
        print(f"   Roman Urdu: editions/{edition_id}/translations/ro/ ({ro_stats['total']} hadiths, {ro_stats['unmapped']} unmapped)")


if __name__ == "__main__":
    sys.exit(main())
