# Hadith API Toon — Data Rebuild Log

**Date:** 2026-04-18  
**Source:** `hadith-new/editions/` (JSON format from hadith-api)  
**Operation:** Full clean rebuild of all translation languages from authoritative source

---

## What Was Done

### Problem with Previous Data

| Book | Issue |
|------|-------|
| `ibnmajah/ur` | Old urdu section 0 had hadiths 1–266 (all in one file), section 1 started at 267 — misaligned with Arabic sections |
| `muslim/ur` | Old urdu section 0 started at hadith 93 (first 92 hadiths missing) |
| `malik/ur` | Old urdu had only 59 sections, Arabic has 62 — 3 sections missing |
| All books | Urdu data was sourced from a different, incomplete extract |
| All langs | No verification step existed between old ingest and toon conversion |

### Solution

1. **Verified** all 54 source pairs against section boundaries (coverage 87.7%–100%)
2. **Deleted** all existing translation lang dirs that have new source in `hadith-new`
3. **Wrote** fresh JSONL `.toon` files from authoritative `hadith-new` JSON
4. **Preserved** langs with no `hadith-new` source (e.g. `nawawi/ur`, `qudsi/ur`, `dehlawi/ur`)
5. **Updated** `available_languages` in both per-book `info.toon` and root `info.toon`

---

## Final Language Matrix (10 books from hadith-new)

| Book | ar | bn | en | fr | id | ru | ta | tr | ur |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| abudawud | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| bukhari | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ibnmajah | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ |
| malik | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ |
| muslim | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| nasai | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ |
| nawawi | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | kept* |
| qudsi | ✓ | — | ✓ | ✓ | — | — | — | — | kept* |
| dehlawi | ✓ | — | ✓ | ✓ | — | — | — | — | kept* |
| tirmidhi | ✓ | ✓ | ✓ | — | ✓ | — | — | ✓ | ✓ |

> `kept*` = No hadith-new source available; existing translation preserved from earlier scrape.

---

## Verification Summary (all 54 pairs)

| Book/Lang | Source Hadiths | Boundary Slots | Matched | Coverage |
|-----------|---------------|----------------|---------|----------|
| abudawud/bn,en,fr,id,ru,tr,ur | 5,274 | 5,322 | 5,320 | **100.0%** |
| bukhari/bn,en,fr,id,ru,ta,tr,ur | 7,589–7,590 | 27,006 | 27,006 | **100.0%** |
| dehlawi/en,fr | 40 | 40 | 40 | **100.0%** |
| ibnmajah/bn,en,fr,id,tr,ur | 4,343 | 22,379 | 22,371 | **100.0%** |
| malik/bn,en,fr,id,tr,ur | 1,858–1,899 | 7,674 | 6,732 | **87.7%** |
| muslim/bn,en,fr,id,ru,ta,tr,ur | 7,563–7,564 | 37,812 | 37,812 | **100.0%** |
| nasai/bn,en,fr,id,tr,ur | 5,765 | 9,784 | 9,774 | **99.9%** |
| nawawi/bn,en,fr,tr | 42 | 42 | 42 | **100.0%** |
| qudsi/en,fr | 40 | 40 | 40 | **100.0%** |
| tirmidhi/bn,en,id,tr,ur | 3,998 | 6,735 | 6,638 | **98.6%** |

> **Malik 87.7%:** Muwatta Malik uses a different numbering scheme in Arabic sections vs the translation hadithnumbers. The 942 missing slots correspond to Arabic-only hadiths that have no translated text in the source (not a data loss — source simply doesn't translate those).

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/rebuild_all_from_hadith_new.py` | Full clean rebuild with verification |
| `scripts/import_hadith_new_langs.py` | Add specific missing lang/book pairs (additive only) |

---

## Preserved Data (not touched)

These books have no hadith-new source — their existing data is from other verified scrapes:

| Book | Preserved Langs |
|------|----------------|
| aladab-almufrad | en, ur |
| bayhaqi | en, ur |
| bulugh-al-maram | en, ur |
| fatah-alrabani | en, ur |
| lulu-wal-marjan | en, ur |
| mishkat | en, ur |
| muajam-tabarani-saghir | en, ur |
| musannaf-ibn-abi-shaybah | en, ur |
| musnad-ahmed | en, ur |
| mustadrak | en, ur |
| sahih-ibn-khuzaymah | en, ur |
| shamail-tirmazi | en, ur |
| silsila-sahih | en, ur |
| sunan-al-daraqutni | en, ur |
| sunan-darmi | en, ur |
| nawawi | ur (no new source) |
| qudsi | ur (no new source) |
| dehlawi | ur (no new source) |
