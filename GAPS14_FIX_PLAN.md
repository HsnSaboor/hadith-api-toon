# GAPS14_FIX_PLAN.md
## Full execution fix plan for all 14 completeness gaps (GAPS14_AUDIT.md verified)

Branch `audit-fixes`. Plan only. All fixes verified by agents reading real files + re-opening cited files.

---

## PHASE A — Mechanical safe fixes (scripted, idempotent, no semantic judgment)

### A1. #6 NFC normalization (~5,045 files, 28 editions) — LARGEST
**What:** content not in NFC form (combining-mark order differs), breaking dedup/search.
**Fix:** repo-wide `unicodedata.normalize('NFC', content)` on every `.toon` file.
```python
import unicodedata, glob, io
for f in glob.glob('editions/**/*.toon', recursive=True):
    t = open(f, encoding='utf-8').read()
    n = unicodedata.normalize('NFC', t)
    if n != t: open(f, 'w', encoding='utf-8').write(n)
```
**Verify post:** every file `normalize('NFC',x)==x`; header-count==row-count invariant preserved (NFC is length-preserving for Arabic; Bengali U+09DF↔U+09AF+U+09BC and Hindi nukta are canonical NFC, render identical). Load 1 file in viewer.html → parses.
**Risk:** LOW. Idempotent. Test viewer.html rendering after (one sample per script family).
**Type:** mechanical, repo-wide batch.

### A2. #5 bidi control chars (1 file — nasai sec36 AR)
**What:** U+200F embedded in 27 rows of `editions/nasai/sections/36.toon` (glm-injected during AI recovery).
**Fix:** strip bidi marks from all data fields:
```python
BIDI = {0x200E,0x200F,0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069}
for f in ['editions/nasai/sections/36.toon','editions/nasai/translations/ur/sections/36.toon']:
    t=open(f,encoding='utf-8').read(); open(f,'w',encoding='utf-8').write(''.join(c for c in t if ord(c) not in BIDI))
```
**Verify:** `grep -rlP '[\x{200E}\x{200F}\x{202A}-\x{202E}\x{2066}-\x{2069}]' editions/` → 0.
**Risk:** LOW (invisible marks, rendering unaffected). Type: mechanical.

### A3. #10 scraping residue strip (8 editions)
Strip appended scraper boilerplate from end of translation text:
- **ibnmajah** (3 EN rows, HN2490/2497/1955): `sections/9.toon,15.toon` — strip `\n?Sunnan e Ibn e Maja Hadees: \d+ Arabic Hadees: \d+$`
- **nasai** (121 rows): `translations/{en,fr,id,tr}/sections/{0,1,14,35,51}.toon` — strip `n?Sunnan e Nisai Hadees: \d+ Arabic Hadees: \d+`
- **shamail-tirmidhi** (UR): `translations/ur/sections/{0,55,56}.toon` — strip `\n?شمائل\s*ترمذی\s*حدیث\s*:\s*\d+\s*عربی\s*حدیث\s*:\s*$`
- **silsila-sahih** (10 EN rows): `translations/en/sections/{2,3,8,9,12}.toon` — strip `Al-Silsila-tu-Ahadees-e-Sahiha Hadees: \d+ Arabic Hadees:?\s*$`
- **tirmidhi** (33 rows): `translations/{en,roman-ur}/sections/*.toon` — strip `Jam e Tirmizi Hadees: \d+ Arabic Hadees: \d+`
- **sunan-al-daraqutni**: `sections/*.toon` chapter_intro — clean `بَابُباب` residue (split AR/UR boundary)
- **malik** (33 FR rows, **regex correction needed**): `translations/fr/sections/{0,16,18,20-25,29,31,39,41,43,44,49}.toon` — use `\d+` not `\d{1,4}`
- **muajam-tabarani-saghir** (53 UR rows, **regex correction**): `translations/ur/sections/*.toon` — use `\d+` not `\d{1,4}`
**Verify:** re-grep each residue pattern per edition → 0.
**Risk:** LOW (removes appended boilerplate, hadith text intact). Agent spot-check 3 rows/edition. Type: mechanical (regex) + verify.

### A4. #11 grade canonicalization (mechanical subset, 7 editions)
- **ibnmajah**: `Da'if` (U+2019 → ASCII `'`, 557 rows); `Da,if`→`Da'if`; `Da\`if (Weak)`→`Da'if` across `sections/*.toon`
- **nasai**: `Da if`→`Da'if` (8), `Daif`→`Da'if` (5) across `sections/*.toon`
- **sahih-ibn-khuzaymah**: strip leading `: ` from 183 grade rows
- **bayhaqi**: split 2 verbose `منکر۔ اخرجہ الحاکم...` → grade=`منکر`, move rest to reference field
- **virtues** `sections/15.toon` HN44: unescape embedded-quote field leak
- **abudawud** (judgment — multi-grade): keep but normalize separators in `sections/1.toon` HN95/281/286/287, HN392
- **musannaf** `No Data Available` → empty (verify already done in prior fix)
**Verify:** re-grep `: Sahih`/`Da if`/`No Data Available` → 0.
**Risk:** LOW (string replace, no semantic change). Type: mechanical.

