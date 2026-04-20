#!/usr/bin/env python3
"""
Full clean rebuild of ALL translations from hadith-new source.

KEY INSIGHT: Uses EXACT hadith number membership from Arabic section files
(not boundary ranges) to place each translated hadith into the correct section.
This correctly handles:
  - Overlapping sections (e.g. ibnmajah section 0+1 both span 1-4345)
  - Section 0 (skipped — it's a catch-all/duplicate in some books)
  - Decimal sub-hadiths (402.2 goes into the section containing 402)
  - Hadith 0 (intro text, prepended to section 1)

Usage:
    python3 scripts/rebuild_all_from_hadith_new.py [--dry-run] [--force]
"""

import json
import os
import sys
import re
import shutil

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HADITH_NEW = os.path.join(BASE_DIR, "hadith-new", "editions")
EDITIONS   = os.path.join(BASE_DIR, "editions")
ROOT_INFO  = os.path.join(BASE_DIR, "info.toon")

LANG_MAP = {
    "ara": "ar", "ben": "bn", "eng": "en", "fra": "fr",
    "ind": "id", "rus": "ru", "tam": "ta", "tur": "tr", "urd": "ur",
}
LANG_NAMES   = {"ar":"Arabic","bn":"Bengali","en":"English","fr":"French",
                "id":"Indonesian","ru":"Russian","ta":"Tamil","tr":"Turkish","ur":"Urdu"}
LANG_SCRIPTS = {"ar":"Arabic","bn":"Bengali","en":"Latin","fr":"Latin",
                "id":"Latin","ru":"Cyrillic","ta":"Tamil","tr":"Latin","ur":"Arabic"}

DRY_RUN = "--dry-run" in sys.argv
FORCE   = "--force"   in sys.argv


# ─── Section membership (exact hn list, not range) ───────────────────────────

def get_section_membership(book: str) -> dict:
    """
    Read all sections/*.toon and return:
      {sec_id(int): [hadithnumber(int), ...]} — ordered, de-duplicated.

    Each hn is assigned to the LOWEST section_id that contains it.
    Section 0 is used as fallback (for hadiths only found there).
    Hadiths not in ANY section are appended to section 1 (orphans).
    """
    sec_dir = os.path.join(EDITIONS, book, "sections")
    hn_to_sec = {}    # hn -> first sec_id that owns it
    sec_hns   = {}    # sec_id -> [hn, ...] in file order
    all_nonzero_hns = set()

    fnames = sorted(
        [f for f in os.listdir(sec_dir) if f.endswith(".toon")],
        key=lambda x: int(x.replace(".toon", ""))
    )
    # First pass: collect all non-zero hns
    for fname in fnames:
        sec_id = int(fname.replace(".toon", ""))
        if sec_id == 0:
            continue
        path = os.path.join(sec_dir, fname)
        hns = []
        with open(path, encoding="utf-8") as f:
            in_data = False
            for line in f:
                s = line.rstrip("\r\n")
                if s.startswith("hadiths["):
                    in_data = True; continue
                if not in_data or not s:
                    continue
                try:
                    hn = int(s.split(",")[0])
                    all_nonzero_hns.add(hn)
                    if hn not in hn_to_sec:
                        hn_to_sec[hn] = sec_id
                    hns.append(hn)
                except (ValueError, IndexError):
                    pass
        sec_hns[sec_id] = hns

    # Second pass: section 0 — collect hadiths only found there (not in any other section)
    sec0_path = os.path.join(sec_dir, "0.toon")
    sec0_only_hns = []
    if os.path.exists(sec0_path):
        with open(sec0_path, encoding="utf-8") as f:
            in_data = False
            for line in f:
                s = line.rstrip("\r\n")
                if s.startswith("hadiths["):
                    in_data = True; continue
                if not in_data or not s:
                    continue
                try:
                    hn = int(s.split(",")[0])
                    if hn not in all_nonzero_hns:
                        sec0_only_hns.append(hn)
                        hn_to_sec[hn] = 0
                except (ValueError, IndexError):
                    pass
        if sec0_only_hns:
            sec_hns[0] = sec0_only_hns

    # Find orphans: hadiths the source has that aren't in ANY section
    # We'll add them to section 1 (or the first available section)
    # This is handled at write-time by checking each source hn against hn_to_sec

    # Deduplicate: each section keeps only hns it owns
    deduped = {}
    for sec_id, hns in sec_hns.items():
        owned = [hn for hn in hns if hn_to_sec.get(hn) == sec_id]
        if owned:
            deduped[sec_id] = owned

    return deduped, hn_to_sec


# ─── Source loading ───────────────────────────────────────────────────────────

