# SOURCE_RECOVERY_PLAN.md
## Recovery plan for KNOWN_ISSUES data-loss items — sources found, fix not yet applied

Audit found 10 data-loss items needing recovery. Sources were probed across sunnah.com, al-hadees.com, fawazahmed0/hadith-api, HuggingFace datasets, tohed.com, hadithunlocked (excluded), PLUS local backups (`~/code/hadith-api-toon-alt/`, `~/code/hadith-api-toon/scripts/cache/`, `~/code/hadith-api-toon-new/*_final.json`, `~/sunnah-now-data/`, `~/markaz-scraper/markaz.db`). hadithunlocked.com rejected entirely (Google/machine-translated, `[AI]` prefix). This is a PLAN ONLY — no fixes applied.

---

## Source access map (verified)

| Source | What it has | Access | Notes |
|---|---|---|---|
| **fawazahmed0 CDN** | canonical-4 (abudawud/ibnmajah/malik/nasai) × ara/eng/fra/urdu/ben/ind/tur/rus/tam | `https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/<lang>-<edition>.min.json` | JSON array, `hadithNumber`+`text` per row. Local mirror: `~/code/hadith-api-toon/scripts/cache/<lang>-<edition>.min.json` |
| **tohed.com** | Arabic + EN/UR/FR per hadith, many editions | `https://en.tohed.com/hadith/<slug>/<HN>/` | Confirmed 200: nasai, shamail-tirmidhi, musannaf-ibn-abi-shaybah, sahih-ibn-khuzaymah, sahih-ibn-hibban. Renders Arabic + EN + UR (+FR) per hadith. ibnhibban slug = `sahih-ibn-hibban`. |
| **al-hadees.com** | Arabic + Urdu | `https://al-hadees.com/hadees/<book>/<page>/0` | existing `scrape_alhadees_full.py`. Covers musnad-ahmad, bayhaqi, partial others. |
| **sunnah.com ajax** | en/ur/bn per page | `https://sunnah.com/ajax/<lang>/<collection>/<page>` | Cloudflare 403 on root, ajax works from existing `scrape_sunnah_*.py`. Coverage: canonical-4 + bukhari/muslim/tirmidhi/malik/ahmad. NOT ibnhibban/lulu/musannaf/silsila/khuzaymah/hisn/virtues. |
| **LOCAL alt repo** `~/code/hadith-api-toon-alt/` | per-edition pre-corruption builds | dir tree | ibnmajah/{ar,en,bn,fr,hi,id,ro} full .toon trees + .json; `backup_pre_backfill/`, `backup_pre_fix/`; `hadith islam360/silsila.db` (3704 hadees + hadees_languages) |
| **LOCAL scripts/cache** `~/code/hadith-api-toon/scripts/cache/` | raw scrapes | JSON | fawaz `<lang>-<edition>.min.json` (all langs), `ahmedbaset_*.json` (al-hadees), `fz_*.json`, `ibnhibban.json`+`ibnhibban_urdu.json` (sunnah), `bayhaqi.json` (116M), `daraqutni.json`, `hakim.json` |
| **LOCAL hadith-api-toon-new** `~/code/hadith-api-toon-new/` | `*_final.json` pre-conversion | JSON dicts (per-section `hadiths[]` with `translations{}`) | musannaf(40M), nasai(46M), khuzaymah(3.2M), silsila(2.2M), shamail(247K), ibnmajah(34M), abudawud(54M), etc. |
| **openrouter LLM** | 6 keys | translate intact AR → target lang | LAST RESORT. Prefix output `[AI-translation]` per row. |
| **hadithunlocked.com** | — | — | ❌ DO NOT USE (machine-translated, `[AI]` prefix) |

---

## Per-item recovery verdict (verified)

