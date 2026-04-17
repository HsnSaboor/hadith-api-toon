# Hadith API — Toon Format

> In the name of God, who has guided me to do this work

The most comprehensive multilingual Hadith database on internet. **25 books, 68,513 hadiths, 8 languages** — all in unified, CDN-optimized `.toon` format.

**Built from:** [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) · [al-hadees.com](https://al-hadees.com) · [sunnah.com](https://sunnah.com) · [hadith-json](https://github.com/AhmedBaset/hadith-json)

---

## Overview

| Metric | Value |
|--------|-------|
| **Books** | 25 |
| **Total Hadiths** | 68,513 |
| **Languages** | Arabic, Urdu, English, Bengali, French, Indonesian, Russian, Turkish |
| **Collections** | 25 unified books |
| **Sections** | 596 section files |

Every book stored in single directory with **all available languages in one file**. No more fetching separate files for Arabic, Urdu, and English.

Book-level intro + author metadata stored in `editions/{book}/info.toon`.

---

## The `.toon` Format

`.toon` is a compact, self-describing, CSV-like plain-text format. Each file defines its own schema in the header, so parsers automatically know which columns are present.

### Structure

```toon
# editions/{book}/info.toon
metadata:
  book_id: bukhari
  book_name: "Sahih al-Bukhari"
  total_hadiths: 12642
  available_languages: "arabic,bengali,english,french,indonesian,russian,urdu"
  intro: "Book introduction"
  intro_ur: "Book introduction in Urdu"

sections[97]{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}:
  1,"Revelation","بدء الوحي",... ,1,7,1,7

# editions/{book}/sections/1.toon
hadiths[7]{hadithnumber,arabic,bengali,english,french,indonesian,russian,urdu,grades,reference,international_number,narrator_chain,chapter_intro}:
  "1","حَدَّثَنَا...","...","Narrated 'Umar...","...","...","...","...","","","","Narrated 'Umar","Revelation"
  "2","حَدَّثَنَا...","...","Narrated 'Aisha...","...","...","...","...","","","","Narrated 'Aisha","Revelation"
```

### How It Works

1. **Global index** — Root `info.toon` lists books and paths.
2. **Book metadata** — `editions/{book}/info.toon` stores intro + section index.
3. **Section data** — `editions/{book}/sections/{section}.toon` stores hadith rows.
4. **Translation slices** — `editions/{book}/translations/{lang}/sections/{section}.toon` stores `{hadithnumber,text}` JSONL rows.
5. **Dynamic columns** — Parse section header (`hadiths[N]{...}`) before reading rows.

---

## Dynamic Schema: Language Availability

Each book includes all available languages in a single unified file. **Read the header to discover which languages are present.**

### Book Introductions

Each book includes multilingual introductions in per-book metadata file:

```toon
# editions/{book}/info.toon
metadata:
  book_id: bukhari
  book_name: "Sahih al-Bukhari"
  available_languages: "arabic,bengali,english,french,indonesian,russian,urdu"
  intro: "Book introduction in original/source language"
  intro_bn: "Bengali translation"
  intro_fr: "French translation"
  intro_id: "Indonesian translation"
  intro_ru: "Russian translation"
  intro_ur: "Urdu translation"
```

**Language availability varies by book:**
- **Tier 1 (7 languages):** arabic, bengali, english, french, indonesian, russian, urdu — Bukhari, Muslim, Abu Dawud
- **Tier 2 (7 languages in section schema):** arabic, bengali, english, french, indonesian, russian, urdu — Nasai, Ibn Majah, Malik, Musnad Ahmed, Mishkat, Al-Adab, Bulugh, Shamail, Sunan Darmi
- **Tier 3 (7 languages in section schema):** arabic, bengali, english, french, indonesian, russian, urdu — Tirmidhi
- **Tier 4 (2 languages):** arabic, urdu — Mustadrak, Sunan Daraqutni, Musannaf, Sahih Ibn Khuzaymah, Muajam Tabarani, Fatah Al-Rabani, Silsila Sahiha, Lulu wal-Marjan, Bayhaqi
- **Tier 5 (6 languages):** arabic, bengali, english, french, turkish, urdu — Nawawi 40
- **Tier 6 (4 languages):** arabic, english, french, urdu — Qudsi 40, Dehlawi 40

Intro translations exist for each non-arabic language in the book. **Check the metadata in each file to see which intro translations are available.**

---

## How to Parse (For Developers)

The key insight: **read the header to discover the columns dynamically**. Don't hardcode column positions.

### JavaScript Example

```js
async function fetchSection(book, sectionId) {
  const url = `https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@v1.0.0/editions/${book}/sections/${sectionId}.toon`;
  const text = await fetch(url).then(r => r.text());
  const lines = text.split('\n').filter(l => l.trim());

  const headerLine = lines[0];
  const cols = headerLine.match(/\{(.+)\}/)[1].split(',');
  const hadiths = lines.slice(1).map(line => {
    const vals = parseCSVLine(line); // use proper CSV parser
    const row = {};
    cols.forEach((col, i) => (row[col] = vals[i] || ''));
    return row;
  });

  return { columns: cols, hadiths };
}

// Usage
const { hadiths } = await fetchSection('bukhari', '1');
console.log(hadiths[0].arabic);   // Arabic text
console.log(hadiths[0].english);  // English text
```

### Python Example

```python
import csv, io, requests

def fetch_section(book, section_id):
    url = f"https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@v1.0.0/editions/{book}/sections/{section_id}.toon"
    text = requests.get(url).text
    lines = [l for l in text.split('\n') if l.strip()]

    header_line = lines[0]
    cols = header_line[header_line.index('{')+1:header_line.index('}')].split(',')

    hadiths = []
    for line in lines[1:]:
        reader = csv.reader(io.StringIO(line))
        vals = next(reader)
        hadiths.append(dict(zip(cols, vals)))
    return cols, hadiths

# Usage
cols, hadiths = fetch_section('bukhari', '1')
print(hadiths[0]['arabic'])
```

### Read Book Intro Metadata

Book intros and section index live in `editions/{book}/info.toon`, not in section files.

### Parsing Rules

| Rule | Detail |
|------|--------|
| **CSV escaping** | RFC 4180 — use `""` for internal quotes, `\n` for newlines |
| **Empty values** | Empty string `""` or nothing between commas |
| **Numbers** | Unquoted integers |
| **Header** | `hadiths[N]{col1,col2,...}:` — N = row count |
| **Book metadata** | In `editions/{book}/info.toon` under `metadata:` block |
| **Intro fields** | `intro`, `intro_bn`, `intro_fr`, `intro_id`, `intro_ru`, `intro_ur` |

### Parsing Metadata

Per-book `info.toon` metadata block contains intro fields:

```toon
# editions/{book}/info.toon
metadata:
  book_id: bukhari
  intro: "Book introduction text"
  intro_bn: "Bengali intro"
  intro_fr: "French intro"
```

**To parse metadata:**
```js
function parseBookInfoMetadata(text) {
  const lines = text.split('\n');
  const metadata = {};
  let inMetadata = false;
  
  for (const line of lines) {
    if (line.trim() === 'metadata:') {
      inMetadata = true;
      continue;
    }
    if (inMetadata && line.startsWith('sections[')) break;
    if (inMetadata && line.trim()) {
      const match = line.match(/^\s+(\w+):\s*"?(.+?)"?$/);
      if (match) metadata[match[1]] = match[2].replace(/"$/, '');
    }
  }
  return metadata;
}

// Usage
const meta = parseBookInfoMetadata(fileContent);
console.log(meta.intro);      // Original intro
console.log(meta.intro_bn);   // Bengali intro (if available)
console.log(meta.intro_fr);   // French intro (if available)
```

---

## CDN Usage

**Recommended: Use version tags for stability**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@v1.0.0/{endpoint}
```

> **Note on caching:** jsDelivr caches `@main` branch URLs for up to 24 hours. For immediate updates, use version tags (e.g., `@v1.0.0`) or commit hashes.

### Global Index

| File | Description |
|------|-------------|
| [`info.toon`](https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@v1.0.0/info.toon) | 25 books index (`id,name,total_hadiths,available_languages,path`) |

### Per-Book Metadata

| Path | Description |
|------|-------------|
| `/editions/{book}/info.toon` | Book intro, intro translations, section index |

### Section Files

```
/editions/{book}/sections/{sectionNo}.toon
```

**Example — Sahih Bukhari, Section 1:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@v1.0.0/editions/bukhari/sections/1.toon
```

### Index Files

```
info.toon        # All 25 books with section metadata (hadith ranges, section names)
```

### Translation Files

```
/editions/{book}/translations/{lang}/sections/{sectionNo}.toon
```

**Example — Nawawi Urdu, Section 1:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@v1.0.0/editions/nawawi/translations/ur/sections/1.toon
```

**Example — Get all books:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@v1.0.0/info.toon
```

---

## Books

| # | Book | Languages | Hadiths |
|---|------|-----------|---------|
| 1 | Sahih al-Bukhari | ar, bn, en, fr, id, ru, ur | 12,642 |
| 2 | Sahih Muslim | ar, bn, en, fr, id, ru, ur | 12,272 |
| 3 | Sunan Abu Dawud | ar, bn, en, fr, id, ru, ur | 5,322 |
| 4 | Sunan an-Nasai | ar, bn, en, fr, id, ru, ur | 6,250 |
| 5 | Sunan Ibn Majah | ar, bn, en, fr, id, ru, ur | 8,455 |
| 6 | Jami At-Tirmidhi | ar, bn, en, fr, id, ru, ur | 5,543 |
| 7 | Muwatta Malik | ar, bn, en, fr, id, ru, ur | 2,904 |
| 8 | Musnad Ahmed | ar, bn, en, fr, id, ru, ur | 1,389 |
| 9 | Mishkat al-Masabih | ar, bn, en, fr, id, ru, ur | 4,428 |
| 10 | Al-Adab Al-Mufrad | ar, bn, en, fr, id, ru, ur | 1,326 |
| 11 | Bulugh al-Maram | ar, bn, en, fr, id, ru, ur | 1,767 |
| 12 | Shamail-e-Tirmazi | ar, bn, en, fr, id, ru, ur | 402 |
| 13 | Sunan ad-Darimi | ar, bn, en, fr, id, ru, ur | 4,055 |
| 14 | Al-Mustadrak | ar, ur | 667 |
| 15 | Sunan al-Daraqutni | ar, ur | 218 |
| 16 | Musannaf Ibn Abi Shaybah | ar, ur | 263 |
| 17 | Sahih Ibn Khuzaymah | ar, ur | 49 |
| 18 | Muajam Saghir Tabarani | ar, ur | 25 |
| 19 | Fatah Al-Rabani | ar, ur | 192 |
| 20 | Silsila Sahiha | ar, ur | 51 |
| 21 | Al-Lu'lu wal-Marjan | ar, ur | 47 |
| 22 | Bayhaqi | ar, ur | 124 |
| 23 | Forty Hadith an-Nawawi | ar, bn, en, fr, tr, ur | 42 |
| 24 | Forty Hadith Qudsi | ar, en, fr, ur | 40 |
| 25 | Forty Hadith Dehlawi | ar, en, fr, ur | 40 |

---

## Data Sources

| Source | Contribution |
|--------|-------------|
| [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) | Original 9 books, base structure |
| [al-hadees.com](https://al-hadees.com) | Arabic + Urdu for all 25 books |
| [sunnah.com](https://sunnah.com) | English for 6 books |
| [AhmedBaset/hadith-json](https://github.com/AhmedBaset/hadith-json) | Complete Arabic + English for 6 books |
| Google Translate | Automated intro translations for multilingual support |

### Grades and References

- `reference` field lives in section rows for all books: `editions/{book}/sections/{section}.toon`
- `grades.toon` provides detailed scholar grading rows, but only for subset of books
- Empty `grades` values in section rows are normal for many books; use `grades.toon` when book coverage exists

### Intro Translation Details

- All 25 books now have multilingual book introductions
- Translations generated using Google Translate API
- Non-English intros (Urdu) first translated to English, then to other available languages
- Each book's intro fields depend on its available language columns

---

## Conversion Scripts

All scripts used to generate this repository are in `scripts/`:

| Script | Purpose |
|--------|---------|
| `unify_editions.py` | Merges all language editions into unified books |
| `convert_info_to_toon.py` | Converts `info.json` → `info.toon` |
| `convert_editions_to_toon.py` | Converts `editions.json` → `editions.toon` |
| `convert_section_files.py` | Converts section JSON → `.toon` |
| `scrape_quranohadith_fast.py` | Scrapes Arabic + Urdu from al-hadees.com |
| `merge_english_from_hadithjson.py` | Merges English from hadith-json |
| `validate_toon.py` | Validates all `.toon` files |
| `translate_intros_v2.py` | Generates multilingual intro translations |

---

## Acknowledgments

This project is a conversion of the original [hadith-api](https://github.com/fawazahmed0/hadith-api) by **[@fawazahmed0](https://github.com/fawazahmed0)**. All Hadith data, translations, and metadata belong to the original project and its contributors. This repository only provides an alternative file format optimized for CDN delivery.

---

## Contributing

Found an issue with the conversion? Have a suggestion for improving the `.toon` format? Please open an issue or PR.

If you'd like to contribute new Hadith translations to the underlying data, please contribute to the [original hadith-api repository](https://github.com/fawazahmed0/hadith-api).

---

## License

Same as the original project — [Unlicense](LICENSE). This is free and unencumbered software released into the public domain.