def load_source(book: str, lang_prefix: str) -> list:
    path = os.path.join(HADITH_NEW, f"{lang_prefix}-{book}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["hadiths"]


def build_hadith_map(hadiths: list) -> dict:
    """
    Returns two structures:
      int_map   : {int_floor -> [(hn_raw, text), ...]}   sorted by hn_raw float
      hadith_zero: [(hn_raw, text)] for hn==0 entries (intro text), or []
    """
    int_map     = {}
    hadith_zero = []
    for h in hadiths:
        hn_raw = h["hadithnumber"]
        text   = h.get("text", "")
        hn_float = float(str(hn_raw))
        if hn_float == 0:
            hadith_zero.append((hn_raw, text))
            continue
        floor_hn = int(hn_float)
        if floor_hn not in int_map:
            int_map[floor_hn] = []
        int_map[floor_hn].append((hn_raw, text))
    # Sort sub-entries by float value so 402 comes before 402.2
    for k in int_map:
        int_map[k].sort(key=lambda x: float(str(x[0])))
    return int_map, hadith_zero


# ─── Writing ─────────────────────────────────────────────────────────────────

def write_translation_sections(book: str, lang: str,
                                int_map: dict, hadith_zero: list,
                                section_membership: dict,
                                hn_to_sec: dict) -> tuple:
    """
    Write one JSONL .toon per section, placing each hadith in its correct section.
    Decimal sub-hadiths (402.2) follow their integer parent (402) in the same section.
    Hadith 0 (intro) is prepended to first section. Orphaned hadiths also go there.
    """
    out_base = os.path.join(EDITIONS, book, "translations", lang, "sections")
    if not DRY_RUN:
        os.makedirs(out_base, exist_ok=True)

    # Collect orphans: source hadiths whose integer floor isn't in any section
    known_hns = set(hn_to_sec.keys())
    orphans = []
    for hn_int, entries in sorted(int_map.items()):
        if hn_int not in known_hns:
            for hn_raw, text in entries:
                orphans.append({"hadithnumber": str(hn_raw), "text": text})

    written_s = written_h = missing_h = 0
    first_section = True
    first_sec_id = min(section_membership.keys()) if section_membership else 1

    for sec_id in sorted(section_membership.keys()):
        hns = section_membership[sec_id]
        rows = []

        # Intro hadith (hn==0) + orphans go at top of first section
        if first_section:
            for hn_raw, text in hadith_zero:
                if str(text).strip():
                    rows.append({"hadithnumber": str(hn_raw), "text": text})
            rows.extend(orphans)
        first_section = False

        for hn in hns:
            entries = int_map.get(hn)
            if entries:
                for hn_raw, text in entries:
                    rows.append({"hadithnumber": str(hn_raw), "text": text})
            else:
                missing_h += 1

        if not rows:
            continue

        if not DRY_RUN:
            out_path = os.path.join(out_base, f"{sec_id}.toon")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")

        written_s += 1
        written_h += len(rows)

    return written_s, written_h, missing_h


def write_metadata(book: str, lang: str, total: int):
    out_path = os.path.join(EDITIONS, book, "translations", lang, "metadata.toon")
    content = (
        f"metadata:\n"
        f"  language: {lang}\n"
        f"  language_name: {LANG_NAMES.get(lang, lang)}\n"
        f"  script: {LANG_SCRIPTS.get(lang, 'Latin')}\n"
        f"  total_hadiths: {total}\n"
        f'  source: "hadith-new"\n'
    )
    if not DRY_RUN:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)


def delete_existing_translation(book: str, lang: str):
    path = os.path.join(EDITIONS, book, "translations", lang)
    if os.path.isdir(path):
        if not DRY_RUN:
            shutil.rmtree(path)
        return True
    return False


# ─── Metadata updates ─────────────────────────────────────────────────────────

def update_book_info_toon(book: str, all_langs: list):
    info_path = os.path.join(EDITIONS, book, "info.toon")
    if not os.path.exists(info_path):
        return
    with open(info_path, encoding="utf-8") as f:
        content = f.read()
    lang_str = ",".join(sorted(all_langs))
    pattern = r'(  available_languages:\s*")([^"]*?)(")'
    new_content, n = re.subn(pattern, lambda m: m.group(1) + lang_str + m.group(3), content)
    if n and not DRY_RUN:
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(new_content)


def update_root_info_toon(book: str, all_langs: list):
    if not os.path.exists(ROOT_INFO):
        return
    with open(ROOT_INFO, encoding="utf-8") as f:
        lines = f.readlines()
    lang_str = ",".join(sorted(all_langs))
    new_lines = []
    for line in lines:
        stripped = line.rstrip("\r\n").lstrip()
        if stripped.startswith(book + ","):
            prefix = "  " if line.startswith("  ") else ""
            parts, current, in_q = [], "", False
            for ch in stripped:
                if ch == '"': in_q = not in_q; current += ch
                elif ch == "," and not in_q: parts.append(current); current = ""
                else: current += ch
            parts.append(current)
            if len(parts) >= 4:
                parts[3] = f'"{lang_str}"'
                new_lines.append(prefix + ",".join(parts) + "\n")
                continue
        new_lines.append(line)
    if not DRY_RUN:
        with open(ROOT_INFO, "w", encoding="utf-8") as f:
            f.writelines(new_lines)