### A5. #7 intro byte-replace (4 editions, mechanical subset)
- **bayhaqi** `info.toon` intro_ur: `سunan`→`سنن` at start
- **bulugh-al-maram** `info.toon` intro_ur: literal `\n` → real newline
- **nasai-kubra** `info.toon` intro_ur: `سunan`→`سنن`, `آرنج`→`ترتیب`
- **musannaf-ibn-abi-shaybah** `info.toon` intro_ur: `کو含اتے`→`رکھتا` (CJK artifact), `آرنج`→`ترتیب`
**Verify:** re-grep these substrings → 0.
**Risk:** LOW (single-field byte replace). Type: mechanical.

### A6. #14 silsila narrator_chain clear (mechanical)
**silsila-sahih** `sections/1.toon`: 51 numeric `narrator_chain` values (`"1"`) → `""` (empty).
**Verify:** no numeric narrator_chain remains in silsila sec1.
**Risk:** LOW. Type: mechanical.

### A7. #12 muajam header fix (mechanical)
**muajam-tabarani-saghir** `translations/en/sections/2.toon`: header `hadiths[522]` → `hadiths[520]` (match actual rows).
**Verify:** header count == row count.
**Risk:** LOW. Type: mechanical.

---

## PHASE B — Judgment fixes (agent per instance, semantic decisions)

### B1. #1 HN alignment (5 editions — LARGEST, HIGH severity)
- **bukhari** (~48K mismatches across all 10 langs): bn/sec0 fabricated `7371+` sequence instead of AR `272–7563`. **Fix:** re-key EVERY translation row's hadithnumber from the AR source row at the same index. For combined-string HNs (`"272, 273"`): **schema decision needed** — preserve at same row index (current) OR split into 2 rows. Recommend: preserve combined at same index (matches AR; viewer handles). Algorithm: per section, per lang, set `trans_HN[k] = AR_HN[k]`. Verify 0 mismatches after.
- **mustadrak** (12 EN sections `{1,27,28,29,30,32,36,42,45,47,49,51}.toon`): CSV corruption (spurious `""<text>""` rows merged into parent, integer HNs lost). **Fix:** re-serialize with python csv writer, split merged rows back, restore integer HNs from AR. Same root as #9/#12.
- **ibnhibban** `translations/en/sections/0.toon`: re-key HN column from AR `sections/0.toon` (restore `book:HN` cross-ref strings; UR already matches).
- **muslim** `translations/tr/sections/{1,15,32}.toon`: 49 missing tail HNs — regenerate or English-fallback `[AI-translation]`.
- **nasai** `translations/id/sections/36.toon`: add missing id translations for HN3945, 3965 (LLM from AR, `[AI-translation]`).
**Type:** judgment (schema decisions + content regen). HIGH risk — biggest data-integrity defect. Verify per-lang HN parity after.

### B2. #2 cross-section duplicate misfiles (4 editions)
- **fath-al-rabbani** `sections/{2,3}.toon`: merge HN145→144, 153→152, 180→179 (within-section identical rows; source marker `۔ (۱۴۴، ۱۴۵)۔` confirms restructuring artifact). Delete duplicate rows, renumber.
- **muslim** `sections/0.toon`: remove duplicate HN7564 (keep one).
- **shamail-tirmidhi** `sections/{1,8,10,12,14,15,24,33,36,39,40,41,54,55}.toon`: 3 cross-section boundary dups — investigate each, remove genuine misfile, keep legit.
- **virtues** `sections/22.toon` HN64 vs HN66: investigate which is misfiled, correct.
**Type:** judgment per group. Do NOT auto-dedupe (would delete legit cross-chapter repetition — 16 editions confirmed legit).

### B3. #11 grade column-shift (4 editions, judgment)
- **abudawud** `sections/1.toon` HN95/281/286/287 (multi-grade) + HN392 (Sahih/Shadh): normalize.
- **malik** `sections/{0,41,47,58,59,60}.toon`: spelling fixes + **HN163502 column-shift** (restore 7 cols — field leaked into wrong column).
- **mishkat** `sections/{0,4,5,7,9,10,11,13,23,25,26,29}.toon`: 12 column-shifted rows (move chapter name col5→col6).
- **sunan-darimi** `sections/{0,1,2,5,11,12}.toon`: 34 rows unescaped quotes (re-quote with python csv).
- **mustadrak** `sections/1.toon` HN9: broken grade commentary (repair or empty).
- **shamail-tirmidhi** `sections/5.toon` HN45: arabic commentary in grade field (move to reference).
**Type:** judgment (column structure repair). HIGH care.

### B4. #14 narrator_chain relocate (4 editions, judgment)
- **malik** `sections/47.toon` HN163502: restore 7 columns (narrator_chain field has wrong content).
- **mishkat** `sections/{0,4,5,7,9,10,11,13,23,25,26,29}.toon`: 12 rows — move chapter name col5→col6 (overlaps B3).
- **muajam-tabarani-saghir** `sections/1.toon`: clear 25 Urdu-text rows in narrator_chain (set empty or rename field).
- **virtues** `translations/en/sections/{4,8,15,21,25,26}.toon`: unescape embedded quotes in narrator_chain.
**Type:** judgment.

