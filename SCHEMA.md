# Hadith API Toon - Schema Documentation

## Architecture

```
editions/
├── {book}/
│   ├── info.toon              # Book metadata & section index
│   ├── sections/
│   │   └── {N}.toon         # Hadiths (NO translations embedded)
│   └── translations/
│       ├── {lang}/          # bn, en, fr, id, ru, ur
│       │   ├── metadata.toon
│       │   └── sections/
│       │       └── {N}.toon  # Translation text only
```

## Correct Structure

### Section files (`editions/{book}/sections/{section}.toon`)
```toon
hadiths[count]{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}:
```
**NO translation columns** - translations go in separate files

### Translation files (`editions/{book}/translations/{lang}/sections/{section}.toon`)
```jsonl
{"hadithnumber": "1", "text": "..."}
```
One file per language, JSONL format

---

## Full Schema

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
  available_languages: "arabic,bn,en,fr,id,ru,ur"
  intro: "Book introduction"
  intro_bn: "Bengali intro"
  intro_fr: "French intro"
  intro_id: "Indonesian intro"
  intro_ru: "Russian intro"
  intro_ur: "Urdu intro"

sections[count]{id,name,name_ar,name_bn,name_en,name_fr,name_id,name_ru,name_tr,name_ur,hadith_first,hadith_last,arabic_first,arabic_last}:
```

### Section file fields (`editions/{book}/sections/{section}.toon`)
| Field | Type | Description |
|-------|------|-------------|
| hadithnumber | int/string | Hadith number in book |
| arabic | string | Arabic text |
| grades | string | Grade (e.g. "Sahih") |
| reference | string | Reference info |
| international_number | string/int | Cross-book numbering |
| narrator_chain | string | ISNAD narration chain |
| chapter_intro | string | Chapter intro/name |

### Translation file fields (`editions/{book}/translations/{lang}/sections/{section}.toon`)
| Field | Type | Description |
|-------|------|-------------|
| hadithnumber | int/string | Matches section hadithnumber |
| text | string | Translation text |

### Translation metadata (`editions/{book}/translations/{lang}/metadata.toon`)
```toon
metadata:
  language: ur
  language_name: Urdu
  script: Arabic
  total_hadiths: 12272
  source: "source description"
```

---

## Supported Languages

| Code | Language | Script |
|------|----------|--------|
| ar | Arabic | Arabic |
| bn | Bengali | Bengali |
| en | English | Latin |
| fr | French | Latin |
| id | Indonesian | Latin |
| ru | Russian | Cyrillic |
| tr | Turkish | Latin |
| ur | Urdu | Arabic |