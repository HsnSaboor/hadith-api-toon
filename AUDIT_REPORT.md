# Hadith .toon Repository Audit — Synthesis Report

**Scope:** 31 editions under `/home/saboor/code/hadith-api-toon/editions`. 31 finder agents read 513 real files; every finding was adversarially re-verified by an agent that re-opened the cited file. Counts below are of *distinct confirmed/uncertain findings as delivered* — several kinds are inflated by one-finding-per-row reporting of systemic patterns (noted in caveats).

---

## 1. Issue Kinds by Count (most frequent first)

| Rank | Kind | Count | Dominant severity | Notes |
|---|---|---|---|---|
| 1 | ai_leakage | ~35 | high | Real but many low-sev editorial "Note:" items |
| 2 | cross_section_duplicate_hadith_text | ~28 | medium | New defect class from completeness critic |
| 3 | field_count_mismatch | ~25 | high | Often awk artifacts — see caveats |
| 4 | empty_text | ~20 | high | Concentrated in a few editions |
| 5 | empty_grades / empty_intl_number / empty_reference / empty_field | ~16 each | low–med | Structural; often "by design" — see caveats |
| 6 | leading_ordinal | ~15 | medium | Cosmetic machine-prepended ordinals |
| 7 | markdown_residue | ~15 | medium | Bullets, italics, code fences, backticks |
| 8 | mojibake | ~15 | high | ASCII `??`, `n`, `?` corruption in Arabic/Urdu |
| 9 | dup_text_in_section | ~15 | medium | Some are legitimate repeated narrations |
| 10 | metadata_malformed | ~12 | medium | **Verdict inconsistent across editions** — see caveats |
| 11 | orphan_line | ~12 | medium | Stray continuation/danda lines |
| 12 | numbering_gap | ~10 | high | Several "intentional" — unverified |
| 13 | info_toon_sections_index_vs_actual_bounds | ~10 | high | sahih-ibn-khuzaymah + malik worst |
| 14 | very_short_text | ~10 | high | Truncated/fragment rows |
| 15 | dup_text | ~10 | high | Runaway repetition loops |
| 16 | script_mismatch | ~8 | high | Urdu/Arabic/Latin cross-script leaks |
| 17 | odd_quote | ~8 | medium | Runaway `""""` sequences |
| 18 | info_lang_mismatch | ~7 | high | `ar` listed but no translations/ar dir |
| 19 | cross_language_hadith_number_alignment | ~6 | high | Row-merge drift (lulu-wal-marjan, mishkat) |
| 20 | bidi_control_characters | ~5 | medium | U+200F/U+202C invisible marks |
| 21 | info_total_mismatch | ~5 | medium | Off-by-ones + real shortfalls |
| 22 | section_boundary_numbering_continuity | ~5 | medium | Non-monotonic section bounds |
| 23 | header_count_mismatch | ~3 | medium | |
| 24 | count_literal | ~2 | high | bukhari only |
| 25 | section_gap | ~1 | low | malik (50–55 absent) |
| 26 | cross_language_section_file_set_parity | ~1 | medium | nasai missing sec 36 |

---

## 2. Most Severe (High-Severity) Findings

### Data-loss / corruption (fix first)

