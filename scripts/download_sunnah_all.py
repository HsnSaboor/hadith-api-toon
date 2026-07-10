#!/usr/bin/env python3
"""
Download all hadith books from sunnah.com with per-book translation files.

Output structure:
  sunnah.com-download/
    <book_slug>/
      <lang_code>.json
"""

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://sunnah.com"
DEFAULT_OUT_DIR = "sunnah.com-download"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

LANG_CODE_MAP = {
    "english": "en",
    "arabic": "ar",
    "urdu": "ur",
    "hindi": "hi",
    "indonesian": "id",
    "bangla": "bn",
    "bosnian": "bs",
    "turkish": "tr",
    "russian": "ru",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "malay": "ms",
    "persian": "fa",
    "swahili": "sw",
}

BOOKS_FALLBACK = [
    "bukhari",
    "muslim",
    "nasai",
    "abudawud",
    "tirmidhi",
    "ibnmajah",
    "malik",
    "ahmad",
    "darimi",
    "ibnkhuzayma",
    "ibnhibban",
    "hakim",
    "abdurrazzaq",
    "ibnabishayba",
    "daraqutni",
    "bayhaqi",
    "nasaikubra",
    "adab",
    "shamail",
    "nawawi40",
    "riyadussalihin",
    "mishkat",
    "bulugh",
    "forty",
    "hisn",
    "virtues",
]

REFERENCE_KEYS = {
    "Reference": "reference",
    "In-book reference": "in_book_reference",
    "USC-MSA web (English) reference": "usc_msa_reference",
}


def fetch(session: requests.Session, url: str, retries: int = 3, timeout: int = 20) -> str:
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception:
            if attempt == retries - 1:
                return ""
            time.sleep(1.5 * (attempt + 1))
    return ""


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def discover_books(session: requests.Session) -> List[str]:
    html = fetch(session, f"{BASE_URL}/")
    if not html:
        return BOOKS_FALLBACK[:]
    soup = BeautifulSoup(html, "html.parser")

    slugs: Set[str] = set()

    # Prefer collection cards on homepage
    for a in soup.select("div.collection_title a[href], a.collection_title[href]"):
        href = a.get("href", "").split("?")[0]
        m = re.fullmatch(r"/([a-z0-9-]+)", href)
        if m:
            slugs.add(m.group(1))

    if slugs:
        return sorted(slugs)

    # Fallback: grab obvious collection links
    for a in soup.select("a[href]"):
        href = a.get("href", "").split("?")[0]
        m = re.fullmatch(r"/([a-z0-9-]+)", href)
        if not m:
            continue
        slug = m.group(1)
        if slug in {"about", "contact", "privacy", "terms", "api", "support", "donate", "news"}:
            continue
        if slug in {"searchtips", "developers", "dhulhijjah"}:
            continue
        slugs.add(slug)

    if slugs:
        return sorted(slugs)

    return BOOKS_FALLBACK[:]


def discover_languages(session: requests.Session, book_slug: str) -> List[str]:
    html = fetch(session, f"{BASE_URL}/{book_slug}")
    if not html:
        return ["english"]
    soup = BeautifulSoup(html, "html.parser")
    langs: Set[str] = {"english"}

    for a in soup.select("a[href]"):
        href = a.get("href", "").split("?")[0]
        m = re.match(rf"^/([a-z-]+)/{re.escape(book_slug)}([/:]|$)", href)
        if m:
            langs.add(m.group(1))

    return sorted(langs)


def discover_chapters(session: requests.Session, book_slug: str) -> List[int]:
    html = fetch(session, f"{BASE_URL}/{book_slug}")
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    chapters: Set[int] = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "").split("?")[0]
        m = re.match(rf"^/{re.escape(book_slug)}/(\d+)$", href)
        if m:
            chapters.add(int(m.group(1)))
    return sorted(chapters)


