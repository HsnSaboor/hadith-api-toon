#!/usr/bin/env python3
"""Sample 50 random hadith per book and verify data quality across Arabic/English/Urdu."""
import csv, os, random, re, json
from pathlib import Path

BASE = Path("/home/saboor/code/hadith-api-toon/editions")
BOOKS = ["abudawud", "bukhari", "muslim", "ibnmajah", "nasai", "tirmidhi"]
SAMPLE_SIZE = 50

HEADER_RE = re.compile(r"^hadiths\[\d+\]\{(.+)\}:")
CSV_FIELD_NAMES = ["hadithnumber","arabic","grades","reference","international_number","narrator_chain","chapter_intro"]
TR_FIELD_NAMES = ["hadithnumber", "text"]


def parse_toon_csv(filepath, fieldnames):
    """Parse a .toon file. Returns dict of hadith_number -> row dict, or empty dict on failure."""
    records = {}
    if not filepath.exists():
        return records
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")
    if not lines:
        return records
    # skip header line
    start = 0
    for i, line in enumerate(lines):
        if HEADER_RE.match(line.strip()):
            start = i + 1
            break
    reader = csv.reader(lines[start:], quotechar='"', escapechar='\\', skipinitialspace=True)
    for row in reader:
        if not row or len(row) < 2:
            continue
        try:
            hn = int(row[0])
        except ValueError:
            continue
        d = dict(zip(fieldnames, row + [''] * (len(fieldnames) - len(row))))
        records[hn] = d
    return records


def trunc(txt, n=80):
    if not txt:
        return ""
    txt = txt.replace("\n", " ").strip()
    if len(txt) <= n:
        return txt
    return txt[:n] + "..."


def sample_book(book_id):
    print(f"\n{'='*80}")
    print(f"BOOK: {book_id.upper()}")
    print(f"{'='*80}")

    sections_dir = BASE / book_id / "sections"
    en_dir = BASE / book_id / "translations" / "en" / "sections"
    ur_dir = BASE / book_id / "translations" / "ur" / "sections"

    # List section files
    sec_files = sorted(sections_dir.glob("*.toon"), key=lambda p: int(p.stem))
    print(f"\nSection files ({len(sec_files)}): {[p.stem for p in sec_files]}")

    # Collect all hadith numbers
    all_hadiths = {}
    for sf in sec_files:
        records = parse_toon_csv(sf, CSV_FIELD_NAMES)
        for hn, rec in records.items():
            all_hadiths[hn] = {"sec": sf.stem, "arabic": rec}

    if not all_hadiths:
        print("  WARNING: No hadith found!")
        return

    total = len(all_hadiths)
    print(f"Total hadith numbers available: {total}")

    sample_nums = sorted(random.sample(list(all_hadiths.keys()), min(SAMPLE_SIZE, total)))
    print(f"Sampling {len(sample_nums)} hadith: {sample_nums[:5]}...{sample_nums[-3:]}")

    # Read all English and Urdu translations into lookup dicts
    en_all = {}
    for ef in en_dir.glob("*.toon"):
        en_all.update(parse_toon_csv(ef, TR_FIELD_NAMES))
    ur_all = {}
    for uf in ur_dir.glob("*.toon"):
        ur_all.update(parse_toon_csv(uf, TR_FIELD_NAMES))

    results = {
        "sampled": 0,
        "has_arabic": 0,
        "arabic_nonempty": 0,
        "has_english": 0,
        "has_urdu": 0,
        "hn_mismatch": 0,
        "empty_arabic": 0,
        "detail": [],
    }

    for hn in sample_nums:
        info = all_hadiths[hn]
        arabic_rec = info["arabic"]
        arabic_text = arabic_rec.get("arabic", "").strip()

        en_rec = en_all.get(hn)
        ur_rec = ur_all.get(hn)

        results["sampled"] += 1

        # Arabic checks
        if arabic_text:
            results["arabic_nonempty"] += 1
        else:
            results["empty_arabic"] += 1
        results["has_arabic"] += 1

        # Translation presence
        en_text = en_rec.get("text", "").strip() if en_rec is not None else ""
        ur_text = ur_rec.get("text", "").strip() if ur_rec is not None else ""
        if en_text:
            results["has_english"] += 1
        if ur_text:
            results["has_urdu"] += 1

        # HN mismatch checks
        if en_rec is not None and int(en_rec.get("hadithnumber", 0)) != hn:
            results["hn_mismatch"] += 1
            results["detail"].append(f"  HN MISMATCH: #{hn} Arabic vs English #{en_rec.get('hadithnumber')}")
        if ur_rec is not None and int(ur_rec.get("hadithnumber", 0)) != hn:
            results["hn_mismatch"] += 1
            results["detail"].append(f"  HN MISMATCH: #{hn} Arabic vs Urdu #{ur_rec.get('hadithnumber')}")

        # Print sample
        print(f"\n  Hadith #{hn} (section {info['sec']}):")
        print(f"    Arabic:  {trunc(arabic_text, 80)}")
        print(f"    English: {trunc(en_text, 80)}")
        print(f"    Urdu:    {trunc(ur_text, 80)}")

    # Summary
    print(f"\n  --- SUMMARY for {book_id} ---")
    print(f"  Total sampled:                {results['sampled']}")
    print(f"  Had Arabic record:            {results['has_arabic']}")
    print(f"  Arabic text non-empty:        {results['arabic_nonempty']}")
    print(f"  Had English translation:      {results['has_english']}")
    print(f"  Had Urdu translation:         {results['has_urdu']}")
    print(f"  Hadith number mismatches:     {results['hn_mismatch']}")
    print(f"  Empty Arabic texts:           {results['empty_arabic']}")

    if results["detail"]:
        print(f"\n  DISCREPANCIES FOUND ({len(results['detail'])}):")
        for d in results["detail"]:
            print(f"    {d}")

    return results


def main():
    random.seed(42)
    all_results = {}
    for book in BOOKS:
        all_results[book] = sample_book(book)

    print(f"\n\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    total_sampled = sum(r['sampled'] for r in all_results.values())
    total_arabic = sum(r['has_arabic'] for r in all_results.values())
    total_arabic_ne = sum(r['arabic_nonempty'] for r in all_results.values())
    total_en = sum(r['has_english'] for r in all_results.values())
    total_ur = sum(r['has_urdu'] for r in all_results.values())
    total_mismatch = sum(r['hn_mismatch'] for r in all_results.values())
    total_empty = sum(r['empty_arabic'] for r in all_results.values())
    print(f"Books analyzed: {len(BOOKS)}")
    print(f"Total hadith sampled (per book cap 50): {total_sampled}")
    print(f"Total with Arabic records:             {total_arabic}")
    print(f"Total with non-empty Arabic text:      {total_arabic_ne}")
    print(f"Total with English translation:        {total_en}")
    print(f"Total with Urdu translation:           {total_ur}")
    print(f"Total hadith number mismatches:        {total_mismatch}")
    print(f"Total empty Arabic texts:              {total_empty}")
    if total_mismatch > 0 or total_empty > 0:
        print(">>> DISCREPANCIES EXIST <<<")
    else:
        print(">>> ALL CHECKS PASSED <<<")


if __name__ == "__main__":
    main()
