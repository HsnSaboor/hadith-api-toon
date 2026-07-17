# .toon Audit — All Errors Explained (with real before → after)

Source: 31 finder agents read 513 real files, adversarially verified, 2248 raw findings → 428 confirmed.
Every example below is a real byte sequence pulled from the repo. `HN` = hadith number.

Severity: 🔴 data-loss/wrong-content · 🟠 structural · 🟡 cosmetic/schema · ⚪ false-positive-prone

Recoverability column = whether the original correct data still exists somewhere we can pull from:
- `external` = gone, only upstream source (sunnah.com / original) can restore
- `partial` = can truncate bad part, but lost original is gone
- `deletable` = just remove the garbage row/content
- `mechanical` = deterministic recompute, no data loss

---

## P0 — DATA LOSS / WRONG CONTENT (fix first)

### E1 🔴 AI-generated translation preambles (ai_leakage)
**What:** translation rows contain LLM boilerplate the model emitted while translating — not hadith text. The whole row is garbage; real hadith missing.
**Root cause:** translation packs run through an LLM with no output filter; the model's preamble/notes got written into the text field.
**Files:** ibnmajah/fr (32 sections), tirmidhi/roman-ur, muslim/tr, shamail-tirmidhi/ur.
| Before | After |
|---|---|
| `"597","Voici la traduction en français des hadiths que vous avez fournis, incluant la chaîne de narration et le corps du hadith. Tous les contenus sont en français uniquement, comme demandé."` | *row deleted* (HN 597 has no real fr translation; flag as missing) |
**Recoverable:** external. **Fix:** agent identifies preamble rows, deletes them (real text absent → can't reconstruct). Replace with empty + missing marker, or re-pull fr from sunnah.com.

### E2 🔴 AI self-monologue in hadith text (ai_leakage, extreme)
**What:** row contains the model talking to itself, then the loop cuts mid-word.
**Files:** shamail-tirmidhi/ur/25 HN161, bayhaqi/ur/10 HN10342.
| Before | After |
|---|---|
| `"161","…PARAM? No, I think I'm making a mistake in the Urdu translation… Here we go: …"` (50× repeat, truncates) | *row deleted or truncated to first clean sentence + `[corrupt]`* |
**Recoverable:** partial. **Fix:** delete the row (original UR hadith 161 gone).

### E3 🔴 Synthetic fabricated rows (muslim tr "Rüya:")
**What:** 49 rows are English hadith text wrapped in `Hadith <name>:\n Rüya:` — fake Turkish, not a translation.
**Files:** muslim/tr sections 1/15/32.
| Before | After |
|---|---|
| `"2841","Hadith A'isha ra:\n Rüya: A'isha (Allah be pleased with her) reported: "I used to perfume the Messenger…"` | *row deleted*, renumber following tr rows |
**Recoverable:** deletable. **Fix:** delete fabricated rows, renumber, verify tr row count drops by 49 and matches AR parity.

### E4 🔴 JSON-LD scrape residue in translation rows (ibnhibban)
**What:** 4 EN rows replaced entirely by schema.org JSON-LD scraped from en.tohed.com instead of the hadith.
**Files:** ibnhibban/en HN 1139, 3610, 5690, 7174.
| Before | After |
|---|---|
| `"1139","The Prophet M"",""mainEntityOfPage"":{""@type"":""WebPage"",""@id"":""https://en.tohed.com/hadith/sahih-ibn-hibban/1139/""},""inLanguage"":""en"",""isPartOf"":…` | *row deleted* (flag HN 1139 missing en) |
**Recoverable:** external. **Fix:** delete rows, re-pull from en.tohed.com properly OR mark missing.

### E5 🔴 Truncated translation rows (ibnhibban)
**What:** 4 EN rows are 9–14 char fragments while AR+UR have full hadiths.
**Files:** ibnhibban/en HN 139, 3830, 5905, 6503.
| Before | After |
|---|---|
| `"139","The Prophet M"` (then CSV split breaks rest of file) | *flag missing* |
**Recoverable:** external. **Fix:** delete fragment, re-pull.

### E6 🔴 Newline-stripped to bare `n` in Arabic (mustadrak)
**What:** `\n` newlines in the source got stripped to the literal letter `n`, leaving `n` embedded inside Arabic words across ~4,530 AR rows.
**Files:** mustadrak (edition-wide, all AR sections).
| Before | After |
|---|---|
| `…بِمَكَّةَ، ن ثنا عَبْدُ اللَّهِ…` (stray `ن ` inside Arabic) | `…بِمَكَّةَ، ثنا عَبْدُ اللَّهِ…` (stray `n` removed) |
**Recoverable:** partial. **Fix:** regex remove standalone `ن ` / `n ` tokens sitting between Arabic words. **Risk:** some `ن` is a real Arabic letter — agent must review context (only strip where surrounded by Arabic on both sides AND not forming a word).

### E7 🔴 `??` in-word corruption (musannaf-ibn-abi-shaybah)
**What:** real ASCII `??` (not U+FFFD) embedded mid-word in 281 AR + 73 EN rows.
**Files:** musannaf-ibn-abi-shaybah AR + EN.
| Before | After |
|---|---|
| `"518","(۵۱۸) … عَنْ إسْرَائِیلَ ?? عَنْ أَشْعَثَ…"` | `…عَنْ إسْرَائِیلَ، عَنْ أَشْعَثَ…` (replace `?? ` with `، `) |
**Recoverable:** partial. **Fix:** regex ` ?? ` → `، ` (comma) where between Arabic names; `??` mid-word (e.g. `زَ??َرِیَّا`) → unknown char, can't reconstruct, mark.

### E8 🔴 Runaway intro repetition loops (tirmidhi, nasai)
**What:** info.toon intro field repeats a phrase hundreds of times, truncating mid-word — LLM generation loop.
**Files:** tirmidhi/info intro_hi (`छह में से` 384×), nasai/info intro_ur (`پالیسٹائن سے` 134×).
| Before | After |
|---|---|
| `intro_hi: "…छह में से छह में से छह में से …(384×)…छah"` | `intro_hi: "<first clean sentence>"` (truncate loop) |
**Recoverable:** partial. **Fix:** keep text up to first repetition, drop loop. Original intro gone.

### E9 🔴 Hadith numbering cliff (musnad-ahmad sec19)
**What:** sec19 has HN 1740 then jumps to 22865 (~21,000-number gap). Matches info.toon declared range, so upstream data error.
**Files:** musnad-ahmad AR + ur sec19.
**Recoverable:** external-verify. **Fix:** DO NOT renumber. Verify against musnad-ahmad's real numbering (sunnah.com) — likely thousands of hadiths missing between. Document as known-incomplete.

### E10 🔴 5-digit malformed hadith numbers (malik)
**What:** 1,797 rows carry numbers like 14601, 42801, 16701 — exceed total_hadiths=2757. Section 49 has 330 such rows. Mirrored across AR + all 6 translations.
**Files:** malik AR + bn/en/fr/id/tr/ur.
| Before | After |
|---|---|
| `"14601","…"` / `"14602","…"` (5-digit, out of range) | needs external scheme — `14601` may be `book14 hadith601`. Don't strip blind. |
**Recoverable:** external-verify. **Fix:** determine the encoding (global-in-book vs cross-edition). Must verify against malik reference before touching.

### E11 🔴 Whole translation tree corrupted (aladab-almufrad en)
**What:** 56/57 EN files have literal `\n`, backslash-escapes (`\The`, `\I asked`), trailing `""""""`, row 548 `and two good deeds` ×733.
**Files:** aladab-almufrad/translations/en (whole tree).
| Before | After |
|---|---|
| `"…\The Prophet…\n…""""""` | `…The Prophet…` (unescape `\` → ``, dedupe `"""""`) + truncate 733× loop |
**Recoverable:** partial. **Fix:** unescape backslashes, collapse `"""""`→`""`, truncate runaway loops. Original row content lost where looped.

### E12 🔴 CSV-quoting bug, runaway quote sequences (hisn)
**What:** 55 bad rows across 40 of 132 EN files; one logical row split into 4–15 fake fields by `""""""""` sequences.
**Files:** hisn/en (132 files).
| Before | After |
|---|---|
| `"…text""""""""more""""""…` (66 quotes/row) | re-parse: collapse `""""`→`""`, re-quote to 2 fields |
**Recoverable:** mechanical (data is there, just mis-quoted). **Fix:** re-quote: collapse runs of `"`>2 down to `""`, verify field count = 2 per row.

### E13 🔴 Dropped/merged hadiths (lulu-wal-marjan en)
**What:** 281 hadiths merged into others (HN 1+2 merged, 11+12 merged…). metadata claims 1906 but EN has 1625. OCR garbage in row 1.
**Files:** lulu-wal-marjan/en/sections/0,1,54.
| Before | After |
|---|---|
| `"1","I The Prophet ^ J .+!e -rrr,-r- said, …"  "2","The fact which stops me…"` (merged, garbage) | can't split cleanly — original HN1 OCR-garbled |
**Recoverable:** external. **Fix:** flag section incomplete. Don't guess-split (risk worse). Re-pull EN from source.

### E14 🔴 Swapped sections (mishkat)
**What:** translation sections 20/21 are swapped vs AR source (AR sec20=Foods HN3992/72 rows; EN sec20=Hunting HN4064/95 rows; sec21 inverse).
**Files:** mishkat all langs sec20 ↔ sec21.
| Before | After |
|---|---|
| EN/sec20 = Hunting content, EN/sec21 = Foods content | EN/sec20 = Foods, EN/sec21 = Hunting (swap file contents back) |
**Recoverable:** mechanical. **Fix:** swap the two files' contents in each language. Verify row counts match AR after.

### E15 🔴 chapter_intro off-by-one (abdurrazzaq, hisn)
**What:** every section carries the PREVIOUS section's chapter name (abdurrazzaq all 31 files) or sec132's name for all (hisn 66 files 67–132).
**Files:** abdurrazzaq (31 AR), hisn (66 AR).
| Before | After |
|---|---|
| abdurrazzaq/sec2 row: `…chapter_intro":"Book of Purification"` (that's sec1's name) | `chapter_intro":"<sec2's actual name from info.toon index>"` |
**Recoverable:** mechanical. **Fix:** read each section's real name from info.toon section index, overwrite chapter_intro in every row.

### E16 🔴 Cross-script contamination (qudsi)
**What:** wrong-language script inside translations — Korean in Tamil, Russian+Devanagari in Bengali.
**Files:** qudsi bn/te/ta.
| Before | After |
|---|---|
| `ta/sec1: "1","அபு…அல்ல…께서…"` (Korean Hangul in Tamil) | strip non-Tamil glyphs OR flag row (original ta lost) |
**Recoverable:** partial. **Fix:** agent reviews; strip obvious foreign-script runs, flag uncertain.

### E17 🔴 Bengali raw-English + AI labels (abudawud bn)
**What:** bn rows contain English `narrator chain:` / `hadith body:` labels and severe vowel-stripping.
**Files:** abudawud/bn sections 3,5,41,42.
| Before | After |
|---|---|
| `bn/41 row 4497: "narrator chain: <english> hadith body: <bengali>"` | delete the English-label rows; verify AR parity |
**Recoverable:** deletable. **Fix:** delete labeled rows, renumber, verify.

### E18 🔴 Grade field contains wrong language (muajam-tabarani-saghir)
**What:** AR grades field carries Urdu text in 25 rows; 18,301/18,326 rows have empty grades + empty reference + empty narrator_chain.
**Files:** muajam-tabarani-saghir AR.
| Before | After |
|---|---|
| `…"urdu text in grades field","",""…` | move Urdu to correct field or empty it |
**Recoverable:** mechanical. **Fix:** agent identifies which field the Urdu belongs in (likely narrator_chain), relocate.

### E19 🔴 Latin gibberish in Urdu (musannaf-ibn-abi-shaybah ur)
**What:** rows contain `plvvlqj` (Latin nonsense).
**Files:** musannaf-ibn-abi-shaybah/ur HN 5898, 22496.
| Before | After |
|---|---|
| `"5898","…plvvlqj…"` | *flag row corrupt* or strip token |
**Recoverable:** partial. **Fix:** delete row or strip token; can't reconstruct UR.

---

## P1 — STRUCTURAL

### E20 🟠 `hadiths[count]` literal header (bukhari + others)
**What:** header says `hadiths[count]` not real row count. 97 bukhari AR + 5 tr files.
**Files:** bukhari (102), repo-wide uncounted.
| Before | After |
|---|---|
| `hadiths[count]{hadithnumber,arabic,…}:` | `hadiths[7277]{…}:` (real count) |
**Recoverable:** mechanical. **Fix:** script counts data rows, writes `hadiths[N]`. Low risk.

### E21 🟠 Header count mismatch (header says N, actual rows ≠ N)
**What:** declared count in header wrong. 3 confirmed.
**Files:** scattered.
**Recoverable:** mechanical. **Fix:** recompute, rewrite header.

### E22 🟠 Field count mismatch (row has wrong # of quoted fields)
**What:** row not 2 fields (translation) or 7 (AR). 25 confirmed high — but high false-positive rate (awk splits on embedded quotes).
**Files:** editions using python-csv found real 8–10 field rows.
| Before | After |
|---|---|
| AR row with 9 fields (one extra `","`) | re-quote to 7 fields |
**Recoverable:** mechanical (data present, mis-quoted). **Fix:** re-quote with python csv. **Caveat:** 25 = floor, awk-inflated editions hide more.

### E23 🟠 info.toon section index malformed (sahih-ibn-khuzaymah)
**What:** 1,059/1,073 index rows have unescaped embedded `"` in Arabic names → CSV split breaks all columns.
**Files:** sahih-ibn-khuzaymah/info.toon.
| Before | After |
|---|---|
| `…,"ذَكَرْتُهَا,"بَابُ…` (embedded quote breaks split) | `…,"ذَكَرْتُهَا,""بَابُ…` (escape inner `"`→`""`) |
**Recoverable:** mechanical. **Fix:** re-quote: escape embedded quotes. High care (1,059 rows).

### E24 🟠 info_lang_mismatch (ar listed, no translations/ar dir)
**What:** available_languages lists `ar` but AR source lives in `sections/` not `translations/ar`. 7 editions.
**Files:** abudawud, aladab-almufrad, nawawi (+ ibnmajah/muslim uncertain).
| Before | After |
|---|---|
| `available_languages: "ar,bn,en,fr,hi,id,…"` | `available_languages: "bn,en,fr,hi,id,…"` (drop `ar`) |
**Recoverable:** mechanical. **Fix:** remove `ar` (it's the source, not a translation). OR decide `ar` belongs.

### E25 🟠 info_total_mismatch
**What:** info.total_hadiths ≠ actual AR rows. 5 confirmed (bukhari 7563 vs 7277, hisn 267 vs 268, musnad-ahmad 28198 vs 28199).
| Before | After |
|---|---|
| `total_hadiths: "7563"` (bukhari) | `total_hadiths: "7277"` (actual AR sum) |
**Recoverable:** mechanical. **Fix:** sum AR rows, write actual.

### E26 🟠 Missing section file (nasai sec36)
**What:** section 36 absent entirely (AR + all 8 translations + info index skip 35→37). Hadiths 3857–3965 unaccounted.
**Files:** nasai.
**Recoverable:** external. **Fix:** can't fabricate. Re-pull section 36 or document as missing.

### E27 🟠 Section numbering gap (malik 50–55)
**What:** section files 50–55 absent in malik dirs.
**Recoverable:** external-verify. **Fix:** verify if intentional; if not, re-pull.

### E28 🟠 Cross-section duplicate hadith text
**What:** same Arabic narration filed under different HN in different section files. 28 groups across 13 editions.
| Before | After |
|---|---|
| sec3 HN50 and sec7 HN201 = identical Arabic | keep one, flag other as cross-ref; or dedupe per edition's repetition policy |
**Recoverable:** judgment. **Fix:** many are legitimate (hadith cited under multiple chapters) — agent decides per group, do NOT mass-delete.

### E29 🟠 Cross-language HN alignment (lulu, mishkat)
**What:** AR row k's HN ≠ translation row k's HN (count parity holds but numbers drift).
**Recoverable:** judgment. **Fix:** per-section ordered-HN diff, realign or flag.

---

## P2 — SCHEMA / METADATA

### E30 🟡 metadata_malformed (sections[] header missing)
**What:** translations/<lang>/metadata.toon lacks `sections[N]{…}` header. 12 flagged, 19 excused — verdict inconsistent.
**Recoverable:** mechanical. **Fix:** needs ONE decision: required → add headers to 12; not required → close 12 findings.

### E31 🟡 Empty metadata fields (grades/reference/intl/chain/intro)
**What:** AR source has empty fields where populating editions (abudawud/nasai/muslim/bukhari) fill them. ~16 each.
**Recoverable:** external (data never had them). **Fix:** NOT universal "by design" — 10 editions deviate from the 4 that populate. Decision: leave empty (acceptable) vs backfill from source. Default: leave, don't fabricate.

### E32 🟡 bidi_control_characters (U+200E/F, U+202A-E)
**What:** invisible RTL/LTR marks in mixed-script text. 5 found, repo-wide unscanned.
**Recoverable:** mechanical. **Fix:** strip bidi marks from data fields.

### E33 🟡 Non-canonical grade values
**What:** grades outside canonical set: `[مرسل صحيح` (stray bracket), `: Sahih` (leading colon), `No Data Available` (7,272 rows musannaf).
| Before | After |
|---|---|
| `[مرسل صحيح` | `مرسل صحيح` |
| `: Sahih` | `Sahih` |
| `No Data Available` | *(empty)* |
**Recoverable:** mechanical. **Fix:** strip brackets/colons, replace `No Data Available`→empty.

### E34 🟡 Reference format inconsistency
**What:** mixed reference schemes within an edition (`Sahih Muslim 1` vs `Muslim 1`).
**Recoverable:** mechanical. **Fix:** normalize to one scheme.

---

## P3 — COSMETIC / TEXT QUALITY (bulk regex)

### E35 🟡 leading_ordinal pollution
**What:** translation text starts with the hadith number (`6.`, `৬.`, `(6)`, `۱.`, `1.`, `हदीस N:`) before real text. 15 confirmed.
| Before | After |
|---|---|
| `"6","৬. মুসাদ্দাদ ইবনে…"` | `"6","মুসাদ্দাদ ইবনে…"` (strip `৬. `) |
**Recoverable:** mechanical. **Fix:** regex strip leading `^\d{1,4}[.):-]\s` / ordinals per language. **Caveat:** don't strip `()` that are real text.

### E36 🟡 markdown_residue
**What:** `**bold**`, `*Chaîne de narration*`, `[text](url)`, ``` ``` ```, `-` bullets in text. 15 confirmed (real, not backtick-transliteration).
**Caveat:** bukhari `` `Urwa `` backticks are transliteration convention, NOT markdown — ~90× false-positive inflation there.
| Before | After |
|---|---|
| `*Chaîne de narration*` | `Chaîne de narration` |
| `- bullet` | `bullet` |
**Recoverable:** mechanical. **Fix:** strip markdown markers, keep content.

### E37 🟡 trailing scraping residue
**What:** scraper artifacts appended: `Sahih X Hadees: N Arabic Hadees: M`, `Hadith arabe : M`, `شمائل ترمذی حدیث:`.
| Before | After |
|---|---|
| `…text. Sahih al-Bukhari 1 Hadees: 1 Arabic Hadees: 1` | `…text.` (strip scraper suffix) |
**Recoverable:** mechanical. **Fix:** regex strip known suffix patterns.

### E38 🟡 mojibake (U+FFFD / `ن` / `?`)
**What:** replacement chars and `??` corruption. 15 confirmed high. Overlaps E6/E7.
**Recoverable:** partial. **Fix:** strip/replace where recoverable, mark where not.

### E39 🟡 orphan_line / odd_quote
**What:** stray non-data lines after header; odd `"` count on a row. 12 + 8.
**Recoverable:** mechanical. **Fix:** remove stray lines, re-quote odd rows.

### E40 🟡 numbering_gap (within-file)
**What:** HN non-sequential within one file. 10 confirmed.
**Recoverable:** external-verify (some intentional). **Fix:** verify vs source before renumbering.

### E41 🟡 very_short_text / empty_text
**What:** translation text <15 chars or empty. 20 empty + 10 short.
| Before | After |
|---|---|
| `"142"," "` | flag missing (don't fabricate) |
**Recoverable:** external. **Fix:** mark missing, re-pull.

### E42 🟡 dup_text_in_section (within one file)
**What:** same text for different HN in one file. 15 confirmed — many legitimate hadith repetitions.
**Recoverable:** judgment. **Fix:** agent review; keep legitimate, flag genuine dupes.

### E43 🟡 dup_text (runaway repetition loops in a row)
**What:** phrase repeated dozens-hundreds of times in one row. 10 confirmed high.
| Before | After |
|---|---|
| `"548","and two good deeds and two good deeds …(733×)"` | truncate to one instance + `[corrupt]` |
**Recoverable:** partial. **Fix:** truncate loop, mark.

### E44 🟡 backslash-quote artifact (`\Word`, `""""""`)
**What:** JSON→CSV round-trip left backslashes and quote runs. Overlaps E11/E12.
**Recoverable:** mechanical. **Fix:** unescape `\`→``, collapse `""""`→`""`.

### E45 🟡 script_mismatch
**What:** dominant script of translation text ≠ language. 8 confirmed high (e.g. ur field full of Latin).
**Recoverable:** partial. **Fix:** agent review — strip cross-script or flag.

---

## FALSE-POSITIVE PRONE (trust counts cautiously)
- **field_count_mismatch (E22):** awk-inflated. Real count = floor. Use python csv for truth.
- **metadata_malformed (E30):** verdict inconsistent across editions. Need 1 decision.
- **dup_text_in_section (E42):** many legitimate repetitions.
- **leading_ordinal/markdown bukhari (E35/E36):** `` `Urwa `` backtick transliteration → 90× inflation.
- **ai_leakage `Note:` (E1):** ~8 are Khan-translation editorial notes, not slop.
- **"intentional" numbering gaps (E40):** asserted not verified.
- **cross-section dup (E28):** assume byte-identical; NFC/NFD drift unscanned → undercount.

---

## RECOVERABILITY SUMMARY
| Type | Errors | Action |
|---|---|---|
| external (data gone) | E1,E4,E5,E9,E10,E13,E26,E41 | re-pull from sunnah.com OR document as known-bad |
| partial (truncate) | E2,E6,E7,E8,E11,E16,E19,E38,E43 | strip bad part, mark, original lost |
| deletable | E3,E17 | remove garbage rows, renumber |
| mechanical (no loss) | E12,E14,E15,E20,E21,E23,E24,E25,E32,E33,E34,E35,E36,E37,E39,E44 | deterministic fix |
| judgment | E18,E28,E29,E42,E45 | agent decides per-instance |
| decision-gated | E30,E31 | need your call first |

## DECISIONS NEEDED FROM YOU
1. **External-source defects (E1,E4,E5,E9,E10,E13,E26,E41):** re-pull from sunnah.com/origin, or mark known-bad? (Re-pull = big effort; mark = honest, fast.)
2. **metadata.toon sections[] header (E30):** required or optional? Unblocks 12 editions.
3. **Empty AR metadata fields (E31):** leave empty (acceptable) or backfill?
4. **malik 5-digit numbers (E10):** any external malik reference to decode them? Don't touch blind.
5. **Fix execution:** scripts for mechanical (P1/P3), agents for judgment (P0)? 
6. **Phase order:** run the 6 unrun greps (bidi, JSON-LD, non-numeric HN, HN-diff, grade-histogram, cross-section-hash) BEFORE finalizing — they may surface more P0. Do this first?
