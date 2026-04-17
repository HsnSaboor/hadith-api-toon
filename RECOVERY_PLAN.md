# Recovery Plan: Lost Translations from Git History

## Problem
- 15 books have NO translations in current structure
- These translations EXIST in git at commit `56db4b8^` in old format (`eng-*`, `urd-*` folders)
- Lost during restructure when unifying editions

## Source Data (Commit: 56db4b8^)
```
editions/eng-{book}/sections/{N}.toon   → English translations
editions/urd-{book}/sections/{N}.toon   → Urdu translations
editions/ben-{book}/sections/{N}.toon   → Bengali translations
editions/fra-{book}/sections/{N}.toon   → French translations
editions/ind-{book}/sections/{N}.toon   → Indonesian translations
editions/rus-{book}/sections/{N}.toon   → Russian translations
```

## Target Structure (Per SCHEMA.md)
```
editions/{book}/
├── sections/{N}.toon          # hadithnumber,arabic,grades,reference,...
└── translations/
    ├── en/sections/{N}.toon   # JSONL: {"hadithnumber":"1","text":"..."}
    ├── ur/sections/{N}.toon
    ├── bn/sections/{N}.toon
    ├── fr/sections/{N}.toon
    ├── id/sections/{N}.toon
    └── ru/sections/{N}.toon
```

## Books to Recover (15 books)
| Book | Source Languages Available |
|------|---------------------------|
| aladab-almufrad | eng, urd |
| bayhaqi | urd |
| bulugh-al-maram | eng, urd |
| fatah-alrabani | urd |
| lulu-wal-marjan | urd |
| mishkat | eng, urd |
| muajam-tabarani-saghir | urd |
| musannaf-ibn-abi-shaybah | urd |
| musnad-ahmed | eng, urd |
| mustadrak | urd |
| sahih-ibn-khuzaymah | urd |
| shamail-tirmazi | eng, urd |
| silsila-sahih | urd |
| sunan-al-daraqutni | urd |
| sunan-darmi | urd |

## Implementation Steps

### Step 1: Create recovery script
- List all books needing recovery
- For each book: detect which lang folders exist at `56db4b8^`
- Map old folder names to new codes:
  - eng → en
  - urd → ur
  - ben → bn
  - fra → fr
  - ind → id
  - rus → ru

### Step 2: Extract translations per language
- For each language folder that exists:
  - Get all section files
  - Parse hadith data
  - Convert to JSONL format:
    ```json
    {"hadithnumber": "1", "text": "..."}
    ```

### Step 3: Write to new structure
- Create directory: `editions/{book}/translations/{lang}/sections/`
- Write each section file as JSONL

### Step 4: Verify
- Count extracted hadiths per book/lang
- Compare with expected counts
- Update `info.toon` available_languages

## Estimated Outcome
- Recover ~2,000+ hadiths per language
- Add ~15,000+ total translation entries
- 10 → 25 books with translations

## After Recovery
- Update root `info.toon` with correct language counts
- Update each book's `info.toon` with available_languages

## Execution Command
```bash
python3 scripts/recover_translations.py
```