1. **musnad-ahmad — AR/UR section 19 numbering gap (HN 1740 → 22865).** `editions/musnad-ahmad/sections/19.toon:3` and `translations/ur/sections/19.toon:3`. Only 2 rows; a ~21,000-number jump. Confirmed in both AR and UR; matches info.toon-declared range, suggesting upstream data error. (high)
2. **mustadrak — literal ASCII `n` embedded in Arabic across ~4,530 AR rows.** `editions/mustadrak/sections/1.toon:2` (e.g. `صحيحn قَالَ`). Newline-stripped to bare `n` during export. Edition-wide. (high)
3. **sahih-ibn-khuzaymah — info.toon section index malformed for 1,059/1,073 rows.** `editions/sahih-ibn-khuzaymah/info.toon:33` — Arabic name fields contain unescaped embedded double-quotes (`ذَكَرْتُهَا,"بَابُ`), so hadith_first/hadith_last/arabic_first/last are unreachable by naive CSV split. Only 14 rows parse to declared 14 columns. (high)
4. **malik — malformed 5-digit hadith numbers (14601, 42801, 16701…) across AR + all 6 translations.** `editions/malik/sections/3.toon:2`. 1,797 rows exceed total_hadiths=2,757; section 49 has 330 such rows. Cross-language drift scan is *clean* only because the corruption is mirrored everywhere — a false negative. (high)
5. **musannaf-ibn-abi-shaybah — literal `??` in-word corruption in 281 AR rows + 73 EN rows.** `editions/musannaf-ibn-abi-shaybah/sections/1.toon:519` (`إسْرَائِیلَ ?? عَنْ`), `sections/2.toon:970` (`زَ??َرِیَّا`). Real bytes, not U+FFFD. (high)
6. **ibnhibban — 4 EN rows replaced by schema.org JSON-LD scraped from en.tohed.com.** `translations/en/sections/10.toon:17` (HN 1139), `31.toon:88` (3610), `49.toon:95` (5690), `62.toon:63` (7174). Plus 4 EN rows truncated to 9–14 char fragments (s1/139, s33/3830, s51/5905, s56/6503) where AR+UR have full hadiths. (high)
7. **tirmidhi — intro_hi runaway loop: phrase `छह में से` repeated 384×, truncating mid-word at `छah`.** `editions/tirmidhi/info.toon:11`. (high)
8. **nasai — intro_ur ends in runaway loop repeating `پالیسٹائن سے` 134×.** `editions/nasai/info.toon:16`. (high)
9. **shamail-tirmidhi — UR hadith 161 is catastrophic AI self-monologue.** `editions/shamail-tirmidhi/translations/ur/sections/25.toon:17`: ~50× repeated loop ending in `PARAM? No, I think I'm making a mistake in the Urdu translation… Here we go:`. (high)
10. **ibnmajah — French translation pervasively AI-generated.** `translations/fr/sections/{1,5,9,10,15,25,33,37}.toon` contain `Voici la traduction…` preamble rows (597, 1311, 1855, 2271, 2520, 3119, 4316) and `Traduction : ` prefixes (sec33 x7). (high)
11. **muslim — Turkish sections 1/15/32 contain 49 synthetic `Hadith <name>:\n Rüya:` rows** wrapping English hadith text into fake Turkish. `translations/tr/sections/15.toon:52`. (high)
12. **aladab-almufrad — entire English translation tree systemically corrupted.** `translations/en/sections/1.toon` and 56/57 EN files: literal `\n` newlines, `\The`/`\I asked` backslash-escapes, trailing `""""""` quote artifacts, and row 548 with `and two good deeds` repeated 733×. (high)
13. **hisn — systemic EN CSV-quoting bug: 55 bad rows across 40 of 132 EN files.** `translations/en/sections/132.toon:2` (66 quotes/row), `72.toon:3`, `9.toon:3`. Runaway `""""""""` sequences split one logical row into 4–15 fake fields. (high)
14. **lulu-wal-marjan — EN translation drops/merges 281 hadiths.** `translations/en/sections/0.toon:2` merges HN 1+2; `1.toon:6` merges 11+12; metadata claims 1906 but EN has 1,625 rows. OCR garbage in `0.toon` row 1 and `54.toon` row 1904. (high)
15. **mishkat — translation sections 20 and 21 are swapped vs AR source.** AR sec20=Foods (HN 3992, 72 rows) but EN/sec20=Hunting (HN 4064, 95 rows); sec21 is the inverse. Confirmed by row-count transposition (72/95 → 95/72). (high)
16. **abdurrazzaq — chapter_intro off-by-one across all 31 AR files.** `sections/2.toon:2` carries "Book of Purification" (sec1's name) for hadith 606–1107; sec16 carries "Book of Jihad" (sec15's name); sec31 carries "Book of Found Property" (sec30's name). Systematic mislabel. (high)
17. **hisn — chapter_intro wrong for all 66 AR sections 67–132.** All carry section 132's title "Comprehensive types of good and manners". `editions/hisn/sections/100.toon:2`. (high)
18. **abudawud — Bengali rows with raw English + AI labels.** `translations/bn/sections/41.toon` rows 4497/4542/4586, `42.toon` rows 4599/4665, `5.toon` row 1275, `3.toon` row 1192: `narrator chain:`/`hadith body:` labels in bn field. Plus bn/41 row 4595 severe Bengali vowel-stripping corruption. (high)
19. **bukhari — all 97 AR source files use literal `[count]` in header.** `sections/1.toon:1` `hadiths[count]{…}`; 5 translation section-0 files likewise. (high)
20. **qudsi — heavy multi-script contamination in bn/te/ta translations.** Korean Hangul `께서` in Tamil (`ta/sections/1.toon:2`), Russian `которого` + Devanagari in Bengali (`bn/sections/1.toon:18`), Arabic/Urdu inline throughout. (high)
21. **muajam-tabarani-saghir — AR grades field contains Urdu text, not Arabic grades.** `sections/1.toon:2` — 25 rows in sec1 carry Urdu in grades; 18,301 of 18,326 AR rows have empty grades; reference + narrator_chain empty for all 18,326. (high)
22. **musannaf-ibn-abi-shaybah — UR rows `plvvlqj` (Latin gibberish).** `translations/ur/sections/6.toon:889` (HN 5898), `23.toon:453` (HN 22496). (high)
23. **bayhaqi — UR hadith 10342 infinite-repetition corruption.** `translations/ur/sections/10.toon:8`: `ہم کو` repeated dozens of times. (high)
24. **fath-al-rabbani — EN hadiths 142 & 152 massive internal repetition; hadith 150 missing as a row.** `translations/en/sections/2.toon` rows 3, 10, 12; row 150's text mangled onto row 149 as unquoted trailing content. (high)
25. **sunan-al-daraqutni — ASCII `?` corrupting Arabic/Urdu in chapter_intro across sections 3/11/15/28.** `sections/15.toon:227` (`حدود اور دی??ت`), `11.toon:23` (`نہی??`). (high)

### Structural (high)
26. **info_lang_mismatch** in abudawud (`info.toon:59`), aladab-almufrad, nawawi (`info.toon:23`): `ar` listed in available_languages with a `translations/ar` path but no such directory exists. ibnmajah + muslim uncertain (ar is source, arguably belongs in list).
27. **nasai missing section 36 entirely** (AR + all 8 translations + info.toon index skip 35→37) — hadiths 3857–3965 unaccounted for.
28. **bukhari info.toon total_hadiths=7563 but AR rows=7277**; Turkish sec0 has 2 malformed merged rows (7412/7413, 7495/7496 embedded into preceding row).

---

## 3. Systemic Patterns (editions/languages disproportionately affected)

- **AI-leakage pipeline (fr, roman-ur, tr):** ibnmajah-fr, tirmidhi-roman-ur, muslim-tr, shamail-ur all show the same upstream pattern — AI preambles (`Voici la traduction`, `Hadith ka Tarjuma`, `Rüya:`), meta-notes asking the user to send full text, and `Traduction :` prefixes. These translation packs were machine-generated and never cleaned.
- **Bengali (bn) is the most-contaminated language across editions:** abudawud-bn (raw English + AI labels, vowel-stripping corruption), muslim-bn (`নarrated` mojibake), qudsi-bn (Russian/Devanagari/Urdu inline), bukhari-bn/ibnmajah-bn (leading ordinals), malik-bn (leading `রেওয়ায়ত N.`). bn is consistently lower quality than sibling translations.
- **English CSV-quoting bug is repo-wide:** aladab-almufrad (`\n`+`""""""`), hisn (55 bad rows), lulu-wal-marjan (embedded `""N""` merges), bukhari-tr (row merges), nawawi (backslash-quote in all 42 bs+tr rows), riyadussalihin (339 EN rows). Same upstream JSON→CSV round-trip artifact.
- **Empty metadata columns are NOT universal:** abudawud/nasai/muslim/bukhari populate grades+reference; abdurrazzaq/dehlawi/fath/bulugh/nawawi/qudsi/tirmidhi/mustadrak/muajam/sunan-al-daraqutni leave them empty. So empty-field editions deviate from the schema reference editions follow — not "by design" universally.
- **chapter_intro off-by-one is a recurring mislabel:** abdurrazzaq (all 31 files), hisn (66 files), nasai-kubra, sahih-ibn-khuzaymah (258 files with Urdu in AR chapter_intro).
- **"Trailing scraping residue"** (`Sahih X Hadees: N Arabic Hadees: M`, `Hadith arabe : M`, `شمائل ترمذی حدیث:`) appended to translation text across muslim (en 20 files, fr 49 files, bn many), malik, shamail — shared upstream scraper artifact.
- **Cross-section duplicate hadith text is repo-wide** (new finding from completeness critic): 28 confirmed groups across 13+ editions (ibnhibban 108 EN/5 AR, sahih-ibn-khuzaymah 32, malik widespread, tirmidhi, abudawud, bukhari, nasai, nasai-kubra, riyadussalihin, muajam, shamail, silsila-sahih, virtues, bayhaqi). Same narration filed under different numbers in different section files.
- **intro script contamination is the rule, not the exception:** every edition whose intro_ur/intro_hi/intro_id was checked (nasai, tirmidhi, riyadussalihin, musnad-ahmad, malik, shamail, nasai-kubra, sunan-darimi, aladab, nawawi) had Latin fragments, runaway loops, or mistranslations. Unchecked editions are a blind spot.

---

## 4. False-Positive / Data-Quality Caveats (which counts to trust)

- **field_count_mismatch — HIGH false-positive rate from awk.** Finders acknowledged (abudawud, bulugh, ibnhibban) that `awk -F'","'` splits on literal embedded quotes inside Bengali/Arabic text, producing phantom mismatches. Editions that used **python csv** (sunan-darimi, sunan-al-daraqutni, tirmidhi, musannaf) found 20+ real 8–10 field rows; editions relying solely on awk and reporting "0 field_count_mismatch" are **suspect**. The ~25 count is a floor, not a ceiling, for real CSV breakage.
- **metadata_malformed (missing sections[] header) — VERDICT INCONSISTENT.** Flagged in ~12 editions (aladab, fath, ibnmajah, malik, mustadrak, muslim, muajam) but explicitly excused as "repo standard" in riyadussalihin, tirmidhi, bulugh, ibnhibban. Same observation, opposite verdicts. **Needs one authoritative call** — either ~12 findings are false positives or ~19 editions have an unreported defect.
- **"Intentional numbering gap" false-negative risk.** Finders asserted gaps mirrored in AR + all translations are "intentional source skips" (nasai 13 sections, tirmidhi, mishkat sec0, bukhari). This is an assumption, not verification — a systematic upstream hadith-drop is indistinguishable. Every such gap should be cross-checked against an external reference.
- **dup_text_in_section — many are legitimate.** tirmidhi's same-narration-under-adjacent-numbers, sunan-al-daraqutni's "This tradition is narrated along with another document." filler, and malik's cross-book repetition are genuine hadith repetitions, not corruption. The ~15 count overstates real defects.
- **leading_ordinal — bukhari backtick `ayn transliteration false positives.** 9,717 backtick hits in bukhari EN/FR are the `` `Urwa `` `` `Aisha `` transliteration convention, NOT markdown. Only 108 real `[text](ref)` bn citations. bukhari's leading_ordinal count is trustworthy; its markdown_residue count was inflated ~90× by this before correction.
- **ai_leakage — "Note:" and "let me know" are often legitimate.** bukhari's Khan-translation editorial `Note:` annotations and `let me know` inside narrator speech were verified false positives. The ~35 ai_leakage count includes ~8 low-severity editorial-note items that are arguably source-faithful, not AI slop.
- **"By design" empty-field acceptance is unverified.** Finders accepted empty grades/ref/intl/chain as "by design" in 10 editions without cross-checking against the populating editions. abudawud/nasai/muslim/bukhari prove the schema supports these fields populated.
- **total_hadiths reconciliation was row-count-only, 2-way.** AR-total vs info.total was checked; translation-metadata.toon total vs its own row count was NOT systematic. lulu-wal-marjan (en metadata claims 1906, en has 1625) shows 3-way reconciliation is needed.
- **Cross-section dup_text scans assume byte-identical comparison.** NFC/NFD normalization drift would make the same hadith appear as non-duplicate. No finder scanned unicode normalization. Cross-section-dup counts are a floor.

---

## 5. Completeness Gaps (likely missed — follow-up audit needed)

The completeness critic flagged 19 unscanned categories. Highest-priority gaps:

1. **cross_language_hadith_number_alignment (per-row, not just count-parity)** — the single most likely undetected systemic defect. Count-parity holds while hadith numbers drift (lulu-wal-marjan, mishkat proved it exists). Need: per-section ordered-HN diff AR vs each translation, all editions.
2. **cross_section_duplicate_hadith_text** — partially filled by the critic's targeted run (28 groups found), but a full hash-all-arabic-fields-then-find-cross-file-collisions pass is still needed across all 31 editions.
3. **info_toon_sections_index_vs_actual_bounds** — confirmed catastrophic in sahih-ibn-khuzaymah (1,059/1,073 malformed) and malik; only ~10 editions checked. The other ~21 editions' section indexes are unverified.
4. **section_boundary_numbering_continuity** — non-monotonic boundaries confirmed in muslim (sec43 starts 969 before sec42 ends), malik (5-digit corruption), nasai, virtues. Need: every edition, sort-by-id then last(N)+1==first(N+1) check.
5. **bidi_control_characters** — only 5 found (nawawi U+202B/202C; ibnmajah/abudawud U+202C; musnad-ahmad U+200F) but grep was not run repo-wide. Mixed RTL/LTR editions (qudsi, muslim, musnad-ahmad) almost certainly have more.
6. **unicode_normalization_nfc_nfd** — never scanned. Breaks dedup and cross-language consistency.
7. **intro_script_consistency_all_editions** — every edition checked had ≥1 bad intro; the majority of editions were never checked.
8. **schema_ld_or_json_leakage_repo_wide** — ibnhibban's 4 JSON-LD rows came from en.tohed.com; other editions sharing that upstream likely have more. A single repo-wide grep for `mainEntityOfPage|@type.*WebPage|en.tohed|al-hadees` is cheap and not done.
9. **non_numeric_hadith_numbers_repo_wide** — hisn's `75a` broke the total by one; a grep for `^"[0-9]+[a-zA-Z]"` / `^"[0-9]+[/-][0-9]+"` across all sections is unrun.
10. **trailing_scraping_residue_repo_wide** — the `Sahih X Hadees: N Arabic Hadees: M` pattern confirmed in muslim/malik/shamail; a repo-wide grep is unrun.
11. **grade_value_canonicalization** — sunan-al-daraqutni `[مرسل صحيح` (stray bracket), sunan-darimi `: Sahih` (leading colon), musannaf `No Data Available` (7,272 rows) are the tip. A repo-wide grade histogram + whitelist is missing.
12. **count_literal_header_repo_wide** — confirmed in bukhari (97 AR + 5 tr); a single `grep -rl 'hadiths\[count\]'` across all editions is unrun.
13. **metadata_toon_sections_header_reconciliation** — see caveat #2; needs a single authoritative decision.
14. **narrator_chain_content_validity** — silsila-sahih sec1 has narrator_chain mis-populated with the intl number; finders only checked emptiness, never content where populated.

### Under-audited editions (low file-coverage, high false-negative risk)
- **musnad-ahmad**: 2,354 section files; finder read ~20 (~0.8% coverage), explicitly admitted incomplete. Largest blind spot.
- **sahih-ibn-khuzaymah**: 1,074 AR sections; only sec 1172 + 2160 inspected beyond the index headline.
- **bukhari**: ~1,078 files; fr placeholder scan = 1 section of 97; tr merge scan = 1 section of 96.
- **muslim**: 638 files; bn mojibake checked in 4 of 44 bn files; tr `Rüya:` fabrication checked in 3 of 54 tr files.
- **abudawud**: 440 files; bn AI-leakage checked in 5 of 44 bn files.
- **ibnmajah**: fr AI-leakage in 8 of 32 fr sections; hi ordinal in 2 of 32.
- **qudsi**: 5 of 13 translation languages unsampled for cross-script leaks.

---

## 6. Prioritized Recommended-Fix List

**P0 — Data loss / user-facing wrong content (fix immediately)**
1. Re-fetch the 8 corrupted ibnhibban EN rows (4 JSON-LD + 4 truncated) from a clean source.
2. Re-export the entire **lulu-wal-marjan** English translation (281 merged/dropped hadiths + OCR garbage).
3. Rewrite **shamail-tirmidhi UR hadith 161** (AI self-monologue) and **bayhaqi UR hadith 10342** (infinite repetition).
4. Regenerate **tirmidhi intro_hi** (384× loop) and **nasai intro_ur** (134× loop).
5. Fix **musnad-ahmad section 19** numbering gap (1740→22865) — upstream re-pull or document the gap.
6. Remove **muslim Turkish `Rüya:` synthetic rows** in sections 1/15/32 (49 fabricated translations).
7. Strip the **ibnmajah French AI preambles** (`Voici la traduction…`, `Traduction :`) across all 32 fr sections.

**P1 — Structural corruption (batch-fixable)**
8. Repo-wide `grep -rl 'hadiths\[count\]'` → replace `[count]` with real row counts (start with bukhari's 102 files).
9. Fix **hisn chapter_intro** (66 sections carry sec132's title) and **abdurrazzaq chapter_intro** off-by-one (31 files) — re-derive from info.toon section names.
10. Repair **sahih-ibn-khuzaymah info.toon** section index (1,059 malformed rows) — re-quote embedded Arabic names.
11. Repair **malik 5-digit hadith numbers** (1,797 malformed rows mirrored across AR + 6 translations).
12. Strip **musannaf-ibn-abi-shaybah `??` corruption** (281 AR + 73 EN rows) and **mustadrak `n`-stripping** (~4,530 AR rows).
13. Remove **abudawud bn raw-English rows** with `narrator chain:`/`hadith body:` labels (sections 3/5/41/42) and fix bn/41 row 4595 vowel corruption.
14. Fix **mishkat swapped sections 20/21** in all translations (transpose file contents back).

**P2 — Schema/metadata reconciliation**
15. Resolve **metadata.toon sections[] header** requirement ONCE — then either fix ~12 editions or close the 12 findings as false positives.
16. Fix **info_lang_mismatch** in abudawud, aladab-almufrad, nawawi (drop `ar` from available_languages or create the dirs).
17. Reconcile **info_total_mismatch** in bukhari (7563 vs 7277 AR), hisn (267 vs 268), musnad-ahmad (28198 vs 28199).
18. Run the **3-way total reconciliation** (info.total vs AR rows vs each translation's metadata.total vs its rows).

**P3 — Cosmetic / text-quality cleanup (bulk regex)**
19. Strip trailing scraping residue (`Sahih X Hadees: N Arabic Hadees: M`, `Hadith arabe : M`, `شمائل ترمذی حدیث:`) across muslim/malik/shamail.
20. Strip leading ordinals (`(N) `, `১.`, `۱.`, `1. `, `हदीस N:`) across musannaf-ibn-abi-shaybah, bukhari-bn, ibnmajah, nasai-bn, muslim multi-lang.
21. Fix the **backslash-quote artifact** repo-wide (`\Word`, `\""""""`) — aladab-almufrad, hisn, nawawi, riyadussalihin.
22. Remove markdown residue (bullets, `*Chaîne de narration*`, ``` code fences) from ibnmajah-fr, tirmidhi-roman-ur, nasai.

**P4 — Follow-up audit passes (cheap, unrun)**
23. `grep -rlP '[\x{200E}\x{200F}\x{202A}-\x{202E}]'` repo-wide for bidi control chars.
24. `grep -rlE 'mainEntityOfPage|@type.*WebPage|en\.tohed|al-hadees'` repo-wide for JSON-LD scrape residue.
25. `grep -rlP '^"[0-9]+[a-zA-Z]"'` repo-wide for non-numeric hadith numbers.
26. Per-section ordered-HN diff AR vs each translation, all editions (the lulu/mishkat drift class).
27. Grade-value histogram + whitelist, all editions.
28. Cross-section Arabic-field hash collision pass, all 31 editions.