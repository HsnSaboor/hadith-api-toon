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
| **Books** | 25 unified books |
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
  intro: "Sahih al-Bukhari is a collection of hadith compiled by..."
  intro_bn: "সহীহ আল-বুখারি..."
  intro_fr: "Ṣaḥīḥ al-Bukhārī est un recueil..."
  intro_id: "Ṣaḥīḥ al-Bukhārī merupakan kumpulan..."
  intro_ru: "Сахих аль-Бухари представляет..."
  intro_ur: "صحیح البخاری حدیث کا مجموعہ..."

hadiths[7]{hadithnumber,arabic,urdu,english,bengali,french,indonesian,russian,grades,reference,international_number,narrator_chain,chapter_intro}:
  1,"حَدَّثَنَا...","آپ صلی اللہ...","Narrated 'Umar...","বাংলা...","Français...","","","","","Sahih","Book 1, Hadith 1",1,"Umar → ...",""
  2,"حَدَّثَنَا...","آپ صلی اللہ...","Narrated 'Aisha...","বাংলা...","Français...","","","","","Sahih","Book 1, Hadith 2",2,"Aisha → ...",""
```

### How It Works

1. **`metadata:` block** — Key-value pairs describing the section (ID, name, hadith range).
2. **Header line** — `hadiths[N]{col1,col2,...}:` defines the column names and row count.
3. **Data rows** — Comma-separated values matching the header order. RFC 4180 CSV escaping (`""` for internal quotes, `\n` for newlines).

---

## Dynamic Schema: Language Availability

Each book includes all available languages in a single unified file. **Read the header to discover which languages are present.**

### Book Introductions

Each book includes multilingual introductions in the metadata:

```toon
metadata:
  section_id: 1
  intro: "Book introduction in English (or original language)"
  intro_bn: "Bengali translation"
  intro_fr: "French translation"
  intro_id: "Indonesian translation"
  intro_ru: "Russian translation"
  intro_ur: "Urdu translation"
```

**Language availability varies by book:**
- **Tier 1 (7 languages):** arabic, bengali, english, french, indonesian, russian, urdu — Bukhari, Muslim, Abu Dawud
- **Tier 2 (6 languages):** arabic, bengali, english, french, indonesian, urdu — Nasai, Ibn Majah, Malik, Musnad Ahmed, Mishkat, Al-Adab, Bulugh, Shamail, Sunan Darmi
- **Tier 3 (5 languages):** arabic, bengali, english, indonesian, urdu — Tirmidhi
- **Tier 4 (2 languages):** arabic, urdu — Mustadrak, Sunan Daraqutni, Musannaf, Sahih Ibn Khuzaymah, Muajam Tabarani, Fatah Al-Rabani, Silsila Sahiha, Lulu wal-Marjan, Bayhaqi
- **Tier 5 (5 languages):** arabic, bengali, english, french, turkish — Nawawi 40
- **Tier 6 (3 languages):** arabic, english, french — Qudsi 40, Dehlawi 40

Intro translations exist for each non-arabic language in the book. **Check the metadata in each file to see which intro translations are available.**

---

## How to Parse (For Developers)

The key insight: **read the header to discover the columns dynamically**. Don't hardcode column positions.

### JavaScript Example

```js
async function fetchSection(book, sectionId) {
  const url = `https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/${book}/sections/${sectionId}.toon`;
  const text = await fetch(url).then(r => r.text());
  const lines = text.split('\n').filter(l => l.trim());

  // Parse metadata block
  const metadata = {};
  let inMetadata = false;
  for (const line of lines) {
    if (line.trim() === 'metadata:') {
      inMetadata = true;
      continue;
    }
    if (inMetadata && line.startsWith('hadiths')) break;
    if (inMetadata && line.trim()) {
      const match = line.match(/^\s+(\w+):\s*"(.+)"$/);
      if (match) metadata[match[1]] = match[2];
    }
  }

  // Parse header
  const headerLine = lines.find(l => l.includes('{') && l.includes('}:'));
  const cols = headerLine.match(/\{(.+)\}/)[1].split(',');

  // Parse data rows (skip metadata and header)
  const startIdx = lines.indexOf(headerLine) + 1;
  return { metadata, hadiths: lines.slice(startIdx).map(line => {
    const vals = parseCSVLine(line); // Use a proper CSV parser
    const row = {};
    cols.forEach((col, i) => row[col] = vals[i] || '');
    return row;
  })};
}

// Usage
const { metadata, hadiths } = await fetchSection('bukhari', '1');
console.log(metadata.intro);      // Original intro
console.log(metadata.intro_bn);   // Bengali intro (if available)
console.log(metadata.intro_fr);   // French intro (if available)
console.log(hadiths[0].arabic);   // Arabic text
console.log(hadiths[0].english);  // English text
```

### Python Example

```python
import csv, io, requests, re

def fetch_section(book, section_id):
    url = f"https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/{book}/sections/{section_id}.toon"
    text = requests.get(url).text
    lines = [l for l in text.split('\n') if l.strip()]

    # Parse metadata
    metadata = {}
    in_metadata = False
    for line in lines:
        if line.strip() == 'metadata:':
            in_metadata = True
            continue
        if in_metadata and line.startswith('hadiths'):
            break
        if in_metadata and line.strip():
            match = re.match(r'\s+(\w+):\s*"(.+)"', line)
            if match:
                metadata[match.group(1)] = match.group(2)

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
    return metadata, hadiths

# Usage
meta, hadiths = fetch_section('bukhari', '1')
print(meta.get('intro'))      # Original intro
print(meta.get('intro_bn'))   # Bengali intro (if available)
print(meta.get('intro_fr'))   # French intro (if available)
print(hadiths[0]['arabic'])
```

### Parsing Rules

| Rule | Detail |
|------|--------|
| **CSV escaping** | RFC 4180 — use `""` for internal quotes, `\n` for newlines |
| **Empty values** | Empty string `""` or nothing between commas |
| **Numbers** | Unquoted integers |
| **Metadata** | Lines starting with `  ` (2 spaces) under `metadata:` block |
| **Header** | `hadiths[N]{col1,col2,...}:` — N = row count |
| **Intro fields** | `intro`, `intro_bn`, `intro_fr`, `intro_id`, `intro_ru`, `intro_ur` in metadata |

### Parsing Metadata

The `metadata:` block contains key-value pairs describing the section:

```toon
metadata:
  section_id: 1
  intro: "Book introduction text"
  intro_bn: "Bengali intro"
  intro_fr: "French intro"
```

**To parse metadata:**
```js
function parseMetadata(text) {
  const lines = text.split('\n');
  const metadata = {};
  let inMetadata = false;
  
  for (const line of lines) {
    if (line.trim() === 'metadata:') {
      inMetadata = true;
      continue;
    }
    if (inMetadata && line.startsWith('hadiths')) break;
    if (inMetadata && line.trim()) {
      const match = line.match(/^\s+(\w+):\s*"?(.+?)"?$/);
      if (match) metadata[match[1]] = match[2].replace(/"$/, '');
    }
  }
  return metadata;
}

// Usage
const meta = parseMetadata(fileContent);
console.log(meta.intro);      // Original intro
console.log(meta.intro_bn);   // Bengali intro (if available)
console.log(meta.intro_fr);   // French intro (if available)
```

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

### Index Files

```
editions.toon    # 25 books registry with available languages
info.toon        # Per-book section metadata (hadith ranges, section names)
```

**Example — Get all books:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions.toon
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
| Google Translate | Automated intro translations for multilingual support |

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
