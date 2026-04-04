# Hadith API to Toon Format - Conversion Plan

## 1. Overview

Convert `fawazahmed0/hadith-api` from JSON to `.toon` format, following the patterns established in `quran-api-toon`. The hadith API has a fundamentally different data model than the Quran API (section-based vs page-based), so the architecture will adapt accordingly.

## 2. Key Architectural Difference: Sections vs Pages

| Aspect | Quran API | Hadith API |
|--------|-----------|------------|
| Primary unit | Mushaf page (1-604) | Section/Book chapter (0-N per collection) |
| Data partitioning | 604 fixed pages | Variable sections per book |
| Global index | `info.toon` (surahs, juzs, pages) | `info.toon` (books, sections, hadith ranges) |

**Decision**: Use **section-based partitioning** as the primary access pattern. Hadiths are naturally organized by kitab/chapter (sections), not by page numbers.

## 3. Target Directory Structure

```
hadith-api-toon/
├── README.md
├── info.toon                          # Global index: books, sections, hadith metadata
├── editions.toon                      # Edition registry (all translations)
├── grades.toon                        # Hadith grading reference data
├── editions/
│   └── {edition-slug}/               # e.g., eng-bukhari, ara-muslim
│       ├── sections/
│       │   ├── 0.toon                # Uncategorized hadiths (section 0)
│       │   ├── 1.toon                # Section 1 hadiths
│       │   ├── 2.toon
│       │   └── ...
│       └── hadiths/                   # Individual hadith files (optional, for granular access)
│           ├── 1.toon
│           ├── 2.toon
│           └── ...
├── scripts/
│   ├── convert_info_to_toon.py
│   ├── convert_editions_to_toon.py
│   ├── convert_section_files.py
│   └── convert_hadith_files.py
└── docs/
    ├── architecture-decision.md
    ├── editions.md
    └── info.md
```

## 4. Toon Format Specifications

### 4.1 `info.toon` - Global Index

Replaces `info.json`. Contains metadata for all hadith books.

```toon
books[9]{id,name,total_hadiths}:
  abudawud,"Sunan Abu Dawud",5274
  bukhari,"Sahih al Bukhari",7563
  dehlawi,"Forty Hadith of Shah Waliullah Dehlawi",40
  ibnmajah,"Sunan Ibn Majah",4341
  malik,"Muwatta Malik",1594
  muslim,"Sahih Muslim",7563
  nasai,"Sunan an Nasai",5758
  nawawi,"Forty Hadith of an-Nawawi",42
  qudsi,"Forty Hadith Qudsi",40
  tirmidhi,"Jami At Tirmidhi",3956

sections_abudawud[44]{id,name,hadith_first,hadith_last,arabic_first,arabic_last}:
  0,"",0,0,0,0
  1,"Purification (Kitab Al-Taharah)",1,390,1,390
  2,"Prayer (Kitab Al-Salat)",391,1160,391,1160
  ...

sections_bukhari[97]{id,name,hadith_first,hadith_last,arabic_first,arabic_last}:
  1,"Revelation",1,7,1,7
  2,"Belief",8,63,8,63
  ...

# Repeat sections_{book} for each book
```

**Note**: Sections are per-book since each hadith collection has its own section structure.

### 4.2 `editions.toon` - Edition Registry

Replaces `editions.json`. Lists all available translation editions.

```toon
editions[~70]{id,book,author,language,has_sections,dir,comments,path}:
  ara-abudawud,abudawud,Unknown,Arabic,true,rtl,,editions/ara-abudawud
  ara-abudawud1,abudawud,Unknown,Arabic,true,rtl,"Diacritics removed for easier searching",editions/ara-abudawud1
  eng-bukhari,bukhari,Muhsin Khan,English,true,ltr,,editions/eng-bukhari
  ...
```

### 4.3 `grades.toon` - Hadith Grading Reference

Extracted from `info.json` grades data. New file not in original API.