def discover_hadith_ids_from_page(session: requests.Session, book_slug: str) -> List[int]:
    html = fetch(session, f"{BASE_URL}/{book_slug}")
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ids: Set[int] = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "").split("?")[0]
        m = re.match(rf"^/{re.escape(book_slug)}:(\d+)$", href)
        if m:
            ids.add(int(m.group(1)))
    return sorted(ids)


def discover_hadith_ids(session: requests.Session, book_slug: str, chapters: List[int]) -> List[int]:
    ids: Set[int] = set()
    for ch in chapters:
        html = fetch(session, f"{BASE_URL}/{book_slug}/{ch}")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[href]"):
            href = a.get("href", "").split("?")[0]
            m = re.match(rf"^/{re.escape(book_slug)}:(\d+)$", href)
            if m:
                ids.add(int(m.group(1)))
        time.sleep(0.2)
    return sorted(ids)


def build_hadith_url(book_slug: str, hadith_id: int, language: str) -> str:
    if language == "english":
        return f"{BASE_URL}/{book_slug}:{hadith_id}"
    return f"{BASE_URL}/{language}/{book_slug}:{hadith_id}"


def parse_reference_block(text: str) -> Tuple[Dict[str, str], bool]:
    refs: Dict[str, str] = {}
    deprecated = False
    if not text:
        return refs, deprecated

    text = clean_text(text)
    for key, field in REFERENCE_KEYS.items():
        pattern = rf"{re.escape(key)}\s*:\s*(.+?)(?=(Reference|In-book reference|USC-MSA web \(English\) reference)\s*:|$)"
        m = re.search(pattern, text)
        if m:
            value = clean_text(m.group(1))
            if "deprecated numbering scheme" in value:
                deprecated = True
                value = value.replace("(deprecated numbering scheme)", "").strip()
            refs[field] = value

    if "deprecated numbering scheme" in text:
        deprecated = True

    return refs, deprecated