# ─── Discovery ────────────────────────────────────────────────────────────────

def get_all_sources() -> dict:
    sources = {}
    for fname in os.listdir(HADITH_NEW):
        if not fname.endswith(".json") or fname.endswith(".min.json"):
            continue
        name = fname.replace(".json", "")
        if name.endswith("1"):
            continue
        parts = name.split("-", 1)
        if len(parts) != 2:
            continue
        lang_prefix, book = parts
        if lang_prefix == "ara":
            continue
        lang = LANG_MAP.get(lang_prefix)
        if not lang:
            continue
        if book not in sources:
            sources[book] = {}
        sources[book][lang] = lang_prefix
    return sources


def get_existing_langs(book: str) -> list:
    tpath = os.path.join(EDITIONS, book, "translations")
    return sorted(os.listdir(tpath)) if os.path.isdir(tpath) else []


# ─── Verification ─────────────────────────────────────────────────────────────

def verify_all(sources: dict):
    """Post-rebuild: verify every (book, lang) pair against source."""
    print("\n" + "="*60)
    print("POST-BUILD VERIFICATION")
    print("="*60)
    errors = []
    ok_count = 0
    for book in sorted(sources.keys()):
        for lang in sorted(sources[book].keys()):
            lang_prefix = sources[book][lang]
            src_hadiths = load_source(book, lang_prefix)
            # Build string-key map for comparison
            src_map = {str(h["hadithnumber"]): h.get("text","") for h in src_hadiths}

            sec_dir = os.path.join(EDITIONS, book, "translations", lang, "sections")
            if not os.path.isdir(sec_dir):
                errors.append(f"  MISSING  {book}/{lang}: no sections dir")
                continue

            toon_map = {}
            for fname in os.listdir(sec_dir):
                with open(os.path.join(sec_dir, fname), encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        try:
                            obj = json.loads(line)
                            toon_map[obj["hadithnumber"]] = obj["text"]
                        except: pass

            missing = [k for k in src_map if k not in toon_map and src_map[k].strip()]
            if missing:
                errors.append(f"  MISSING_HNS {book}/{lang}: {missing[:5]}")
            else:
                ok_count += 1
                print(f"  OK  {book}/{lang}: {len(src_map)} src == {len(toon_map)} toon")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors: print(e)
    else:
        print(f"\n✓ All {ok_count} pairs verified. Zero missing hadiths.")
    return len(errors) == 0


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if DRY_RUN:
        print("=== DRY RUN ===\n")

    sources = get_all_sources()
    total_sections = total_hadiths = replaced = 0
    errors = []

    for book in sorted(sources.keys()):
        book_langs = sources[book]
        existing   = get_existing_langs(book)
        keep_langs = [l for l in existing if l not in book_langs]

        print(f"\n{'='*60}")
        print(f"BOOK: {book}")

        if not os.path.isdir(os.path.join(EDITIONS, book, "sections")):
            print(f"  ⚠ SKIP — no sections/ dir")
            continue

        # Build section membership once per book (shared for all langs)
        membership, hn_to_sec = get_section_membership(book)
        print(f"  Sections (non-zero, deduped): {sorted(membership.keys())[:8]}... "
              f"({len(membership)} total)")

        rebuilt_langs = []
        for lang, lang_prefix in sorted(book_langs.items()):
            print(f"\n  ▶ {lang_prefix} → {lang}")
            try:
                hadiths = load_source(book, lang_prefix)
            except FileNotFoundError as e:
                errors.append(f"{book}/{lang}: {e}"); continue

            int_map, hadith_zero = build_hadith_map(hadiths)

            # Delete old
            if lang in existing:
                if delete_existing_translation(book, lang):
                    replaced += 1

            s, h, miss = write_translation_sections(
                book, lang, int_map, hadith_zero, membership, hn_to_sec
            )
            write_metadata(book, lang, len(hadiths))
            print(f"    {s} sections, {h} hadiths written, {miss} hns not in source")
            total_sections += s; total_hadiths += h
            rebuilt_langs.append(lang)

        final_langs = sorted(set(["ar"] + keep_langs + rebuilt_langs))
        update_book_info_toon(book, final_langs)
        update_root_info_toon(book, final_langs)
        print(f"\n  available_languages → {final_langs}")

    print(f"\n\n{'='*60}")
    print(f"DONE: {total_sections} section files, {total_hadiths} hadiths")
    if errors:
        print("ERRORS:"); [print(f"  {e}") for e in errors]

    # Auto-verify after write
    if not DRY_RUN:
        verify_all(sources)


if __name__ == "__main__":
    main()
