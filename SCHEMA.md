# Hadith API Toon - Schema Documentation

## Current Schema

### Root `info.toon`
```toon
metadata:
  version: 2.0
  total_books: 25
  description: "Hadith API - Toon Format"

books[count]{id,name,total_hadiths,available_languages,path}:
```

### Per-book `editions/{book}/info.toon`
```toon
metadata:
  book_id: bukhari
  book_name: "Sahih al-Bukhari"
  total_hadiths: 12642
  available_languages: "arabic,bengali,english,french,indonesian,russian,urdu"
  intro: "Book introduction"
  intro_bn: "..."
  intro_fr: "..."
  intro_id: "..."
  intro_ru: "..."
  intro_ur: "..."

sections[count]{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}:
```

### Section files (`editions/{book}/sections/{section}.toon`)
```toon
hadiths[count]{hadithnumber,arabic,bengali,english,french,indonesian,russian,urdu,grades,reference,international_number,narrator_chain,chapter_intro}:
```

### Translation slices
```text
editions/{book}/translations/{lang}/sections/{section}.toon
```

Rows are JSONL objects:
```json
{"hadithnumber": "1", "text": "..."}
```

### Per-book metadata fields (`editions/{book}/info.toon`)
| Field | Type | Description |
|-------|------|-------------|
| book_id | string | Book slug |
| book_name | string | Book display name |
| total_hadiths | int | Book hadith count |
| available_languages | string | Comma-separated language list |
| intro | string | Book introduction in source language |
| intro_bn | string | Bengali intro translation |
| intro_fr | string | French intro translation |
| intro_id | string | Indonesian intro translation |
| intro_ru | string | Russian intro translation |
| intro_ur | string | Urdu intro translation |

### Section index fields (`editions/{book}/info.toon`)
| Field | Type | Description |
|-------|------|-------------|
| id | int | Section/chapter number |
| name | string | Section name |
| name_ar | string | Arabic section name |
| name_bn | string | Bengali section name |
| name_en | string | English section name |
| name_fr | string | French section name |
| name_id | string | Indonesian section name |
| name_ru | string | Russian section name |
| name_tr | string | Turkish section name |
| name_ur | string | Urdu section name |
| hadith_first | int | First hadith number in section |
| hadith_last | int | Last hadith number in section |
| arabic_first | int | First Arabic-numbering index |
| arabic_last | int | Last Arabic-numbering index |

### Section row fields (`editions/{book}/sections/{section}.toon`)
| Field | Type | Description |
|-------|------|-------------|
| hadithnumber | int/string | Hadith number in book |
| arabic | string | Arabic text |
| bengali | string | Bengali translation (if present) |
| english | string | English translation (if present) |
| french | string | French translation (if present) |
| indonesian | string | Indonesian translation (if present) |
| russian | string | Russian translation (if present) |
| urdu | string | Urdu translation (if present) |
| grades | string | Grade text/source field |
| reference | string | Reference text |
| international_number | string/int | Cross-numbering |
| narrator_chain | string | Narrator chain |
| chapter_intro | string | Chapter intro/name field |

Note: translation-language columns vary per book. Parse section header dynamically.
