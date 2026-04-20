# Hadith API Toon — Scripts Reference

Documentation for all conversion and maintenance scripts in `scripts/`.

---

## `rebuild_all_from_hadith_new.py` ⭐ Primary

**Full clean rebuild** of all translation languages from `hadith-new/editions/` source.

```bash
# Dry run (no writes, shows what would happen)
python3 scripts/rebuild_all_from_hadith_new.py --dry-run

# Full rebuild (deletes + rewrites all pairs from hadith-new)
python3 scripts/rebuild_all_from_hadith_new.py

# Force even low-coverage pairs (>50% default threshold)
python3 scripts/rebuild_all_from_hadith_new.py --force
```

**What it does:**
- Reads all `{lang_prefix}-{book}.json` from `hadith-new/editions/` (non-Arabic, non-`*1` variants)
- For each pair: verifies coverage against Arabic section boundaries before touching anything
- Deletes existing translation dir (if exists), rewrites from fresh source
- Preserves langs with no hadith-new source (e.g. books like `aladab-almufrad`)
- Updates `available_languages` in `editions/{book}/info.toon` and root `info.toon`

**Coverage safety gate:** Aborts any pair with < 50% coverage (use `--force` to override).

---

## `import_hadith_new_langs.py` — Additive Only

**Adds specific missing lang/book pairs** without touching existing data.

```bash
python3 scripts/import_hadith_new_langs.py --dry-run
python3 scripts/import_hadith_new_langs.py
```

Configure `MISSING_PAIRS` list inside the script for targeted imports.  
Skips if `translations/{lang}/sections/` already exists and has files.

---

## `convert_section_files.py`

Converts `hadith-new`-style section JSON files to toon section format.  
Used for Arabic sections (`editions/{book}/sections/*.toon`).

```bash
python3 scripts/convert_section_files.py
```

---

## `convert_info_to_toon.py`

Converts book metadata JSON to `editions/{book}/info.toon` format.

---

## `validate_toon.py`

Validates the structure of generated `.toon` files.

```bash
python3 validate_toon.py
```

---

## Language Code Reference

| hadith-new prefix | toon folder | Language | Script |
|-------------------|-------------|----------|--------|
| `ara` | `ar` | Arabic | Arabic |
| `ben` | `bn` | Bengali | Bengali |
| `eng` | `en` | English | Latin |
| `fra` | `fr` | French | Latin |
| `ind` | `id` | Indonesian | Latin |
| `rus` | `ru` | Russian | Cyrillic |
| `tam` | `ta` | Tamil | Tamil |
| `tur` | `tr` | Turkish | Latin |
| `urd` | `ur` | Urdu | Arabic |

---

## File Format Reference

### Translation section file: `editions/{book}/translations/{lang}/sections/{N}.toon`

JSONL — one JSON object per line:
```json
{"hadithnumber": "1", "text": "Translation text here..."}
{"hadithnumber": "2", "text": "Next hadith translation..."}
```

### Translation metadata file: `editions/{book}/translations/{lang}/metadata.toon`

```
metadata:
  language: ur
  language_name: Urdu
  script: Arabic
  total_hadiths: 7589
  source: "hadith-new"
```

### Per-book info: `editions/{book}/info.toon`

```
metadata:
  book_id: bukhari
  book_name: "Sahih al-Bukhari"
  total_hadiths: 12642
  available_languages: "ar,bn,en,fr,id,ru,ta,tr,ur"
  intro: "..."

sections[98]{id,name,...,hadith_first,hadith_last,...}:
  1,...
```

### Root index: `info.toon`

```
metadata:
  version: 2.0
  total_books: 25

books[25]{id,name,total_hadiths,available_languages,path}:
  bukhari,"Sahih al-Bukhari",12642,"ar,bn,en,fr,id,ru,ta,tr,ur",editions/bukhari
```