def extract_text_for_language(soup: BeautifulSoup, language: str) -> str:
    selectors = []
    if language == "english":
        selectors = [".english_hadith_full .text_details", ".english_hadith_full", ".english_hadith"]
    elif language == "arabic":
        selectors = [".arabic_hadith_full .text_details", ".arabic_hadith_full", ".arabic_hadith"]
    else:
        selectors = [
            ".text_details",
            ".arabic_hadith_full .text_details",
            ".english_hadith_full .text_details",
        ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = clean_text(el.get_text(" ", strip=True))
            if text:
                return text
    return ""


def scrape_hadith_meta(session: requests.Session, book_slug: str, hadith_id: int) -> Dict[str, str]:
    url = build_hadith_url(book_slug, hadith_id, "english")
    html = fetch(session, url)
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")

    narrator = ""
    narrator_el = soup.select_one(".hadith_narrated")
    if narrator_el:
        narrator = clean_text(narrator_el.get_text(" ", strip=True))

    grade = ""
    grade_el = soup.select_one(".hadith_grade, .grade")
    if grade_el:
        grade = clean_text(grade_el.get_text(" ", strip=True))
        grade = grade.replace("Grade:", "").strip()

    ref_text = ""
    ref_el = soup.select_one(".hadith_reference, .reference")
    if ref_el:
        ref_text = ref_el.get_text(" ", strip=True)
    refs, deprecated = parse_reference_block(ref_text)

    meta = {
        "hadithnumber": str(hadith_id),
        "narrator": narrator,
        "status": grade,
    }
    meta.update(refs)
    if deprecated:
        meta["usc_msa_reference_deprecated"] = True
    return meta


def scrape_hadith_text(
    session: requests.Session, book_slug: str, hadith_id: int, language: str
) -> str:
    url = build_hadith_url(book_slug, hadith_id, language)
    html = fetch(session, url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return extract_text_for_language(soup, language)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_language_file(
    output_dir: str, book_slug: str, lang_code: str, hadiths: List[Dict[str, str]]
) -> None:
    ensure_dir(os.path.join(output_dir, book_slug))
    out_path = os.path.join(output_dir, book_slug, f"{lang_code}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hadiths, f, ensure_ascii=False, indent=2)


def get_lang_code(language: str) -> str:
    if language in LANG_CODE_MAP:
        return LANG_CODE_MAP[language]
    return language[:2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download all sunnah.com books with translations")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="Output directory")
    parser.add_argument(
        "--books",
        default="",
        help="Comma-separated book slugs to download (default: discover all)",
    )
    parser.add_argument("--workers", type=int, default=6, help="Concurrent workers")
    parser.add_argument("--sleep", type=float, default=0.15, help="Delay between requests")
    args = parser.parse_args()

    session = requests.Session()

    if args.books:
        books = [b.strip() for b in args.books.split(",") if b.strip()]
    else:
        books = discover_books(session)

    if not books:
        print("No books discovered. Provide --books explicitly.")
        return

    ensure_dir(args.out)

    for book_slug in books:
        print(f"\n=== {book_slug} ===")
        langs = discover_languages(session, book_slug)
        chapters = discover_chapters(session, book_slug)
        hadith_ids = discover_hadith_ids(session, book_slug, chapters)
        if not hadith_ids:
            hadith_ids = discover_hadith_ids_from_page(session, book_slug)

        print(f"Languages: {', '.join(langs)}")
        print(f"Chapters: {len(chapters)} | Hadiths: {len(hadith_ids)}")

        if not hadith_ids:
            print("No hadith IDs found, skipping.")
            continue

        meta_by_id: Dict[str, Dict[str, str]] = {}
        print("Fetching metadata...")
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(scrape_hadith_meta, session, book_slug, hid): hid for hid in hadith_ids}
            done = 0
            for future in as_completed(futures):
                hid = futures[future]
                try:
                    meta_by_id[str(hid)] = future.result()
                except Exception:
                    meta_by_id[str(hid)] = {"hadithnumber": str(hid)}
                done += 1
                if done % 200 == 0 or done == len(hadith_ids):
                    print(f"  meta {done}/{len(hadith_ids)}")
                time.sleep(args.sleep)

        for language in langs:
            lang_code = get_lang_code(language)
            out_path = os.path.join(args.out, book_slug, f"{lang_code}.json")
            existing: Dict[str, Dict[str, str]] = {}
            if os.path.exists(out_path):
                try:
                    with open(out_path, "r", encoding="utf-8") as f:
                        for item in json.load(f):
                            if "hadithnumber" in item:
                                existing[item["hadithnumber"]] = item
                except Exception:
                    existing = {}

            hadiths_map: Dict[str, Dict[str, str]] = {}
            if existing:
                hadiths_map.update(existing)

            print(f"Fetching {language} text...")
            missing_ids = [hid for hid in hadith_ids if str(hid) not in hadiths_map]
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futures = {
                    ex.submit(scrape_hadith_text, session, book_slug, hid, language): hid
                    for hid in missing_ids
                }
                done = 0
                for future in as_completed(futures):
                    hid = futures[future]
                    hid_str = str(hid)
                    text = ""
                    try:
                        text = future.result()
                    except Exception:
                        text = ""
                    record = dict(meta_by_id.get(hid_str, {"hadithnumber": hid_str}))
                    record["text"] = text
                    hadiths_map[hid_str] = record
                    done += 1
                    if done % 200 == 0 or done == len(missing_ids):
                        print(f"  {language} {done}/{len(missing_ids)}")
                    time.sleep(args.sleep)

            hadiths = [hadiths_map[str(hid)] for hid in hadith_ids]
            write_language_file(args.out, book_slug, lang_code, hadiths)
            print(f"  Wrote {len(hadiths)} to {book_slug}/{lang_code}.json")


if __name__ == "__main__":
    main()