```toon
grades[~N]{book,hadithnumber,grader,grade}:
  abudawud,1,Al-Albani,"Hasan Sahih"
  abudawud,1,Muhammad Muhyi Al-Din Abdul Hamid,"Hasan Sahih"
  abudawud,1,Shuaib Al Arnaut,"Sahih Lighairihi"
  ...
```

### 4.4 Edition Section Files: `editions/{slug}/sections/{n}.toon`

Replaces `editions/{slug}/sections/{n}.json`. Contains all hadiths in a section.

```toon
metadata:
  book:abudawud
  section[1]{id,name}:
    1,"Purification (Kitab Al-Taharah)"
  section_detail[1]{id,hadith_first,hadith_last,arabic_first,arabic_last}:
    1,1,390,1,390

hadiths[390]{hadithnumber,arabicnumber,text,reference_book,reference_hadith}:
  1,1,"Narrated Abu Huraira: ...",1,1
  2,2,"Narrated 'Aisha: ...",1,2
  3,3,"Narrated Anas: ...",1,3
  ...
```

**Key design decisions:**
- `grades` array is NOT included in edition section files (it's empty in originals). Grades are in `grades.toon`.
- `arabicnumber` may be omitted if identical to `hadithnumber` (matching original API behavior).
- `reference_book` = section number, `reference_hadith` = hadith within section.

### 4.5 Individual Hadith Files: `editions/{slug}/hadiths/{n}.toon`

Replaces `editions/{slug}/{n}.json`. For granular single-hadith access.

```toon
hadith:
  hadithnumber:1
  arabicnumber:1
  text:"Narrated 'Umar bin Al-Khattab: ..."
  reference_book:1
  reference_hadith:1
  section:1,"Revelation"
```

### 4.6 `~/Downloads/chaptertranslation.json` Addition

This file will be added as a new data source. Based on the naming convention, it likely contains chapter/section translations for hadith books in additional languages.

**Proposed integration:**

```
hadith-api-toon/
├── section-translations.toon    # Chapter/section name translations
└── section-translations/
    └── {lang}.toon              # Per-language section name translations
```

Format for `section-translations.toon`:
```toon
translations[~N]{lang,book,section_id,name}:
  en,abudawud,1,"Purification (Kitab Al-Taharah)"
  ur,abudawud,1,"پاکستانی کتاب الطہارۃ"
  fr,bukhari,1,"La Révélation"
  ...
```

Format for `section-translations/{lang}.toon`:
```toon
sections_{book}[count]{section_id,name}:
  1,"Purification (Kitab Al-Taharah)"
  2,"Belief"
  ...
```

**Assumption**: The file structure is expected to be JSON with section/chapter names translated per book. The exact structure will be determined once the file is available.

## 5. Conversion Scripts

### 5.1 `convert_info_to_toon.py`

**Input**: `info.json`
**Output**: `info.toon`, `grades.toon`

Steps:
1. Parse `info.json` - extract books, sections, section_details, hadith metadata
2. Generate `books[count]{id,name,total_hadiths}:` section
3. For each book, generate `sections_{book}[count]{id,name,hadith_first,hadith_last,arabic_first,arabic_last}:`
4. Extract all grades from hadith metadata → `grades.toon`
5. Handle section 0 (uncategorized) specially

### 5.2 `convert_editions_to_toon.py`

**Input**: `editions.json`
**Output**: `editions.toon`

Steps:
1. Parse `editions.json`
2. Flatten book → collection array into flat edition list
3. Generate `editions[count]{id,book,author,language,has_sections,dir,comments,path}:`

### 5.3 `convert_section_files.py`

**Input**: `editions/{slug}/sections/{n}.json` (all editions)
**Output**: `editions/{slug}/sections/{n}.toon`

Steps:
1. For each edition directory, iterate section JSON files
2. Extract metadata → `metadata:` block
3. Extract hadiths array → `hadiths[count]{hadithnumber,arabicnumber,text,reference_book,reference_hadith}:`
4. Handle text escaping (commas, quotes, colons → double-quote wrapping)
5. Handle special characters (ﷺ, Arabic text, etc.)
6. Skip grades field (empty in editions)

### 5.4 `convert_hadith_files.py`

**Input**: `editions/{slug}/{n}.json` (individual hadith files)
**Output**: `editions/{slug}/hadiths/{n}.toon`

Steps:
1. For each edition, iterate individual hadith JSON files
2. Convert to single-hadith toon format
3. Include section name from metadata

### 5.5 `convert_chapter_translation.py` (TBD)

**Input**: `~/Downloads/chaptertranslation.json`
**Output**: `section-translations.toon`, `section-translations/{lang}.toon`

Steps:
1. Parse the JSON file (structure TBD)
2. Generate global index + per-language files
3. Handle missing section mappings

## 6. Data Mapping Summary

| Original JSON | Toon Format | Notes |
|--------------|-------------|-------|
| `info.json` (books + sections) | `info.toon` | Split into books + per-book sections |
| `info.json` (hadith grades) | `grades.toon` | Extracted from hadith skeleton |
| `editions.json` | `editions.toon` | Flattened from nested structure |
| `editions/{slug}/sections/{n}.json` | `editions/{slug}/sections/{n}.toon` | Primary data files |
| `editions/{slug}/{n}.json` | `editions/{slug}/hadiths/{n}.toon` | Granular access |
| `chaptertranslation.json` | `section-translations.toon` | New addition |

## 7. Toon Format Rules

### 7.1 Schema Header Pattern
```
section_name[count]{field1,field2,field3}:
```
- `count` = number of data rows
- Fields are comma-separated in curly braces
- Colon terminates the header

### 7.2 Data Rows
- Comma-separated values matching field order
- Strings with commas, colons, or special chars → double-quoted
- Numbers → unquoted
- Null → `null` (unquoted)
- Nested JSON arrays → preserved as JSON strings (double-quoted)

### 7.3 Key-Value Pattern
```
section_name:
  key1:value1
  key2:value2
```
- Used for metadata blocks
- Colon separates key from value

### 7.4 Escaping
- `\n` for newlines within strings
- `\"` for literal quotes within quoted strings
- Double-quote entire field if it contains: `,`, `:`, `"`, `\n`

## 8. Estimated Scale

| Metric | Value |
|--------|-------|
| Hadith books | 9 |
| Total editions | ~70+ |
| Total sections | ~500+ (varies by book) |
| Total hadiths | ~40,000+ across all books |
| Section files per edition | 10-100 (depends on book) |
| Total .toon files | ~5,000-10,000 |

## 9. CDN URL Pattern

```
https://cdn.jsdelivr.net/gh/{user}/hadith-api-toon@main/editions/{slug}/sections/{n}.toon
https://cdn.jsdelivr.net/gh/{user}/hadith-api-toon@main/editions/{slug}/hadiths/{n}.toon
https://cdn.jsdelivr.net/gh/{user}/hadith-api-toon@main/info.toon
https://cdn.jsdelivr.net/gh/{user}/hadith-api-toon@main/editions.toon
https://cdn.jsdelivr.net/gh/{user}/hadith-api-toon@main/grades.toon
```

## 10. Implementation Order

1. **Phase 1**: Core conversion scripts
   - `convert_info_to_toon.py`
   - `convert_editions_to_toon.py`

2. **Phase 2**: Edition data conversion
   - `convert_section_files.py`
   - `convert_hadith_files.py`

3. **Phase 3**: Chapter translation integration
   - `convert_chapter_translation.py` (once file structure is known)

4. **Phase 4**: Validation & documentation
   - Validate all .toon files
   - Write README and docs
   - Test CDN URL patterns

## 11. Edge Cases & Considerations

1. **Section 0**: Uncategorized hadiths - exists in some books, may be empty
2. **Missing arabicnumber**: Some editions omit it when equal to hadithnumber
3. **Empty grades**: Edition files have empty grades arrays - grades only in info.json
4. **Text escaping**: Hadith text contains quotes, colons, special Unicode (ﷺ), newlines
5. **Arabic diacritics**: Two variants per book (with/without diacritics)
6. **Large sections**: Some sections have 700+ hadiths - ensure toon format handles large counts
7. **Reference mapping**: `reference.book` = section number, not book name - needs clarification in docs
