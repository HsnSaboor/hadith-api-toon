#!/usr/bin/env python3
"""
Generic extractor: Hindi + Roman Urdu from takhreej JSONL → edition toon sections.

Usage:
    python3 scripts/extract_hi_ro_book.py <takhreej_key> <edition_id>

Examples:
    python3 scripts/extract_hi_ro_book.py bukhari bukhari
    python3 scripts/extract_hi_ro_book.py maja ibnmajah
    python3 scripts/extract_hi_ro_book.py muwatta malik

Outputs:
    editions/<edition_id>/translations/hi/metadata.toon
    editions/<edition_id>/translations/hi/sections/<kitab_id>.toon
    editions/<edition_id>/translations/ro/metadata.toon
    editions/<edition_id>/translations/ro/sections/<kitab_id>.toon
    (also updates available_languages in editions/<edition_id>/info.toon)
"""

import json
import os
import re
import sys

REPO_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_SOURCE   = "/home/saboor/takhreej-source/hadith"

LANG_CONFIG = {
    "hi": {"language_id": 3, "language_name": "Hindi",      "field": "hindi"},
    "ro": {"language_id": 4, "language_name": "Roman Urdu", "field": "roman"},
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


def write_toon_sections(records: list, edition_dir: str, lang_code: str, lang_id: int, lang_name: str) -> dict:
    out_dir = os.path.join(edition_dir, "translations", lang_code, "sections")
    meta_dir = os.path.join(edition_dir, "translations", lang_code)
    os.makedirs(out_dir, exist_ok=True)

    # Group by kitab_id
    kitab_groups: dict = {}
    for rec in records:
        kid = rec.get("kitab_id", 0)
        kitab_groups.setdefault(kid, []).append(rec)

    total = 0
    empty = 0
    written_sections = 0

    for kid in sorted(kitab_groups.keys()):
        section_recs = kitab_groups[kid]
        lines = []
        for rec in section_recs:
            text = ""
            for t in rec.get("translations", []):
                if t.get("language_id") == lang_id:
                    text = (t.get("hadees") or "").strip()
                    break
            entry = {"hadithnumber": str(rec["hadees_number"]), "text": text}
            lines.append(json.dumps(entry, ensure_ascii=False))
            total += 1
            if not text:
                empty += 1

        out_path = os.path.join(out_dir, f"{kid}.toon")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        written_sections += 1

    # metadata.toon
    meta = {"metadata": {
        "language": lang_code,
        "language_name": lang_name,
        "total_hadiths": str(total),
        "source": "takhreej-source",
    }}
    with open(os.path.join(meta_dir, "metadata.toon"), "w", encoding="utf-8") as f:
        f.write(yaml_like(meta))

    return {"total": total, "empty": empty, "sections": written_sections}


def update_info_toon(edition_dir: str, new_langs: list):
    info_path = os.path.join(edition_dir, "info.toon")
    if not os.path.exists(info_path):
        return
    with open(info_path, encoding="utf-8") as f:
        content = f.read()

    m = re.search(r'available_languages:\s*"([^"]*)"', content)
    if not m:
        return

    current = set(m.group(1).split(","))
    updated = sorted(current | set(new_langs))
    new_val = ",".join(updated)
    content = re.sub(r'available_languages:\s*"[^"]*"',
                     f'available_languages: "{new_val}"', content)
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(content)
    return new_val


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <takhreej_key> <edition_id>")
        sys.exit(1)

    takhreej_key = sys.argv[1]
    edition_id   = sys.argv[2]

    jsonl_path   = os.path.join(RAW_SOURCE, f"{takhreej_key}.jsonl")
    edition_dir  = os.path.join(REPO_ROOT, "editions", edition_id)

    # Validate
    if not os.path.exists(jsonl_path):
        print(f"ERROR: {jsonl_path} not found")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"Extracting Hi/Ro: {takhreej_key} → {edition_id}")
    print(f"{'='*60}")

    # Load
    print(f"\n[1] Loading {jsonl_path} ...")
    records = load_records(jsonl_path)
    print(f"    → {len(records)} records")

    # Create edition dir if it doesn't exist (for books with no existing edition)
    os.makedirs(edition_dir, exist_ok=True)

    # Extract Hindi
    print(f"\n[2] Writing Hindi (hi) ...")
    hi_stats = write_toon_sections(records, edition_dir, "hi", 3, "Hindi")
    print(f"    → {hi_stats['sections']} sections | {hi_stats['total']} hadiths | {hi_stats['empty']} empty")

    # Extract Roman Urdu
    print(f"\n[3] Writing Roman Urdu (ro) ...")
    ro_stats = write_toon_sections(records, edition_dir, "ro", 4, "Roman Urdu")
    print(f"    → {ro_stats['sections']} sections | {ro_stats['total']} hadiths | {ro_stats['empty']} empty")

    # Update info.toon
    print(f"\n[4] Updating info.toon available_languages ...")
    new_langs_val = update_info_toon(edition_dir, ["hi", "ro"])
    if new_langs_val:
        print(f"    → available_languages: {new_langs_val}")
    else:
        print(f"    → info.toon not found or no available_languages field")

    # Summary
    print(f"\n✅ Done: {edition_id}")
    print(f"   Hindi:      editions/{edition_id}/translations/hi/ ({hi_stats['total']} hadiths)")
    print(f"   Roman Urdu: editions/{edition_id}/translations/ro/ ({ro_stats['total']} hadiths)")

    # Write a result JSON for the verifier
    result = {
        "edition_id": edition_id,
        "takhreej_key": takhreej_key,
        "records_loaded": len(records),
        "hi": hi_stats,
        "ro": ro_stats,
    }
    result_path = os.path.join(edition_dir, "translations", "_extract_result.json")
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
