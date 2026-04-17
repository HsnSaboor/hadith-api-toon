# Hadith API to Toon Format - Conversion Status

## 1. Scope

Repository now uses book-centric Toon layout for 25 hadith books.

## 2. Current Directory Model

```text
hadith-api-toon/
├── README.md
├── info.toon                             # Root book index
├── grades.toon                           # Grade reference data
├── editions/
│   └── {book}/
│       ├── info.toon                     # Book intro + section index
│       ├── sections/
│       │   ├── 1.toon
│       │   ├── 2.toon
│       │   └── ...
│       └── translations/
│           └── {lang}/
│               ├── metadata.toon         # Book intro for language
│               └── sections/
│                   ├── 1.toon
│                   ├── 2.toon
│                   └── ...
└── scripts/
```

## 3. File Contracts

### 3.1 Root Index (`info.toon`)

```toon
metadata:
  version: 2.0
  total_books: 25

books[25]{id,name,total_hadiths,available_languages,path}:
```

### 3.2 Per-Book Metadata (`editions/{book}/info.toon`)

Contains:
- `metadata` block (`book_id`, `book_name`, `total_hadiths`, `available_languages`, `intro*` fields)
- `sections[count]{...}` table with section names + ranges.

### 3.3 Section Data (`editions/{book}/sections/{section}.toon`)

```toon
hadiths[count]{...dynamic language columns...,grades,reference,international_number,narrator_chain,chapter_intro}:
```

No metadata block in section files. Parser must read header for column order.

### 3.4 Translation Slices (`editions/{book}/translations/{lang}/sections/{section}.toon`)

Rows are JSONL:

```json
{"hadithnumber": "1", "text": "..."}
```

## 4. Recent Completed Work

- Urdu translation slices added from source section data:
  - `editions/dehlawi/translations/ur/sections/1.toon`
  - `editions/qudsi/translations/ur/sections/1.toon`
  - `editions/nawawi/translations/ur/sections/1.toon`
- Root index language coverage updated for these books.
- Book-level language metadata updated for these books.
- `editions/nawawi/info.toon` restored (was removed).
- `editions/qudsi/info.toon` malformed `intro_ur` payload fixed.

## 5. Validation Notes

- `validate_toon.py` currently reports legacy issues in older book files unrelated to latest Urdu extraction changes.
- Parser contract for new/updated files remains valid:
  - root `info.toon` index
  - per-book `info.toon` intro metadata
  - translation JSONL slices.

## 6. Deprecated Notes (from old draft plan)

Following items from old planning doc no longer reflect current repo state:
- `editions.toon` as active registry file.
- `editions/{slug}/hadiths/{n}.toon` as active layout.
- section-level metadata blocks containing intro fields.
- 9-book initial scope estimates.

Current source of truth: actual files in repository (`info.toon`, `editions/*/info.toon`, `editions/*/sections/*.toon`, `editions/*/translations/*/sections/*.toon`).