---

## PHASE C — Intro re-translation (11 editions, judgment)
#7 intro defects needing re-translation (LLM from intro_en/intro_ar, or scholarly):
- abudawud `info.toon` (intro_bn, intro_ur, intro_ru, intro_fr, intro_roman-ur)
- aladab-almufrad `info.toon` (intro_ur)
- ibnmajah `info.toon` (intro_roman-ur, intro_ur, intro_bn, intro_hi, intro_fr, intro)
- malik `info.toon` (intro_ur Cyrillic/Devanagari contamination)
- mishkat `info.toon` (intro_hi: Arabic فقه + CJK 方面)
- musnad-ahmad `info.toon` (intro_ur: Individual, کٹیلاک, سنیہ)
- nasai `info.toon` (intro_ur mixed-script; add intro_ru, intro_ta)
- nawawi `info.toon` (intro, intro_en truncated mid-word)
- riyadussalihin `info.toon` (intro_ur: `manners`→`اخلاق`)
- shamail-tirmidhi `info.toon` (intro_ur: 10 English intrusions)
- virtues `info.toon` (intro, intro_en, intro_ar, intro_ur all truncated)
**Fix:** LLM (glm-5-2) translate from clean intro_en/intro_ar, or scholarly source. Mark `[AI-translation]` if LLM.
**Type:** judgment + LLM.

---

## PHASE D — Document intentional (no file change)
Update KNOWN_ISSUES.md with:
- **#2 cross-section dup**: 16 editions legit cross-chapter repetition (abdurrazzaq, abudawud, bayhaqi, bukhari, malik, mishkat, muajam, musannaf, musnad-ahmad, nasai, nasai-kubra, riyadussalihin, sahih-ibn-khuzaymah, silsila-sahih, sunan-al-daraqutni, tirmidhi). Do NOT dedupe.
- **#3 index bounds**: all 31 match or intentional (malik composite BBBHH scheme).
- **#4 boundary gaps**: 6 intentional numbering schemes (malik BBBHH, mishkat sec0 3899-4627, musnad-ahmad per-companion resets, bukhari combined rows, nasai sec0 Uncategorized + 18 absent source HNs, silsila HN52-204 never assigned).
- **#9 non-numeric HN**: 4 intentional repeat-variants (aladab 348a/b/1001b/1319b, bukhari 402b/1390c combined, hisn 75a, ibnhibban book:HN cross-refs). Keep.
- **#13 metadata header**: REFUTED — 0/122 metadata.toon have `sections[` header; universal repo schema (section index centralized in info.toon). NOT a defect.
- **#11 synonyms**: nasai-kubra (Sahih/Sound, Daif/Weak), sunan-al-daraqutni (مرسل/موقوف/مضطرب scholarly terms) — optional mapping, leave.
- **#14 inline-isnad**: bulugh/lulu/tirmidhi/most — isnad embedded in arabic field, narrator_chain empty by design. Leave.
**Type:** documentation.

---

## PHASE E — Verify (blocking, after each phase)
1. Re-grep: `#5 bidi`=0, `#8 JSON-LD`≤2 (metadata refs), `#10 residue`=0, `#11 bad grades`=0, `#12 count_literal`=0 → expect drops.
2. NFC invariant: `normalize('NFC',x)==x` for all files.
3. Header-count==row-count invariant preserved across all touched files.
4. viewer.html regression: load 1 sample per fix type → metadata parses, hadith renders, NFC-normalized text shows correctly.
5. Commit per phase: `fix(gaps14-A): NFC + bidi + residue + grades (mechanical)`, etc.

---

## Execution order + risk
1. **Phase A** (mechanical) — A1 NFC, A2 bidi, A3 residue, A4 grades-mech, A5 intro-byte, A6 silsila, A7 muajam. Lowest risk, do first. Test viewer after NFC.
2. **Phase B** (judgment) — B1 HN alignment (biggest), B2 dup merges, B3 grade col-shift, B4 narrator relocate. Agent per instance, verify after each.
3. **Phase C** (intro re-translation) — 11 editions via glm-5-2.
4. **Phase D** (document) — KNOWN_ISSUES update.
5. **Phase E** (verify) — after each phase.

## Scope
- Mechanical: ~5,045 files (NFC) + ~30 files (other mechanical) ≈ 5,075 files
- Judgment: ~50 files (HN re-key bukhari 48K rows across 10 langs, mustadrak 12, ibnhibban 1, muslim 3, nasai 1, dups ~20 rows, grade col-shift ~50 rows, narrator ~91 rows)
- Intro re-translation: 11 info.toon files
- Total: ~5,130 files touched, ~48K rows re-keyed (bukhari), ~5K NFC-normalized, ~250 residue-stripped, ~700 grade-canonicalized, ~91 narrator-fixed, 11 intros re-translated.
