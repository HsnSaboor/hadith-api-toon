# Hadith API — Toon Format

> In the name of God, who has guided me to do this work

A CDN-optimized, lightweight version of the [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api), converted from 466,000+ JSON files into a sleek `.toon` format.

**Same data. 82% smaller. 185× fewer files.**

---

## Why This Exists

The original [hadith-api](https://github.com/fawazahmed0/hadith-api) by [@fawazahmed0](https://github.com/fawazahmed0) is an incredible open-source project providing free Hadith data in multiple languages. However, its structure has some challenges for modern app development:

| Metric | Original (JSON) | This (Toon) | Improvement |
|--------|----------------|-------------|-------------|
| **Total files** | 466,000+ | 2,525 | **185× fewer** |
| **Total size** | ~997 MB | ~176 MB | **82% smaller** |
| **Largest single file** | 658 KB | 581 KB | 12% smaller raw |
| **Largest file (Brotli)** | 63.5 KB | 62.6 KB | Optimized for CDN |
| **Files per section** | 2 (`.json` + `.min.json`) | 1 (`.toon`) | No duplication |
| **Redundant data** | Grades duplicated across editions | Centralized `grades.toon` | Zero duplication |
| **CSV compatibility** | N/A (nested JSON) | RFC 4180 compliant | Standard library parsing |

### Key Improvements

1. **Fewer files, faster CDN** — 2,525 section files instead of 466,000+ individual hadith files. Each section is a single file, no chunking needed. Even the largest section (5,785 hadiths) compresses to just **62.6 KB with Brotli**.

2. **No redundant data** — The original stores each hadith as both an individual file AND inside a section file. This keeps only section files as the single source of truth.

3. **Centralized grades** — Hadith grades (Sahih, Hasan, Daif, etc.) are extracted from `info.json` into a single `grades.toon` file (67,716 entries) instead of being empty arrays repeated across every edition.

4. **RFC 4180 CSV escaping** — All text values use standard CSV double-quote escaping (`""`), making `.toon` files parseable by any standard CSV library on the frontend.

5. **Multi-language chapter translations** — Chapter/section names in 8 languages (Arabic, Urdu, Bengali, French, Indonesian, Turkish, Russian, Tamil) are consolidated into per-book `chapter_translations.toon` files, enabling instant language switching with a single CDN request.

6. **Consistent with quran-api-toon** — Uses the same `.toon` format as the [quran-api-toon](https://github.com/saboor/quran-api-toon) project, enabling shared parsing logic and tooling across both APIs.

---

## URL Structure

```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/{endpoint}
```

Supports HTTP GET. Files are served directly from the CDN with automatic Gzip/Brotli compression.

---

## Endpoints

### Global Index Files

| File | Description | Example URL |
|------|-------------|-------------|
| `info.toon` | Books list + per-book section metadata | `/info.toon` |
| `grades.toon` | All hadith grades (67,716 entries) | `/grades.toon` |
| `editions.toon` | Edition registry (74 editions) | `/editions.toon` |

### Edition Section Files

```
/editions/{edition-slug}/sections/{sectionNo}.toon
```

**Example — Get Sahih Bukhari, Section 1 (Revelation):**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/eng-bukhari/sections/1.toon
```

### Chapter Translations

```
/editions/{book-key}/chapter_translations.toon
```

**Example — Get Bukhari chapter names in all languages:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/chapter_translations.toon
```

---

## The .toon Format

A compact, human-readable, CSV-like format designed as a lightweight alternative to JSON.

### Schema: Section Files

```toon
metadata:
  section_id: 1
  section_name: Revelation
  hadith_first: 1
  hadith_last: 7
  arabic_first: 1
  arabic_last: 7

hadiths[7]{hadithnumber,text,reference_book,reference_hadith}:
  1,"Narrated 'Umar bin Al-Khattab: ...",1,1
  2,"Narrated 'Aisha: ...",1,2
```

### Schema: Chapter Translations

```toon
chapter_translations[776]{lang,chapter_id,name}:
  ar,1,كِتَابُ بَدْءِ الوَحْيِ
  en,1,Revelation
  ur,1,کتاب الوحی
```

### Schema: Grades

```toon
grades[67716]{book,hadithnumber,grader,grade}:
  bukhari,1,Al-Albani,Sahih
  bukhari,1,Muhammad Muhyi Al-Din Abdul Hamid,Sahih
```

### Parsing Rules

- **Strings** containing `,`, `"`, `:`, `\n`, `\r` are double-quoted with RFC 4180 escaping (`""` for internal quotes)
- **Numbers** are unquoted
- **Null values** are `null` (no quotes)
- **Header line** defines the schema: `section_name[count]{field1,field2,...}:`
- **Data rows** are comma-separated values matching the header order

---

## Editions

74 editions across 9 hadith books and 8+ languages:

| Book | Languages Available |
|------|-------------------|
| Sahih al Bukhari | Arabic (×2), Bengali, English, French, Indonesian, Russian, Tamil, Turkish, Urdu |
| Sahih Muslim | Arabic (×2), Bengali, English, French, Indonesian, Russian, Tamil, Turkish, Urdu |
| Sunan Abu Dawud | Arabic (×2), Bengali, English, French, Indonesian, Russian, Turkish, Urdu |
| Sunan an Nasai | Arabic (×2), Bengali, English, French, Indonesian, Russian, Turkish, Urdu |
| Jami At Tirmidhi | Arabic (×2), Bengali, English, Indonesian, Turkish, Urdu |
| Sunan Ibn Majah | Arabic (×2), Bengali, English, French, Indonesian, Turkish, Urdu |
| Muwatta Malik | Arabic (×2), Bengali, English, French, Indonesian, Turkish, Urdu |
| Forty Hadith of an-Nawawi | Arabic (×2), Bengali, English, French, Indonesian, Turkish |
| Forty Hadith Qudsi | Arabic (×2), Bengali, English, French, Indonesian, Turkish, Russian, Tamil |

> **Note on Arabic editions:** Each book has two Arabic editions. The one without a suffix (e.g., `ara-bukhari`) contains full diacritics (Tashkeel). The one with a `1` suffix (e.g., `ara-bukhari1`) has diacritics removed for easier text searching.

---

## Conversion Scripts

All scripts used to generate this repository are in the `scripts/` directory:

| Script | Purpose |
|--------|---------|
| `convert_info_to_toon.py` | Converts `info.json` → `info.toon` + `grades.toon` |
| `convert_editions_to_toon.py` | Converts `editions.json` → `editions.toon` |
| `convert_section_files.py` | Converts all section JSON files → `.toon` |
| `convert_chapter_translations.py` | Converts chapter translations → per-book `.toon` |
| `validate_toon.py` | Validates all output files for correctness |

---

## Acknowledgments

This project is a conversion of the original [hadith-api](https://github.com/fawazahmed0/hadith-api) by **[@fawazahmed0](https://github.com/fawazahmed0)**. All Hadith data, translations, and metadata belong to the original project and its contributors. This repository only provides an alternative file format optimized for CDN delivery.

Original project: https://github.com/fawazahmed0/hadith-api

---

## Contributing

Found an issue with the conversion? Have a suggestion for improving the `.toon` format? Please open an issue or PR.

If you'd like to contribute new Hadith translations to the underlying data, please contribute to the [original hadith-api repository](https://github.com/fawazahmed0/hadith-api).

---

## License

Same as the original project — [Unlicense](LICENSE). This is free and unencumbered software released into the public domain.