| # | Item | Best source | Coverage | Action |
|---|---|---|---|---|
| 1 | ibnhibban EN HN 1139,3610,5690,7174 (JSON-LD) | tohed.com | 4/4 (page renders EN) | rescrape tohed → write EN rows |
| 2 | ibnhibban EN 12 truncated (1517,1615,1714,1845,2128,2505,3784,3812,5905,6142,6971,7402) | tohed.com | 12/12 (EN renders) | rescrape tohed |
| 3 | ibnmajah FR HN 597,1311,1855,2271,2291,2520,4316 (AI preambles) | **local `scripts/cache/fra-ibnmajah.min.json`** (CLEAN verified) | 7/7 clean | local rescrape (fawaz) |
| 4 | lulu-wal-marjan EN 281 missing | NO clean source anywhere (local empty, fawaz empty, tohed 404, sunnah no-lulu) | 0/281 | **LLM translate from intact AR** (AR/UR have 1906) |
| 5 | nasai section 36 (HN ~3939–3965, all 9 langs) | local `hadith-api-toon-new/nasai_final.json` + `scripts/cache/*-nasai.min.json` (all 9 langs) | full | local rescrape, all langs |
| 6 | musannaf UR HN 5898, 22496 (plvvlqj) | tohed.com (renders Urdu) — local backup has EN only, no UR | 2/2 via tohed | rescrape tohed UR |
| 7 | shamail-tirmidhi UR HN161 | local `hadith-api-toon-new/shamail-tirmazi_final.json` + tohed | 1/1 | local first, tohed verify |
| 8 | sahih-ibn-khuzaymah index (1059 rows + 320 chapter_intro) | local `hadith-api-toon-new/sahih_ibn_khuzaymah_final.json` (3.2M) + tohed | full | local rescrape metadata |
| 9 | silsila-sahih EN ~3182 empty | local `hadith-api-toon-alt/hadith islam360/silsila.db` (sqlite, 3704 hadees + languages) + `hadith-api-toon-new/silsila_sahih_final.json` (has translations) | full | local sqlite/JSON |
| 10 | abudawud BN HN4588 (vowel corruption) | **local `scripts/cache/ben-abudawud.min.json`** (fawaz Bengali) | 1/1 | local rescrape |

**Recoverable from clean source: 9/10 items. LLM fallback needed: 1 (lulu EN, 281 hadiths).**

---

## Detailed recovery procedure per item

### Item 1+2 — ibnhibban EN (HN 1139, 3610, 5690, 7174, 1517, 1615, 1714, 1845, 2128, 2505, 3784, 3812, 5905, 6142, 6971, 7402)
- **Source:** `https://en.tohed.com/hadith/sahih-ibn-hibban/<HN>/` (renders Arabic + English).
- **Confirmed:** tohed page for HN1139 returns real EN text (title "Ibn Hibban 1139 — Chapter on Nullifiers of Ablution..."); EN renders per-hadith.
- **Local check:** `~/code/hadith-api-toon-alt/ibnhibban/en.json` (1.9M) has these HNs but text is EMPTY (len=0) — that's WHY JSON-LD filled them. Not usable. `scripts/cache/ibnhibban.json` (sunnah format) — also check, but tohed is cleaner.
- **Procedure:**
  1. For each of the 16 HNs: fetch `https://en.tohed.com/hadith/sahih-ibn-hibban/<HN>/`, parse the English hadith body from HTML (the `hadith-app` content block).
  2. Map into `editions/sahih-ibn-hibban...`? — confirm repo edition dir name. The repo has no `editions/sahih-ibn-hibban` (audit referenced `ibnhibban`). Confirm: repo edition = `ibnhibban`. EN files at `editions/ibnhibban/translations/en/sections/<N>.toon`. Find which section file holds each HN (grep hadithnumber).
  3. Write the fetched EN text into the row's `text` field (translation schema = `{hadithnumber,text}`). Delete any `[corrupt]`/JSON-LD marker left by the fix run.
  4. Be polite: small delay between fetches.
