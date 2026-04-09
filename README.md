# Hadith API — Toon Format

> In the name of God, who has guided me to do this work

The most comprehensive multilingual Hadith database on the internet. **25 books, 87,000+ hadiths, 9+ languages** — all in a unified, CDN-optimized `.toon` format.

**Built from:** [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) · [al-hadees.com](https://al-hadees.com) · [sunnah.com](https://sunnah.com) · [hadith-json](https://github.com/AhmedBaset/hadith-json)

---

## Overview

| Metric | Value |
|--------|-------|
| **Books** | 25 |
| **Total Hadiths** | 68,513 |
| **Languages** | Arabic, Urdu, English, Bengali, French, Indonesian, Russian, Tamil, Turkish |
| **Editions** | 94 language editions |
| **Sections** | 623 section files |

Every book is stored in a single directory with **all available languages in one file**. No more fetching separate files for Arabic, Urdu, and English.

---

## The `.toon` Format

`.toon` is a compact, self-describing, CSV-like plain-text format. Each file defines its own schema in the header, so parsers automatically know which columns are present.

### Structure

```toon
metadata:
  section_id: 1
  section_name: Revelation

hadiths[7]{hadithnumber,arabic,urdu,english,bengali,french,indonesian,russian,urdu,grades,reference,international_number,narrator_chain,chapter_intro}:
  1,"حَدَّثَنَا...","آپ صلی اللہ...","Narrated 'Umar...","বাংলা...","Français...","","","","","Sahih","Book 1, Hadith 1",1,"Umar → ...",""
  2,"حَدَّثَنَا...","آپ صلی اللہ...","Narrated 'Aisha...","বাংলা...","Français...","","","","","Sahih","Book 1, Hadith 2",2,"Aisha → ...",""
```

### How It Works

1. **`metadata:` block** — Key-value pairs describing the section (ID, name, hadith range).
2. **Header line** — `hadiths[N]{col1,col2,...}:` defines the column names and row count.
3. **Data rows** — Comma-separated values matching the header order. RFC 4180 CSV escaping (`""` for internal quotes, `\n` for newlines).

---

## Dynamic Schema: Three Tiers

The columns in each file change based on which languages are available for that book. **Read the header to know which languages are present.**

### Tier 1: Original 9 Books (Full Multilingual)

Books with 9 languages: Arabic, Urdu, English, Bengali, French, Indonesian, Russian, Tamil, Turkish.

```toon
hadiths[7587]{hadithnumber,arabic,bengali,english,french,indonesian,russian,urdu,grades,reference,international_number,narrator_chain,chapter_intro}:
```

**Books:** Bukhari, Muslim, Abu Dawud, Ibn Majah, Malik, Nasai, Tirmidhi, Nawawi 40, Qudsi 40, Dehlawi 40

### Tier 2: 6 Books with Arabic + English

Books where we have complete Arabic + English from hadith-json, but incomplete Urdu (<90% coverage).

```toon
hadiths[4428]{hadithnumber,arabic,english,grades,reference,international_number,narrator_chain,chapter_intro}:
```

**Books:** Musnad Ahmed, Al-Adab Al-Mufrad, Shamail-e-Tirmazi, Mishkat al-Masabih, Bulugh al-Maram

### Tier 3: 9 Rare Books (Arabic + Urdu Only)

Scholarly collections without publicly available English translations.

```toon
hadiths[124]{hadithnumber,arabic,urdu,grades,reference,international_number,narrator_chain,chapter_intro}:
```

**Books:** Bayhaqi, Mustadrak, Sunan Darmi, Silsila Sahiha, Fatah Al-Rabani, Al-Lu'lu wal-Marjan, Muajam Saghir Tabarani, Musannaf Ibn Abi Shaybah, Sahih Ibn Khuzaymah, Sunan al-Daraqutni

---

## Minority Languages

When a language has **< 90% coverage** for a book (e.g., Urdu for Musnad Ahmed), it is stored separately to keep the main file clean:

```
editions/musnad-ahmed/
├── sections/1.toon          ← Core: Arabic + English
└── translations/urdu/sections/
    └── 1.toon               ← Minority: Urdu only
```

Minority files use a simple schema: `hadiths[N]{hadithnumber,text}:`

---

## How to Parse (For Developers)

The key insight: **read the header to discover the columns dynamically**. Don't hardcode column positions.

### JavaScript Example

```js
async function fetchSection(book, sectionId) {
  const url = `https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/${book}/sections/${sectionId}.toon`;
  const text = await fetch(url).then(r => r.text());
  const lines = text.split('\n').filter(l => l.trim());

  // Parse header
  const headerLine = lines.find(l => l.includes('{') && l.includes('}:'));
  const cols = headerLine.match(/\{(.+)\}/)[1].split(',');

  // Parse data rows (skip metadata and header)
  const startIdx = lines.indexOf(headerLine) + 1;
  return lines.slice(startIdx).map(line => {
    const vals = parseCSVLine(line); // Use a proper CSV parser
    const row = {};
    cols.forEach((col, i) => row[col] = vals[i] || '');
    return row;
  });
}

// Usage
const hadiths = await fetchSection('bukhari', '1');
console.log(hadiths[0].arabic);   // Arabic text
console.log(hadiths[0].english);  // English text
console.log(hadiths[0].urdu);     // Urdu text
```

### Python Example

```python
import csv, io, requests

def fetch_section(book, section_id):
    url = f"https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/{book}/sections/{section_id}.toon"
    text = requests.get(url).text
    lines = [l for l in text.split('\n') if l.strip()]

    # Parse header
    header_line = next(l for l in lines if '{' in l and '}:' in l)
    cols = header_line[header_line.index('{')+1:header_line.index('}')].split(',')

    # Parse data rows
    start_idx = lines.index(header_line) + 1
    hadiths = []
    for line in lines[start_idx:]:
        reader = csv.reader(io.StringIO(line))
        vals = next(reader)
        hadiths.append(dict(zip(cols, vals)))
    return hadiths

# Usage
hadiths = fetch_section('bukhari', '1')
print(hadiths[0]['arabic'])
print(hadiths[0]['english'])
```

### Parsing Rules

| Rule | Detail |
|------|--------|
| **CSV escaping** | RFC 4180 — use `""` for internal quotes, `\n` for newlines |
| **Empty values** | Empty string `""` or nothing between commas |
| **Numbers** | Unquoted integers |
| **Metadata** | Lines starting with `  ` (2 spaces) under `metadata:` |
| **Header** | `hadiths[N]{col1,col2,...}:` — N = row count |

---

## CDN Usage

```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/{endpoint}
```

### Global Index

| File | Description |
|------|-------------|
| [`editions.toon`](https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions.toon) | 25 books with available languages |
| [`info.toon`](https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon) | Per-book section metadata |

### Section Files

```
/editions/{book}/sections/{sectionNo}.toon
```

**Example — Sahih Bukhari, Section 1:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/sections/1.toon
```

### Minority Language Files

```
/editions/{book}/translations/{lang}/sections/{sectionNo}.toon
```

**Example — Musnad Ahmed Urdu translations:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/musnad-ahmed/translations/urdu/sections/1.toon
```

---

## Books

| # | Book | Languages | Hadiths |
|---|------|-----------|---------|
| 1 | Sahih al-Bukhari | ar, bn, en, fr, id, ru, ur | 12,642 |
| 2 | Sahih Muslim | ar, bn, en, fr, id, ru, ur | 12,272 |
| 3 | Sunan Abu Dawud | ar, bn, en, fr, id, ru, ur | 5,322 |
| 4 | Sunan an-Nasai | ar, bn, en, fr, id, ur | 6,250 |
| 5 | Sunan Ibn Majah | ar, bn, en, fr, id, ur | 8,455 |
| 6 | Jami At-Tirmidhi | ar, bn, en, id, ur | 5,543 |
| 7 | Muwatta Malik | ar, bn, en, fr, id, ur | 2,904 |
| 8 | Musnad Ahmed | ar, bn, en, fr, id, ur | 1,389 |
| 9 | Mishkat al-Masabih | ar, bn, en, fr, id, ur | 4,428 |
| 10 | Al-Adab Al-Mufrad | ar, bn, en, fr, id, ur | 1,326 |
| 11 | Bulugh al-Maram | ar, bn, en, fr, id, ur | 1,767 |
| 12 | Shamail-e-Tirmazi | ar, bn, en, fr, id, ur | 402 |
| 13 | Sunan ad-Darimi | ar, bn, en, fr, id, ur | 4,055 |
| 14 | Al-Mustadrak | ar, ur | 667 |
| 15 | Sunan al-Daraqutni | ar, ur | 218 |
| 16 | Musannaf Ibn Abi Shaybah | ar, ur | 263 |
| 17 | Sahih Ibn Khuzaymah | ar, ur | 49 |
| 18 | Muajam Saghir Tabarani | ar, ur | 25 |
| 19 | Fatah Al-Rabani | ar, ur | 192 |
| 20 | Silsila Sahiha | ar, ur | 51 |
| 21 | Al-Lu'lu wal-Marjan | ar, ur | 47 |
| 22 | Bayhaqi | ar, ur | 124 |
| 23 | Forty Hadith an-Nawawi | ar, bn, en, fr, tr | 42 |
| 24 | Forty Hadith Qudsi | ar, en, fr | 40 |
| 25 | Forty Hadith Dehlawi | ar, en, fr | 40 |

---

## Data Sources

| Source | Contribution |
|--------|-------------|
| [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) | Original 9 books, base structure |
| [al-hadees.com](https://al-hadees.com) | Arabic + Urdu for all 25 books |
| [sunnah.com](https://sunnah.com) | English for 6 books |
| [AhmedBaset/hadith-json](https://github.com/AhmedBaset/hadith-json) | Complete Arabic + English for 6 books |

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
