# Hadith API — Toon Format

> In the name of God, who has guided me to do this work

The most comprehensive multilingual Hadith database on the internet. **31 books, 214,353 hadiths, 16 languages** — all in unified, CDN-optimized `.toon` format.


**Built from:** [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) · [al-hadees.com](https://al-hadees.com) · [sunnah.com](https://sunnah.com) · [hadith-json](https://github.com/AhmedBaset/hadith-json)

---

## Overview

| Metric | Value |
|--------|-------|
| **Books** | 31 |
| **Total Hadiths** | 214,353 |
| **Languages** | Arabic, Bengali, Bosnian, German, English, Spanish, French, Hindi, Indonesian, Romanian, Russian, Swahili, Tamil, Telugu, Turkish, Urdu |
| **Collections** | 31 unified books |
| **Database Files** | 9,223 `.toon` files |

Arabic text and metadata stored in `editions/{book}/sections/{N}.toon`. Translations stored separately in `editions/{book}/translations/{lang}/sections/{N}.toon` for efficient loading.

Book-level intro + author metadata stored in `editions/{book}/info.toon`.

---

## 💻 Web Reader Client (`viewer.html`)

The database includes a premium, S-tier browser client (`viewer.html`) for accessing all collections.

### Key Features:
* **Offline Bookmarking (Starred)**: Star any Hadith across any collection to save it locally via `localStorage` for quick retrieval.
* **Instant Filtering**: Real-time keyword search across Arabic text, grades, references, and translations dynamically.
* **Preferences Customizer**: Adjustable font scales for both Arabic text and translations, with independent visibility toggles.
* **Formatted Copy-to-Clipboard**: Copy references, Arabic text, and translations with a single click, featuring interactive copy validation.

---

## The `.toon` Format

`.toon` is a compact, self-describing, CSV-like plain-text format. Each file defines its own schema in the header, so parsers automatically know which columns are present.

### 💾 Storage & Compression Savings (Toon vs. JSON vs. Protobuf)

A benchmark was conducted on the complete dataset (Arabic text + translations) of **Shama'il al-Tirmidhi** (417 hadiths) comparing Toon vs. standard formats:

| Format Profile | Raw Size (Bytes) | Gzip Size (Bytes) | Brotli Size (Bytes) | Raw vs. Minified JSON | Brotli vs. Minified JSON |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Toon (Merged)** | **868,599** | **190,638** | **137,962** | **-4.73%** | **-0.75%** |
| **Protobuf (Binary)** | 877,352 | 200,550 | 145,344 | -3.77% | +4.56% |
| **JSON (Minified)** | 911,753 | 192,614 | 139,003 | *Baseline* | *Baseline* |
| **JSON (Pretty)** | 950,799 | 193,988 | 139,541 | +4.28% | +0.39% |

* **Zero-Key Overhead**: Positional columns in Toon remove the repetitive schema keys present in JSON.
* **Optimized for Brotli**: The combination of Toon positional syntax and Brotli (`content-encoding: br`) yields the absolute smallest network footprints.

### Structure

```toon
# editions/{book}/info.toon
metadata:
  book_id: bukhari
  book_name: "Sahih al-Bukhari"
  total_hadiths: 12642
  available_languages: "ar,bn,en,fr,id,ru,ur"
  intro: "Book introduction"
  intro_ur: "Book introduction in Urdu"

sections[97]{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}:
  1,"Revelation","بدء الوحي",... ,1,7,1,7

# editions/{book}/sections/1.toon (Arabic + metadata only)
hadiths[7]{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}:
  "1","حَدَّثَنَا...","Sahih","...","1","Narrated 'Umar","Revelation"
  "2","حَدَّثَنَا...","Sahih","...","2","Narrated 'Aisha","Revelation"

# editions/{book}/translations/ur/sections/1.toon (Translation only)
hadiths[7]{hadithnumber,text}:
  "1","عمر بن خطاب رضی اللہ عنہ سے روایت ہے..."
  "2","عائشہ رضی اللہ عنہا سے روایت ہے..."
```
### How It Works

1. **Global index** — Root `info.toon` lists all 25 books with metadata.
2. **Book metadata** — `editions/{book}/info.toon` stores intro + section index.
3. **Section data** — `editions/{book}/sections/{N}.toon` stores Arabic text + metadata (NO translations).
4. **Translation files** — `editions/{book}/translations/{lang}/sections/{N}.toon` stores translations separately.
5. **Dynamic columns** — Parse header (`hadiths[N]{...}`) to discover available fields.

---

## Language Support

Arabic text and metadata are in section files. Translations are stored separately by language in `editions/{book}/translations/{lang}/sections/{N}.toon`.

### Book Introductions

Each book includes multilingual introductions in per-book metadata file:

```toon
# editions/{book}/info.toon
metadata:
  book_id: bukhari
  book_name: "Sahih al-Bukhari"
  available_languages: "ar,bn,en,fr,id,ru,ur"
  intro: "Book introduction"
  intro_bn: "Bengali translation"
  intro_fr: "French translation"
  intro_id: "Indonesian translation"
  intro_ru: "Russian translation"
  intro_ur: "Urdu translation"
```

**Language availability varies by book.** Check `available_languages` in book metadata or list translation directories.

---

## How to Parse (For Developers)

### Getting Started

**Step 1: Load the book index**

Start by fetching `info.toon` to get all 25 books with their metadata:

```js
// Quote-aware positional field splitter
function parseToonLine(line) {
  const result = [];
  let current = '', inQuotes = false, i = 0;
  while (i < line.length) {
    const char = line[i];
    if (inQuotes) {
      if (char === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') { current += '"'; i += 2; }
        else { inQuotes = false; i++; }
      } else { current += char; i++; }
    } else {
      if (char === '"') { inQuotes = true; i++; }
      else if (char === ',') { result.push(current); current = ''; i++; }
      else { char !== '\r' ? current += char : null; i++; }
    }
  }
  result.push(current);
  return result;
}

const response = await fetch('https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon');
const text = await response.text();
const lines = text.split('\n').filter(l => l.trim());

// Parse header to get column names
const header = lines[0];
const cols = header.match(/\{(.+)\}/)[1].split(',').map(c => c.trim());

// Parse book rows
const books = lines.slice(1).map(line => {
  const vals = parseToonLine(line);
  return Object.fromEntries(cols.map((col, i) => [col, vals[i] || '']));
});

// Now you have all books with: id, name, total_hadiths, available_languages, path
console.log(books[0]); // { id: 'abdurrazzaq', name: 'Musannaf Abdur Razzaq', ... }
```

**Step 2: Load book metadata**

Fetch `editions/{book}/info.toon` to get:
- Available translations index (language codes, section counts, paths)
- Section index with hadith ranges
- Translated section/chapter names in all available languages (name_ar, name_bn, name_en, name_fr, name_id, name_ru, name_tr, name_ur)
- Book introduction in multiple languages

```js
const bookInfo = await fetch(`https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/info.toon`);
// Parse to get:
// - translations table: language, sections, path
// - sections table: id, name, name_ar, name_bn, name_en, name_fr, name_id, name_ru, name_tr, name_ur, hadith_first, hadith_last
```

**Step 3: Load hadiths**

Fetch section files for Arabic text, and translation files for specific languages.

### Parsing Section Files

Section files contain Arabic text and metadata. Translation files contain only `hadithnumber` and `text` columns. Parse headers dynamically to discover available fields.

### JavaScript Example

```js
// Quote-aware positional field splitter
function parseToonLine(line) {
  const result = [];
  let current = '', inQuotes = false, i = 0;
  while (i < line.length) {
    const char = line[i];
    if (inQuotes) {
      if (char === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') { current += '"'; i += 2; }
        else { inQuotes = false; i++; }
      } else { current += char; i++; }
    } else {
      if (char === '"') { inQuotes = true; i++; }
      else if (char === ',') { result.push(current); current = ''; i++; }
      else { char !== '\r' ? current += char : null; i++; }
    }
  }
  result.push(current);
  return result;
}

async function fetchSection(book, sectionId) {
  const url = `https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/${book}/sections/${sectionId}.toon`;
  const text = await fetch(url).then(r => r.text());
  
  const headerMatch = text.match(/^([A-Za-z_]+)\[(?:count|\d+)\]\{([^}]+)\}\s*:/);
  if (!headerMatch) return null;
  
  const cols = headerMatch[2].split(',').map(f => f.trim());
  const rest = text.substring(headerMatch[0].length);
  
  const lines = rest.split('\n');
  const hadiths = [];
  let currentRebuiltRow = '';
  let inQuote = false;
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
    currentRebuiltRow += (currentRebuiltRow ? '\n' : '') + line;
    const quotesCount = (trimmed.replace(/""/g, '').match(/"/g) || []).length;
    if (quotesCount % 2 === 1) inQuote = !inQuote;
    
    if (!inQuote) {
      const vals = parseToonLine(currentRebuiltRow);
      const row = {};
      cols.forEach((col, i) => (row[col] = vals[i] || ''));
      hadiths.push(row);
      currentRebuiltRow = '';
    }
  }
  return { columns: cols, hadiths };
}

// Usage
const { hadiths } = await fetchSection('bukhari', '1');
console.log(hadiths[0].arabic);          // Arabic text
console.log(hadiths[0].hadithnumber);    // Hadith number
console.log(hadiths[0].grades);          // Scholar grades

// For translations, fetch from the translations path:
const { hadiths: enHadiths } = await fetchSection('bukhari/translations/en', '1');
console.log(enHadiths[0].text);          // English translation text
```

### Python Example

```python
import csv, io, requests, re

def fetch_section(book, section_id):
    url = f"https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/{book}/sections/{section_id}.toon"
    text = requests.get(url).text
    
    # 1. Parse header block structure: hadiths[count]{fields}:
    header_match = re.search(r'^([A-Za-z_]+)\[(?:count|\d+)\]\{(.*?)\}\s*:', text, re.DOTALL)
    if not header_match:
        raise ValueError("Invalid .toon format header")
        
    cols = [f.strip() for f in header_match.group(2).split(',')]
    rest_data = text[header_match.end():]
    
    # 2. Parse data rows statefully using csv.reader
    reader = csv.reader(io.StringIO(rest_data))
    hadiths = []
    for row in reader:
        if not row:
            continue
        # Align rows with schema fields
        if len(row) < len(cols):
            row += [''] * (len(cols) - len(row))
        hadiths.append(dict(zip(cols, row)))
        
    return cols, hadiths

# Usage
cols, hadiths = fetch_section('bukhari', '1')
print(hadiths[0]['arabic'][:100])
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
  const meta = {};
  const lines = text.split('\n');
  let inMetadata = false;
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === 'metadata:') {
      inMetadata = true;
      continue;
    }
    if (inMetadata) {
      if (trimmed.startsWith('translations[') || trimmed.startsWith('sections[')) {
        break;
      }
      const match = trimmed.match(/^(\w+):\s*"?([^"]*)"?$/);
      if (match) {
        meta[match[1]] = match[2];
      }
    }
  }
  return meta;
}

// Usage
const meta = parseBookInfoMetadata(fileContent);
console.log(meta.book_id);      // e.g. 'bukhari'
console.log(meta.book_name);    // e.g. 'Sahih al-Bukhari'
console.log(meta.intro_bn);     // Bengali intro (if available)
console.log(meta.intro_ur);     // Urdu intro (if available)
```

---

## CDN Usage

**Recommended: Use branch or version tags for stability**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/{endpoint}
```

> **Note on caching:** jsDelivr caches `@main` branch URLs for up to 24 hours. For immediate updates, use version tags or commit hashes.

### Global Index

| File | Description |
|------|-------------|
| [`info.toon`](https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon) | 31 books index (`id,name,total_hadiths,available_languages,path`) |

### Per-Book Metadata

| Path | Description |
|------|-------------|
| `/editions/{book}/info.toon` | Book intro (multilingual), translations index (language, sections, path), section index with translated chapter/section names |

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
info.toon        # All 31 books with section metadata (hadith ranges, section names)
```

### Translation Files

```
/editions/{book}/translations/{lang}/sections/{sectionNo}.toon
```

**Example — Nawawi Urdu, Section 1:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/nawawi/translations/ur/sections/1.toon
```

**Example — Get all books:**
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon
```

---

## Books

| # | Book | Languages | Hadiths |
|---|------|-----------|---------|
| 1 | Musannaf Abdur Razzaq | ar, en, ur | 18,777 |
| 2 | Sunan Abu Dawud | ar, bn, en, fr, hi, id, roman-ur, ru, tr, ur | 5,274 |
| 3 | Al-Adab Al-Mufrad | ar, en, ur | 1,333 |
| 4 | Sunan Al-Kubra Bayhaqi | ar, en, ur | 21,815 |
| 5 | Sahih al-Bukhari | ar, bn, en, fr, hi, id, roman-ur, ru, ta, tr, ur | 7,273 |
| 6 | Bulugh al-Maram | ar, en, ur | 1,358 |
| 7 | Forty Hadith of Shah Waliullah Dehlawi | ar, en, fr, ur | 40 |
| 8 | Fatah Al-Rabani | ar, en, ur | 89 |
| 9 | Hisn al-Muslim | ar, en | 268 |
| 10 | Sahih Ibn Hibban | ar, en, ur | 7,395 |
| 11 | Sunan Ibn Majah | ar, bn, en, fr, hi, id, roman-ur, tr, ur | 4,341 |
| 12 | Al-Lulu wal-Marjan | ar, en, ur | 1,906 |
| 13 | Muwatta Malik | ar, bn, en, fr, id, tr, ur | 2,762 |
| 14 | Mishkat al-Masabih | ar, en, hi, roman-ur, ur | 6,294 |
| 15 | Muajam Tabarani Saghir | ar, en, ur | 18,326 |
| 16 | Musannaf Ibn Abi Shaybah | ar, en, ur | 39,098 |
| 17 | Sahih Muslim | ar, bn, en, fr, hi, id, roman-ur, ru, ta, tr, ur | 7,564 |
| 18 | Musnad Ahmad | ar, en, ur | 22,368 |
| 19 | Al-Mustadrak | ar, en, ur | 8,803 |
| 20 | Sunan an-Nasai | ar, bn, en, fr, hi, id, roman-ur, tr, ur | 5,713 |
| 21 | Sunan al-Kubra an-Nasai | ar, en, ur | 11,385 |
| 22 | Forty Hadith of an-Nawawi | ar, bn, bs, en, fr, tr, ur | 42 |
| 23 | Forty Hadith Qudsi | ar, bn, de, en, es, fr, hi, id, ru, sw, ta, te, tr, ur | 40 |
| 24 | Riyad as-Salihin | ar, en, ur | 1,896 |
| 25 | Sahih Ibn Khuzaymah | ar, en, ur | 3,784 |
| 26 | Shamail-e-Tirmazi | ar, en, ur | 417 |
| 27 | Silsila Sahiha | ar, en, ur | 3,550 |
| 28 | Sunan al-Daraqutni | ar, en, ur | 4,859 |
| 29 | Sunan ad-Darimi | ar, en, ur | 3,535 |
| 30 | Jami At-Tirmidhi | ar, bn, en, hi, id, roman-ur, tr, ur | 3,955 |
| 31 | Virtues of Good Deeds | ar, en, ur | 93 |

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

## Scripts

All utility scripts are in `scripts/`:

### Data Quality & Validation

| Script | Purpose |
|--------|---------|
| `validate_all_toon.py` | Validates all 9,223 active `.toon` files for CSV schema compliance (stateful multi-line quote check) |
| `fix_zero_width.py` | Recursively removes zero-width characters and invisible control tokens from database files |
| `fix_truncated_offline.py` | Automatically repairs truncated hadiths offline using cached databases |
| `fix_truncated_only.py` | Repairs remaining truncations concurrently using local LLM completion endpoints |
| `run_experiment.py` | Formats and sizes benchmark comparing JSON, Min.JSON, Toon, and Protobuf (+ Gzip/Brotli) |
| `clean_toon_data.py` | Historical: removes trailing commas and fixes broken CSV quotes |
| `check_data_integrity.py` | Historical: verifies record counts to ensure no data loss |

### Usage

**Validate database files:**
```bash
python3 scripts/validate_all_toon.py
```

**Run format comparison benchmark:**
```bash
python3 scripts/run_experiment.py
```

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