- **Risk:** tohed slug `sahih-ibn-hibban` ≠ repo `ibnhibban` — HN numbering must match (tohed uses Ibn Hibban's numbering; repo ibnhibban uses same). Verify 1 HN before bulk.

### Item 3 — ibnmajah FR (HN 597, 1311, 1855, 2271, 2291, 2520, 4316)
- **Source:** **LOCAL** `~/code/hadith-api-toon/scripts/cache/fra-ibnmajah.min.json` (fawaz FR, 2.7M, 4343 hadiths).
- **Verified CLEAN:** HN 597 → "Rapporté par Abu Hurairah : Le Messager d'Allah a dit : 'Sous chaque c...'", HN 1311 → "Rapporté par Ibn 'Abbas...", etc. No `Voici`/`Traduction`/`mainEntity` artifacts.
- **Note:** the alt repo `~/code/hadith-api-toon-alt/ibnmajah/fr.json` ALSO has the AI preamble (bad=True for same HNs) — do NOT use that. Use the fawaz cache.
- **Procedure:**
  1. Load `fra-ibnmajah.min.json`, build `HN → text` map.
  2. For each of the 7 HNs: find the row in `editions/ibnmajah/translations/fr/sections/<N>.toon` (grep hadithnumber), replace the `text` field with the fawaz clean FR text.
  3. Verify no `Voici`/`Traduction` preamble remains; re-grep `editions/ibnmajah` for `Voici` → expect 0 in hadith rows (1 may remain in info.toon intro, documented).
- **Risk:** fawaz HN = Ibn Majah sunnah numbering; repo ibnmajah uses same. Low.

### Item 4 — lulu-wal-marjan EN (281 missing, all 55 sections)
- **Source:** NONE clean. Local backups empty (`eng-lulu.json`=14B, `lulu_wal_marjan_final.json`=2B), fawaz `eng-lulu`=empty, tohed 404, sunnah.com has no lulu collection, al-hadees no lulu.
- **Intact:** AR + UR have full 1906 (per KNOWN_ISSUES note). AR is the source of truth.
- **Action:** **LLM translate from intact Arabic** (openrouter, 6 keys, strong model). Prefix every recovered row `[AI-translation] ` so consumers know it's machine-translated.
- **Procedure:**
  1. For each missing HN (281): read its AR row from `editions/lulu-wal-marjan/sections/<N>.toon` (the `arabic` field).
  2. Translate AR → EN via openrouter. Prompt: faithful hadith translation, no commentary, preserve proper names in transliteration, no preamble.
  3. Write into the corresponding `editions/lulu-wal-marjan/translations/en/sections/<N>.toon` row, prefixed `[AI-translation] `.
  4. For the OCR-garbage rows (sec0 row1, sec54 row1904) and the merged rows (HN 1+2, 11+12...): also LLM-translate the AR for each individual HN and split into separate rows matching AR HN list.
- **Risk:** 281 LLM translations = cost + quality variance. Acceptable as marked fallback; humans should later replace with a scholarly EN if/when available.
- **Alternative if you prefer no AI:** leave EN missing, document in `info.toon` that EN is incomplete (281/1906 absent). LLM is the only path to fill.

### Item 5 — nasai section 36 (HN ~3939–3965, all 9 languages)
- **Source:** LOCAL. `~/code/hadith-api-toon-new/nasai_final.json` (46M) has AR + translations per section. `~/code/hadith-api-toon/scripts/cache/` has per-language: `ara-nasai`, `eng-nasai`, `fra-nasai`, `urd-nasai`, `ben-nasai`, `tur-nasai`, `ind-nasai`, `rus-nasai`, `tam-muslim` (Tamil on muslim — verify `tam-nasai` exists; if not, Tamil nasai may be absent → LLM for ta only).
- **Procedure:**
  1. From `nasai_final.json` (or `ara-nasai.min.json`), extract the hadiths in HN range 3939–3965 (confirm exact range: sec35 ends 3856, sec37 starts 3966 → sec36 = 3857–3965 per KNOWN_ISSUES; but note said sec0 covers 3857–3938, leaving 3939–3965 with no section — reconcile exact HNs).
  2. For each of the 9 languages present in repo (`editions/nasai/translations/<lang>/sections/`): create `36.toon` with header `hadiths[N]{hadithnumber,text}` and the rows from the language cache. For AR source: `editions/nasai/sections/36.toon` with 7-field schema.
  3. Update `editions/nasai/info.toon` section index to include section 36 (currently skips 35→37).
  4. Verify per-lang row count == AR row count.
- **Risk:** HN range boundary (3857 vs 3939) must be confirmed from `nasai_final.json` before creating files. Tamil may be absent in cache → LLM for ta only.

### Item 6 — musannaf UR HN 5898, 22496 (plvvlqj gibberish)
- **Source:** tohed.com (renders Urdu). `https://en.tohed.com/hadith/musannaf-ibn-abi-shaybah/<HN>/` — confirmed renders English + Urdu.
- **Local:** `hadith-api-toon-new/musannaf_ibn_abi_shaybah_final.json` has these HNs but `translations` only has `en` (no `ur`) — so local can't restore UR. AR is intact (ar_len 221/238).
- **Procedure:**
  1. Fetch tohed for HN 5898 and 22496, parse the Urdu hadith body.
  2. Replace the `plvvlqj`-corrupted `text` field in `editions/musannaf-ibn-abi-shaybah/translations/ur/sections/<N>.toon` rows.
- **Fallback if tohed UR absent for these HNs:** LLM translate from intact AR, prefix `[AI-translation]`.
- **Risk:** musannaf-ibn-abi-shaybah numbering is per-hadith (the backup has 37943 sections = hadiths). Confirm tohed uses same HN. Low.

### Item 7 — shamail-tirmidhi UR HN161 (AI self-monologue)
- **Source:** LOCAL `~/code/hadith-api-toon-new/shamail-tirmazi_final.json` (247K, has translations) + tohed (shamail-tirmidhi=200, renders Urdu).
- **Procedure:**
  1. Load `shamail-tirmazi_final.json`, find HN161, read its `translations.ur` (or `translations['ur']`).
  2. If present + clean (no `PARAM` loop): replace the row's `text` in `editions/shamail-tirmidhi/translations/ur/sections/25.toon` HN161.
  3. If local also corrupt: fetch tohed `https://en.tohed.com/hadith/shamail-tirmidhi/161/`, parse Urdu.
- **Risk:** low.

### Item 8 — sahih-ibn-khuzaymah index (1059 malformed rows + 320 chapter_intro Urdu-contaminated)
- **Source:** LOCAL `~/code/hadith-api-toon-new/sahih_ibn_khuzaymah_final.json` (3.2M) — clean section metadata (section name, HN range) per section. Also `scripts/cache` may have khuzaymah; tohed `sahih-ibn-khuzaymah`=200 for verify.
- **Procedure:**
  1. From `sahih_ibn_khuzaymah_final.json`, rebuild the `info.toon` section index: per section → `hadith_first`, `hadith_last`, `arabic_first`, `arabic_last`, `name` (Arabic, properly escaped — escape inner `"` → `""`).
  2. Overwrite `editions/sahih-ibn-khuzaymah/info.toon` section index block with the rebuilt clean index.
  3. For the 320 chapter_intro Urdu-contaminated AR rows: re-derive each section's chapter_intro from the clean section name in the final.json, overwrite the `chapter_intro` field in every row of `editions/sahih-ibn-khuzaymah/sections/<N>.toon`.
- **Risk:** re-quoting 1059 rows — use python csv writer with proper escaping, not string concat.

### Item 9 — silsila-sahih EN (~3182 of 3550 empty after scraper-residue strip)
- **Source:** LOCAL `~/code/hadith-api-toon-alt/hadith islam360/silsila.db` (sqlite: `hadees` 3704 rows + `hadees_languages` with per-language text) AND `~/code/hadith-api-toon-new/silsila_sahih_final.json` (2.2M, has `translations`).
- **Procedure:**
  1. Inspect `silsila.db`: `SELECT * FROM hadees JOIN hadees_languages ON ... WHERE language_id=(SELECT id FROM language WHERE name='English')` — get 3704 English hadiths.
  2. OR load `silsila_sahih_final.json`, extract `translations.en` per hadith.
  3. Map to repo HN (verify silsila-sahih numbering matches repo). Fill the empty `text` fields in `editions/silsila-sahih/translations/en/sections/*.toon`.
  4. Verify the 3182 empties now have text; re-run audit `empty_text` count → should drop sharply.
- **Risk:** HN mapping between islam360/final.json and repo. Verify 5 HNs before bulk.

### Item 10 — abudawud BN HN4588 (vowel corruption)
- **Source:** **LOCAL** `~/code/hadith-api-toon/scripts/cache/ben-abudawud.min.json` (fawaz Bengali, 7.6M) — verified clean Bengali.
- **Procedure:**
  1. Load `ben-abudawud.min.json`, build `HN → text` map.
  2. Find HN4588 row in `editions/abudawud/translations/bn/sections/<N>.toon`, replace the vowel-corrupted `text` with the clean fawaz Bengali.
- **Risk:** fawaz BN HN = abudawud sunnah numbering; repo abudawud uses same. Verify the HN matches (note: KNOWN_ISSUES says "was 4595" → confirm 4588 vs 4595 against AR row). Low.

---

## LLM-translation fallback section

Only **1 item** genuinely has no human source: **lulu-wal-marjan EN (281 hadiths)**.

- Use openrouter (6 API keys), strong model (Claude/GPT-class for faithful translation).
- Source = intact Arabic from `editions/lulu-wal-marjan/sections/<N>.toon`.
- Output prefixed `[AI-translation] ` per row.
- No commentary, no preamble, preserve proper-name transliteration, faithful hadith register.
- Cost: 281 translations. Acceptable.
- Mark in `info.toon` that lulu EN is AI-translated pending scholarly replacement.

If during execution any other item's chosen source turns out empty for a specific HN (e.g. tohed missing ibnhibban HN3610), fall back to LLM from intact AR for THAT HN only, same `[AI-translation]` prefix. Do not bulk-LLM items that have a human source.

---

## Do-not-recover / accept-loss section

**None currently.** All 10 items have a path (9 human source, 1 LLM). If lulu EN LLM is declined (you prefer no AI), then lulu EN = accept-loss (281/1906 missing), documented in `info.toon`. No AR is lost — only EN translation.

---

## Recommended execution order

1. **Local-fawaz rescrape first** (bulk, clean, fast, no network): items 3 (ibnmajah FR), 10 (abudawud BN) — just read local JSON, write rows.
2. **Local-final.json rescrape**: items 5 (nasai sec36), 7 (shamail UR), 8 (khuzaymah index), 9 (silsila EN) — read local JSON/sqlite, write.
3. **tohed rescrape** (live, polite delay): items 1+2 (ibnhibban EN, 16 HNs), 6 (musannaf UR, 2 HNs) — tohed renders these.
4. **LLM last**: item 4 (lulu EN, 281) — only after confirming no source. Mark `[AI-translation]`.
5. After all: re-run `toon_audit.py` on changed files → confirm `empty_text`/`ai_leakage`/`json-ld`/`placeholder` counts drop; load 1 sample in `viewer.html` → parse OK; commit per item.

---

## Risk notes
- **Slug mismatch:** tohed `sahih-ibn-hibban` ≠ repo `ibnhibban`; `musannaf-ibn-abi-shaybah` matches; `shamail-tirmidhi` matches; `sahih-ibn-khuzaymah` matches. Verify each before bulk.
- **HN numbering:** fawaz/tohed use sunnah-standard numbering; repo may have edition-local numbering. Verify 1 HN per edition before bulk.
- **Cloudflare:** sunnah.com root 403; existing `scrape_sunnah_*.py` had access — reuse those scripts if sunnah is needed (not needed for these 10 items).
- **Local backup cleanliness:** verified fawaz FR + fawaz BN are clean; verified alt ibnmajah/fr is DIRTY (same AI preamble) — use fawaz cache, not alt. Always check a sample HN before trusting a backup.
- **Re-quoting:** khuzaymah index re-write must use proper CSV escaping (python csv), not string concat, or it re-corrupts.
- **Tamil nasai:** confirm `tam-nasai` exists in cache; if not, Tamil sec36 → LLM.
- **hadithunlocked.com:** excluded entirely. Never use.

---

## Source files created during this probe
- `toon_sourcefind_workflow.js` — the probe workflow (partially run, 5/10 agents completed before local sources made it redundant; their tohed/fawaz confirmations are incorporated above).

## Verification of this plan (what was actually checked)
- fawaz CDN editions.json → canonical-4 only.
- tohed per-edition 200 status: nasai, shamail-tirmidhi, musannaf-ibn-abi-shaybah, sahih-ibn-khuzaymah, sahih-ibn-hibban (slug). tohed lulu = 404 (all slug variants).
- tohed musannaf HN5898 page renders English + Urdu; tohed ibnhibban HN1139 renders English.
- fawaz `fra-ibnmajah.min.json`: HN 597/1311/1855/2271/4316 all CLEAN (no Voici).
- alt `ibnmajah/fr.json`: HN 597/1311/1855/2271/4316 all DIRTY (Voici preamble) → not used.
- alt `ibnhibban/en.json`: target HNs present but text EMPTY (len 0) → why JSON-LD filled; not usable → tohed.
- `musannaf_ibn_abi_shaybah_final.json`: HN 5898/22496 present, AR intact (len 221/238), translations has only `en` (no `ur`) → tohed for UR.
- `silsila.db`: 3704 hadees + hadees_languages (per-language text) → silsila EN source.
- `sahih_ibn_khuzaymah_final.json` (3.2M), `nasai_final.json` (46M), `shamail-tirmazi_final.json` (247K), `silsila_sahih_final.json` (2.2M): all present, non-empty.
- `ben-abudawud.min.json`: fawaz Bengali, 7.6M, clean → abudawud BN.
