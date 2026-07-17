# Final Verified Audit + Fix Plan — hadith-api-toon (31 editions × 14 gaps)

**Scope:** 31 editions, 14 gap definitions, 434 gap-investigations. 31 finder agents read real files per edition; real-fix candidates were re-verified by agents that re-opened cited files and checked external sources. All cited files below were confirmed to exist (repo total: 11,605 `.toon` files).

## 1. Per-Gap Verified Status

| Gap | Description | Real-fix editions | Intentional | Already-fixed / False-positive | Files affected (real) | Confirmed real |
|-----|-------------|-------------------|------------|--------------------------------|----------------------|----------------|
| 1 | HN alignment AR vs translations | 5 | 1 | 25 | ~4,950 (bukhari all-translations) | YES (bukhari, mustadrak confirmed; ibnhibban, muslim, nasai confirmed) |
| 2 | Cross-section duplicate arabic = misfile | 4 | 16 | 11 | ~20 rows | YES (fath-al-rabbani, shamail, virtues, muslim-sec0 confirmed) |
| 3 | info.toon section index bounds mismatch | 0 | 1 (malik composite) | 30 | 0 | n/a |
| 4 | Section-boundary continuity gaps outside index | 0 | 5 | 26 | 0 | n/a |
| 5 | Bidi control chars (U+200E/F, U+202A-E, U+2066-69) | 1 (nasai) | 0 | 30 | 1 file, 27 rows | YES |
| 6 | NFC normalization (combining-mark order) | ~28 | 2 (nasai, virtues: "internally consistent") | 1 (muajam optional) | **~5,045 files** (my scan; prompt's 3,373 was a partial sample) | YES — every re-verified gap-6 fix came back CONFIRMED; zero refuted |
| 7 | Intro defects (wrong-script / runaway-loop / truncation) | 15 | 0 | 16 | 15 info.toon files | YES (aladab, bayhaqi, bulugh, ibnmajah, malik, mishkat, musannaf, nawawi, riyad, shamail, virtues confirmed; mishkat has extra CJK damage audit missed) |
| 8 | Schema/JSON-LD leakage into data fields | 0 | 0 | 31 | 0 | n/a |
| 9 | Non-numeric HN (letter-suffix/range) | 1 (mustadrak) | 4 (bukhari, hisn, ibnhibban, aladab) | 26 | 12 EN files (same root as gap 1) | YES (same CSV corruption as mustadrak gap 1) |
| 10 | Scraping residue appended to translation text | 8 | 0 | 23 | ~250 rows across ~25 files | YES (ibnmajah, malik, muajam, nasai, shamail, silsila, tirmidhi confirmed; **malik + muajam fix regexes need correction**) |
| 11 | Non-canonical grades | 11 | 2 (nasai-kubra, daraqutni scholarly terms) | 18 | ~700 rows | YES (abudawud, bayhaqi, ibnmajah, malik, mishkat, mustadrak, nasai, sahih-ibn-khuzaymah, shamail, sunan-darimi, virtues confirmed) |
| 12 | `hadiths[count]` header / count mismatch | 2 | 0 | 29 | 7 files | YES (muajam, mustadrak; mustadrak same root as gap 1) |
| 13 | metadata.toon lacks `sections[` header | **0 effective** (see §4) | 20+ | rest | 0 | **REFUTED** — 0 of 122 metadata.toon files repo-wide have `sections[`; it is the universal schema, not a defect. Only bukhari arguably needs per-language index (info.toon is AR-centric) |
| 14 | narrator_chain numeric/garbage | 5 | 0 | 26 | ~91 rows | YES (malik, mishkat, muajam, silsila, virtues confirmed) |

**Totals:** ~33 confirmed-real-fix gaps across ~5,200 files. Gap #6 (NFC) dwarfs all others (~5,045 files, mechanical). Excluding NFC, ~155 files need real fixes.

---

## 2. Confirmed Real-Fix Gaps — Exact Fix, Risk, Mechanical vs Judgment

### MECHANICAL (safe, scripted, idempotent, no semantic judgment)

**Gap #6 — NFC normalization (~5,045 files, 28 editions)**
- Fix: `python3 -c "import unicodedata,glob; [open(f,'w',encoding='utf-8').write(unicodedata.normalize('NFC',open(f,encoding='utf-8').read())) for f in glob.glob('editions/**/*.toon',recursive=True)]"` then verify `normalize('NFC',x)==x` post-pass and header-count==row-count invariant.
- Risk: LOW. Arabic cases are pure length-preserving reordering (shadda/vowel swap). Bengali (U+09DF→U+09AF+U+09BC) and Hindi (U+095B→U+091C+U+093C) nukta cases DO change length but are canonical NFC transforms — render identically. Idempotent. See §6 for full risk assessment.
- Type: **mechanical, repo-wide batch**

**Gap #5 — nasai bidi control chars (1 file)**
- File: `editions/nasai/sections/36.toon` (27 rows, HN3939–3965)
- Fix: strip U+200F from arabic field: `''.join(c for c in text if ord(c) not in {0x200E,0x200F,0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069})`
- Risk: LOW (visible rendering unaffected; removes stray RTL marks from AI-recovery pipeline). Type: **mechanical**

**Gap #10 — scraping residue stripping (6 of 8 editions, regex-correctable)**
- `ibnmajah`: strip `\n?Sunnan e Ibn e Maja Hadees: \d+ Arabic Hadees: \d+$` from 3 EN rows (`editions/ibnmajah/translations/en/sections/15.toon` HN2490,2497; `sections/9.toon` HN1955)
- `nasai`: strip `n?Sunnan e Nisai Hadees: \d+ Arabic Hadees: \d+` from 121 rows (en/fr/id/tr sections 0,1,14,35,51)
- `shamail-tirmidhi`: strip `\n?شمائل\s*ترمذی\s*حدیث\s*:\s*\d+\s*عربی\s*حدیث\s*:\s*$` from UR `sections/{0,55,56}.toon`
- `silsila-sahih`: strip `Al-Silsila-tu-Ahadees-e-Sahiha Hadees: \d+ Arabic Hadees:?\\s*$` from 10 EN rows
- `tirmidhi`: strip `Jam e Tirmazi Hadees: \d+ Arabic Hadees: \d+` from 33 rows (en/roman-ur)
- `sunan-al-daraqutni`: clean `chapter_intro` `بَابُباب` residue (split AR/UR boundary)
- Risk: LOW (removes appended boilerplate, leaves hadith text intact). Type: **mechanical** (regex)
- **malik gap #10 and muajam gap #10 need regex correction** (see §3)

**Gap #11 — grade canonicalization (mechanical subset)**
- `ibnmajah`: replace `Da’if` (U+2019) → `Da'if` (ASCII) across 557 rows; `Da,if`→`Da'if`; `Da\`if (Weak)`→`Da'if`
- `nasai`: `Da if`→`Da'if` (8), `Daif`→`Da'if` (5)
- `sahih-ibn-khuzaymah`: strip leading `: ` from 183 grade rows
- `bayhaqi`: split 2 verbose `منکر۔ اخرجہ الحاکم...` → grade=`منکر`, note to reference
- Risk: LOW. Type: **mechanical** (string replace)

**Gap #7 (mechanical subset)**
- `bayhaqi`: replace `سunan`→`سنن` at start of intro_ur (`editions/bayhaqi/info.toon`)
- `bulugh-al-maram`: replace literal `\n` with real newlines in intro_ur
- `nasai-kubra`: replace `سunan`→`سنن`, `آرنج`→`ترتیب` in intro_ur
- `musannaf-ibn-abi-shaybah`: replace `کو含اتے`→`رکھتا`, `آرنج`→`ترتیب` in intro_ur
- Type: **mechanical** (single-field byte replace)

**Gap #14 (mechanical subset)**
- `silsila-sahih`: clear 51 numeric narrator_chain values in `sections/1.toon` (set to `''`)
- Type: **mechanical**

**Gap #12 (mechanical subset)**
- `muajam-tabarani-saghir`: fix `translations/en/sections/2.toon` header `hadiths[522]`→`hadiths[520]`
- Type: **mechanical**

### JUDGMENT (requires human/scholarly decision or content re-translation)

**Gap #1 (all 5) — HN re-keying**
- `bukhari` (HIGH, ~48K mismatches): re-key ALL translation rows to AR hadithnumber; bn/0.toon fabricated 7371+ sequence must re-index to AR 272–7563; combined-string HNs (`272, 273`) either preserved at same row index or split. **Largest single data-integrity defect in repo.** Requires schema decision on combined rows.
- `mustadrak` (HIGH, 12 EN sections): re-serialize with proper CSV writer; merge spurious `""<text>""` rows back into parent hadith; restore integer HNs. Same root cause as gaps #9/#12.
- `ibnhibban` (LOW, 1 file): re-key `translations/en/sections/0.toon` HN column from AR `sections/0.toon` (restore `book : HN` cross-ref strings; UR already matches)
- `muslim` (MEDIUM, tr 3 sections): regenerate `translations/tr/sections/{1,15,32}.toon` for missing 49 tail HNs, or append English-fallback
- `nasai` (MEDIUM): add missing id translations for HN3945,3965 in `translations/id/sections/36.toon`
- Type: **judgment** (schema decisions, content regeneration)

**Gap #2 (4 editions) — duplicate hadith resolution**
- `fath-al-rabbani`: merge HN145→144, 153→152, 180→179 (within-section identical rows; source marker `۔ (۱۴۴، ۱۴۵)۔` confirms restructuring artifact)
- `shamail-tirmidhi`: 3 cross-section boundary dups (HN107/108, 276/277, 384/385) + 12 within-section dups — needs reference-numbering verification
- `virtues`: `sections/22.toon` HN64 vs HN66 intra-section identical — likely filing error
- `muslim`: decide whether `sections/0.toon` HN7564 (dup of sec56 HN7563) should be removed
- Type: **judgment** (scholarly numbering decision)

**Gap #7 (judgment subset)**
- `abudawud`: re-serialize intro_bn/intro_ur as proper YAML block scalars; regenerate intro_ru (mixed Latin/Cyrillic); strip intro_fr `Voici la traduction...` preamble; decide on intro_roman-ur stub
- `aladab-almufrad`: rewrite intro_ur (remove `manners`/`NARRATIONS`/`اتیکتات` Latin leakage)
- `ibnmajah`: re-translate truncated intros (roman-ur, bn, hi); fix intro_ur KATAKANA `イン`+ASCII `السITTاہ`; dedupe `### اس کے خصوصیات`; strip intro_fr preamble; drop redundant default `intro`
- `malik`: rewrite intro_ur (Cyrillic `پراکٹس`, Devanagari `کوور`, `کٹیلاک`, `موالا ملک`→`موطأ مالك`)
- `mishkat`: fix intro_hi — replace Arabic `فقه` AND **CJK `方面` (U+65B9 U+9762) the original audit MISSED** with Devanagari
- `musnad-ahmad`: rewrite intro_ur (`Individual`, `کٹیلاک`→`مجموعہ`, `سنیہ`→`سنت`)
- `nasai`: rewrite intro_ur (mixed-script stub); add missing intro_ru, intro_ta
- `nawawi`: restore full English intro/intro_en (currently truncated mid-word `migrati`)
- `riyadussalihin`: replace `manners`→`اخلاق` in intro_ur
- `shamail-tirmidhi`: re-translate intro_ur (10 English intrusions: anners, QUALITIES, lifestyle, Generosity, etc.)
- `virtues`: complete all 4 truncated intros (intro, intro_en, intro_ar, intro_ur end mid-sentence)
- Type: **judgment** (requires re-translation / scholarly completion)

**Gap #11 (judgment subset)**
- `abudawud`: canonicalize 4 multi-grade cells (HN95/281/286/287) — restore `1: X\n2: Y` structure or split to list
- `malik`: reconstruct `sections/47.toon` HN163502 7-col row (grade=`Da'if`, ref=`Muwatta Imam Malik 1635`, chapter_intro=`كتاب حسن الخلق`); fill empty sec0 grades
- `mishkat`: re-source true grade for 12 column-shifted rows (move `Mishkat al-Masabih N` back to reference, `Book X, Hadith Y` to international_number)
- `mustadrak`: fix `sections/1.toon` HN9 broken grade (strip `\"` artifacts, canonicalize `هذا على شرط مسلم`)
- `shamail-tirmidhi`: move `sections/5.toon` HN45 arabic commentary out of grades field
- `sunan-darimi`: re-escape embedded `","` in 34 arabic fields so rows parse to 7 cols
- Type: **judgment** (requires re-sourcing grades or CSV re-serialization)

**Gap #14 (judgment subset)**
- `malik`: restore `sections/47.toon` HN163502 (same as gap #11)
- `mishkat`: move chapter-name from narrator_chain (col5) to chapter_intro (col6) on 12 rows (after gap #11 fix)
- `muajam-tabarani-saghir`: clear 25 Urdu-text rows in `sections/1.toon` narrator_chain; decide policy on chapter_intro field (currently echoes HN for all 18,326 rows)
- `virtues`: unescape embedded quotes in 7 EN rows (`translations/en/sections/{4,8,15,21,25,26}.toon`)
- Type: **judgment**

---

## 3. Fix-Regex Corrections Required (verifier caught errors)

Two gap-#10 fixes as written by finders match 0 rows — must be corrected before execution:
- **malik gap #10**: cited regex `?(Muwatta|Mouta|Mutta|Mal)\w* (Imam )?Malik Hadith ?: ?\d+ Hadith arabe ?:?$` fails because (a) lines end with `:"` not bare `:`, (b) `\xa0` non-breaking spaces present in ~10 rows, (c) `\n` escape prefixes ignored. Corrected regex: `r'\s*[-,:.]?\s*(?:\\n)?\s*(Muwatta|Mouta|Mutta|Malik|Mal)?\s*\w*\s*(Imam\s+)?Malik Hadith\s*[:\xa0]?\s*\d+\s+Hadith arabe\s*[:\xa0]?"?\s*$'` catches 29/33; remaining 4 use `Hadith de l'Imam Malik` / `Malik. Hadith` variants. Actual residue count is **33 rows across 15 files** (audit undercounted as 26).
- **muajam-tabarani-saghir gap #10**: cited regex `\s+\d{1,4}\s*$` misses 6 five-digit residue cases (10400, 10473, 11778, 11958, 14289, 17192). Broaden to `\s+\d+\s*$`. 53 rows confirmed.

**mishkat gap #7**: audit missed 2 additional CJK chars `方面` (U+65B9 U+9762) at intro_hi offset 319–320. Complete fix must replace all 4 stray chars, not just the 2 Arabic.

---

## 4. "Document as Intentional" List

| Gap | Editions | Why legit |
|-----|----------|----------|
| 2 (cross-chapter repetition) | abdurrazzaq, abudawud, bayhaqi, bukhari, malik, mishkat, muajam-tabarani-saghir, musannaf-ibn-abi-shaybah, musnad-ahmad, nasai, nasai-kubra, riyadussalihin, sahih-ibn-khuzaymah, silsila-sahih, sunan-al-daraqutni, tirmidhi | Canonical hadith practice: same narration cited under multiple topical chapters with distinct HN. Not misfiles. |
| 3 (composite HN convention) | malik | Composite HNs `14601`=`146` spanning two books; index tracks real base HN. |
| 4 (boundary gaps covered by sec0 / source numbering) | bukhari (combined rows in sec0), malik (sec0 catch-all), mishkat (sec0 intro HN 3899–4627), musnad-ahmad (per-companion numbering resets), nasai (sec0 + 18 absent source HNs), silsila-sahih (HN 52–204 never assigned by source) | All gaps are recorded in info.toon index or are source numbering conventions. |
| 9 (letter-suffix HN) | aladab-almufrad (348a/b, 1001b, 1319b), bukhari (402b, 1390c, combined rows), hisn (75a), ibnhibban (`book : HN` cross-refs) | Source-faithful variant-narration / cross-reference notation. Preserve as-is. |
| 13 (metadata.toon lacks `sections[`) | **ALL 31 editions** — 0 of 122 metadata.toon files repo-wide contain `sections[` | **Universal repo schema**: section index centralized once in `info.toon`; per-language metadata.toon is a thin language descriptor by design. Re-verification REFUTED bayhaqi/malik/mishkat/fath-al-rabbani gap-13 real_fix claims. Only bukhari is borderline (info.toon AR-centric, per-language section files genuinely differ) — but even there, adding sections[] to 10 metadata.toon duplicates info.toon. Recommend: **document as intentional repo-wide; do not add sections[] to metadata.toon.** |
| 11 (scholarly composite grades) | nasai-kubra (Sahih/Sound, Daif/Weak English synonyms — optional mapping), sunan-al-daraqutni (مرسل/موقوف/مضطرب/مقطوع are legitimate Daraqutni grading vocabulary) | Meaningful scholarly terms, not garbage. Optional canonicalization only. |
| 14 (narrator_chain empty by design) | bulugh-al-maram, lulu-wal-marjan, tirmidhi, most editions | Isnad embedded inline in the arabic field; narrator_chain column intentionally unpopulated. Empty ≠ garbage. |

---

## 5. Already-Fixed / False-Positive List

- **Gap 3, 4, 8, 12**: uniformly false-positive / already-fixed across all 31 editions (index bounds match, boundaries accounted for, zero schema leakage, header counts match — except the 2 real gap-12 cases).
- **Gap 8** (schema/JSON-LD leakage): 0 hits in any hadith row across all 31 editions. Fully false-positive.
- **Gap 7 false-positives**: abdurrazzaq, dehlawi, fath-al-rabbani, hisn, ibnhibban, lulu-wal-marjan, muajam-tabarani-saghir, muslim, mustadrak, qudsi, sahih-ibn-khuzaymah, sunan-al-daraqutni, sunan-darimi, tirmidhi (14 editions — no intros or clean intros).
- **Gap 14 false-positives**: 22 editions where narrator_chain is uniformly empty (isnad in arabic field) — no garbage to clean.

---

## 6. Prioritized Execution Plan

### Phase 1 — Mechanical safe batch fixes (do first, lowest risk, highest file count)

1. **Gap #6 NFC normalization (repo-wide, ~5,045 files)** — single Python one-liner over `editions/**/*.toon`. Idempotent. Verify `normalize('NFC',x)==x` and header-count==row-count after. **This single fix resolves ~96% of all affected files.**
2. **Gap #5 nasai bidi strip** (1 file, 27 rows) — strip U+200F from `editions/nasai/sections/36.toon`.
3. **Gap #10 residue stripping** (6 editions, regex-corrected per §3) — ibnmajah, nasai, shamail-tirmidhi, silsila-sahih, tirmidhi, sunan-al-daraqutni. Apply corrected regexes.
4. **Gap #11 mechanical grade canonicalization** — ibnmajah (Da'if apostrophe), nasai (Da if/Daif), sahih-ibn-khuzaymah (leading `: `), bayhaqi (verbose منکر split).
5. **Gap #7 mechanical intro byte-replaces** — bayhaqi, bulugh-al-maram, nasai-kubra, musannaf-ibn-abi-shaybah.
6. **Gap #12 muajam header fix** — `translations/en/sections/2.toon` 522→520.
7. **Gap #14 silsila-sahih** — clear 51 numeric narrator_chain rows.

### Phase 2 — Judgment fixes requiring schema/content decisions

8. **Gap #1 bukhari HN re-keying** (HIGH — largest data-integrity defect) — decide combined-row policy, re-index bn/0.toon, re-key all translations to AR HN.
9. **Gap #1 mustadrak CSV re-serialization** (HIGH — fixes gaps #1/#9/#12 together) — re-serialize 12 EN files with `csv` module, merge spurious rows, restore integer HNs, recompute header counts.
10. **Gap #1 muslim (tr), nasai (id), ibnhibban (en sec0)** — regenerate/re-key missing translations.
11. **Gap #2 dedup** — fath-al-rabbani, shamail-tirmidhi, virtues, muslim/sec0 (scholarly numbering review).
12. **Gap #7 re-translations** (11 editions) — abudawud, aladab, ibnmajah, malik, mishkat (+CJK fix), musnad-ahmad, nasai, nawawi, riyadussalihin, shamail-tirmidhi, virtues.
13. **Gap #11 judgment grades** — abudawud (multi-grade cells), malik (col-shift), mishkat (12 col-shifted), mustadrak (HN9), shamail (HN45), sunan-darimi (34 CSV-escape).
14. **Gap #14 judgment** — malik (HN163502), mishkat (move col5→col6), muajam (clear + chapter_intro policy), virtues (unquote EN rows).

### Phase 3 — Document as intentional (no code change)

15. **Gap #13 repo-wide**: add a single line to repo README/CONTRIBUTING: "Per-translation `metadata.toon` intentionally carries only language descriptors; the section index lives in `info.toon sections[]`." Do NOT add `sections[]` to 122 metadata.toon files.
16. Document intentional cross-chapter repetition (gap 2), composite HN (gap 3 malik), source numbering gaps (gap 4), letter-suffix HN (gap 9), scholarly composite grades (gap 11 nasai-kubra/daraqutni), empty narrator_chain by design (gap 14).

---

## 7. NFC Normalization Risk Assessment (Gap #6, ~5,045 files)

**My independent scan found ~5,045 non-NFC files across 31 editions** (the prompt's 3,373 figure was a partial sample — sahih-ibn-khuzaymah alone has 1,329 and musnad-ahmad 1,214).

**Root cause (uniform):** Arabic combining marks stored in non-canonical order — ARABIC SHADDA (U+0651, combining class 33) placed BEFORE the harakat (FATHA U+064E cc30, KASRA U+0650, DAMMA U+064F). NFC requires ascending combining class, so vowel must precede shadda. Affects every Arabic-bearing file. Secondary causes: Bengali U+09DF (YYA) precomposed→U+09AF+U+09BC; Hindi U+095B→U+091C+U+093C; Urdu ALEF+HAMZA decomposed→precomposed U+0623.

**Risk: LOW.** Justification:
- Arabic cases are **length-preserving pure reordering** — `len(orig)==len(NFC)`, identical rendering, no data loss.
- Bengali/Hindi nukta cases **change length** (e.g. bulugh `translations/ur/sections/2.toon` 115581→115549) but are the **canonical NFC form** — render identically, just use decomposed codepoints.
- Idempotent: re-running is a no-op (verified for dehlawi).
- Header lines are pure ASCII (`hadiths[N]{...}:`), so NFC leaves them byte-identical → header-count==row-count invariant preserved.
- Every re-verified gap-6 fix (abdurrazzaq, abudawud, aladab, bayhaqi, bukhari, bulugh, dehlawi, fath, hisn, ibnhibban, ibnmajah, lulu, malik, mishkat) came back **CONFIRMED**; zero refuted.

**Precautions:**
1. Run on a single edition first, diff-render a sample row before/after to confirm visual identity.
2. Verify post-pass: `normalize('NFC',x)==x` for all files AND header-count==row-count for all section files (NFC must not merge/split rows — it only touches data fields).
3. Two finder classifications diverge: `nasai` and `virtues` gap-6 marked false_positive ("internally consistent; NFC optional, not a defect"). My scan shows 197 and 34 non-NFC files respectively. These are the same non-canonical ordering — recommend including them in the batch for byte-uniformity, but flag as optional (low severity, rendering-identical).
4. Commit the NFC pass as an isolated commit for easy revert if any downstream byte-exact consumer breaks.

**One-time vs ongoing:** Recommend adding `unicodedata.normalize('NFC', content)` to the `.toon` writer/emitter so future writes are canonical (lulu-wal-marjan finder suggested this), preventing recurrence.
