# RECOVERY REPORT — hadith .toon truncation audit

Scope: 30 books, 59,158 truncated rows identified. Of these, **40,201 are recoverable** from existing scholarly/local sources and **18,957 need scholarly rescrape** (no source exists for the truncated language at that HN). No LLM/MT is recommended or used for recovery; LLM is only the existing AI-translation track already applied to `silsila-sahih` EN and `lulu-wal-marjan`/`silsila-sahih` EN inserts (clearly badged `[AI-translation]`), which are out of scope for this scholarly-recovery pass.

Total truncated: **59,158** · Recoverable: **40,201** (backup 38,946 / external 1,255) · Needs rescrape: **18,957**.

---

## 1. Per-source availability table

`full` = capacity (hadiths that source can fill), not deduplicated against other sources. "Scholarly" = human translation; MT/AI and Hadith Unlocked are excluded by task rules.

| Source | Path / URL | Books covered | Langs | HN scheme → repo HN | Truncations recoverable (dedup contribution) |
|---|---|---|---|---|---|
| alt repo (pre-fix backups) | `~/code/hadith-api-toon-alt/<book>/<lang>.json` | abudawud, aladab-almufrad, bayhaqi, bukhari, ibnhibban(empty), malik, mishkat, muajam-tabarani-saghir, musannaf-ibn-abi-shaybah, muslim, musnad-ahmad, nasai-kubra, sahih-ibn-khuzaymah, sunan-al-daraqutni, sunan-darimi, tirmidhi | en/ur/ar (varies) | SAME (hadithnumber field == repo HN) for most; malik uses `refnum`/`refnum.sub` (repo 183602 → alt `1836.2`); mustadrak under `hakim/` subdir | 2334 (bukhari), 577 (muslim), 3955 (tirmidhi), 1357 (malik), 132 (mishkat), 68 (bayhaqi), 64 (sunan-darimi), 30 (muajam), 9 (khuzaymah UR), 11 (musnad-ahmad), 17 (nasai-kubra), 203 (aladab) |
| new repo pre-conversion final | `~/code/hadith-api-toon-new/<book>_final.json` | aladab-almufrad, bayhaqi (corrupt-EXCL), bulugh, ibnmajah, malik, mishkat, mustadrak, nasai, nasai-kubra(no-different book), nawawi, qudsi, riyadussalihin, sahih-ibn-khuzaymah, shamail-tirmidhi, sunan-al-daraqutni, sunan-darimi, tirmidhi, silsila-sahih | en/ur/bn/fr/id/tr/ro | SAME (keyed by HN string) for most; bulugh/shamail `tirmazi_final` DIFFERENT_SCHEME (match by normalized arabic); malik `refnum`, repo HN>5000 → HN//100; muslim/nasai DIFFERENT_SCHEME (sunnah per-book HN) — EXCLUDED | 9960 (tirmidhi), 4089 (malik), 1083 (nasai), 12 (aladab), 6 (sunan-darimi), 11 (khuzaymah), 1 (mishkat), 48 (shamail), 16 (musnad-ahmad via ahmad_final), 0 (riyad — DIFFERENT scheme) |
| ahmed source (sunnah.com scrape) | `~/code/hadith-api-toon-new/<book>_source/ahmed_<book>.json` | aladab-almufrad, bulugh-al-maram | en | SAME (`idInBook` == repo HN for adab); bulugh DIFFERENT_SCHEME (globalNum, match by arabic) | 2 (aladab), 63 (bulugh — same data as final) |
| fawaz CDN local cache | `~/code/hadith-api-toon/scripts/cache/<lang3>-<book>.min.json` | abudawud, bukhari, ibnmajah, malik, muslim, nasai, nawawi, qudsi, shamail(none), tirmidhi, dehlawi | en/ur/bn/fr/id/tr/ro | SAME (hadithnumber 1..N) for abudawud/bukhari/ibnmajah/muslim/nawawi/qudsi; tirmidhi/nasai DIFFERENT_SCHEME (fawaz own HN, map by arabic LCP≥200); malik sequential==refnum | 4321 (ibnmajah), 4485→395 (malik, partial), 8574 (muslim), 5240 (nasai), 3865 (tirmidhi) |
| fawaz repo clone (hadith-api-1) | `~/hadith-api-1/editions/<lang3>-<book>.min.json` + `~/hadith-api-1/database/originals/<lang3>-<book>.txt` | abudawud, bukhari, ibnmajah, malik, muslim, nasai, nawawi, qudsi, tirmidhi, lulu-via-bukhari/muslim editions | en/ur/bn/fr/id/tr | SAME as cache; tirmidhi/nasai DIFFERENT_SCHEME; lulu mapped via arabic substring to bukhari/muslim HN | 121 (lulu←bukhari), 13 (lulu←muslim), 3956 (tirmidhi), 0 extra vs cache elsewhere |
| fawaz CDN live (jsdelivr, canonical-4 only) | `https://cdn.jsdelivr.net/.../eng-<book>.min.json` etc. | abudawud, ibnmajah, malik, nasai ONLY (canonical-4) | en/ur/bn/fr/id/tr | SAME as local cache (byte-qual) | 0 new (redundant with local cache) |
| git history (`.toon` section files) | `editions/<book>/translations/<lang>/sections/<N>.toon` @ older commits | bayhaqi, bukhari, ibnhibban, mustadrak, nasai, nasai-kubra, shamail, sunan-al-daraqutni, others | en/ur | SAME (hadithnumber == repo HN); daraqutni commit `352319d6c6` pre-normalization | 232 (daraqutni), 68 (mustadrak baseline `2e34386ffd`), 3 (nasai), 2 (bukhari roman-ur), 0 elsewhere (truncation predates history) |
| islam360 sqlite | `~/code/hadith-api-toon-alt/hadith islam360/<book>.db` | abudawud(MISALIGNED-EXCL), bukhari, mishkat(none), muslim, nasai, silsila(garbled-EXCL) | en/ur | SAME HN but abudawud content MISALIGNED (different hadith at same HN); silsila UR custom-font ciphered | 0 (excluded) |
| tohed.com (live) | `https://en.tohed.com/<slug>/<HN>` (EN), `https://tohed.com/<slug>/<HN>` (UR) | ibnhibban, sahih-ibn-khuzaymah, shamail-tirmidhi, (nasai, musannaf-ibn-abi-shaybah, sahih-ibn-hibban — not applied) | en/ur | SAME (tohed HN == repo HN, verified by content match); khuzaymah high HNs >3229 return 404 | 1108 (ibnhibban), 87 (khuzaymah), 50+25→27 dedup (shamail) |
| al-hadees.com (live) | `https://al-hadees.com/hadees/<slug>/<HN>` | musnad-ahmad, bayhaqi, mustadrak, sunan-darimi, sahih-ibn-khuzaymah, fath-al-rabbani(via ahmad), silsila-sahih | ur (+ar) | SAME (`Hadees Number` == repo HN); mustadrak abridged at source (~280 chars) | 1 (fath-al-rabbani, via pre-scraped `ahmad_ur.json`); 0 new elsewhere (source itself short/abridged) |
| quranohadith.com (live + scraped backup) | `~/code/hadith-api-toon/scraped_data/muajam-tabarani-saghir/urdu.toon` (HN 1-500), live pages 501-1190 | muajam-tabarani-saghir, silsila-sahih | ur | DIFFERENT_SCHEME (site_HN 1-1190; footer `عربی حدیث: N` maps site_HN → repo arabic HN, non-monotonic) | 30 (local backup) + 32 (live) = 62 (muajam) |
| HuggingFace datasets | `hf://datasets/freococo/musannaf_ibn_abi_shaybah`, `M-AI-C/bukhari_en` | musannaf-ibn-abi-shaybah, bukhari (mirror only) | en | DIFFERENT_SCHEME (hadith_id 1-37943, no constant offset; match by arabic jaccard≥0.6) | 1 (musannaf HN1612←HF 1602); bukhari HF is sunnah mirror, 0 new |
| sunnah.com ajax (live) | `https://sunnah.com/ajax/{english,urdu,bangla}/<book>/<page>` | bukhari, abudawud, tirmidhi(EN), malik(EN), ibnmajah(redundant), muslim(via URN crosswalk) | en (urdu/bangla 500/403 for several) | DIFFERENT_SCHEME (per-book hadithNumber == sunnah global; crosswalk via `matchingArabicURN`) | 6 (malik EN, partial); 0 new elsewhere (redundant/403-blocked) |
| ahmedbaset cache | `~/code/hadith-api-toon/scripts/cache/ahmedbaset_<book>.json` | abudawud, ahmad, bukhari, darimi, ibnmajah, malik, muslim, nasai, tirmidhi | en/ur | SAME (`idInBook` == repo HN) | 0 (superseded by alt/final for covered books) |
| Bayhaqi fawaz cache (`scripts/cache/bayhaqi.json`) | local | bayhaqi | — | SAME | EXCLUDED (Hadith Unlocked source, prohibited) |
| `scripts/cache/daraqutni.json` | local | sunan-al-daraqutni | — | SAME | EXCLUDED (Hadith Unlocked, prohibited) |
| `scripts/cache/ibnhibban.json` | local | ibnhibban | — | SAME | EXCLUDED (Hadith Unlocked, prohibited) |

Sources that yielded **zero** usable recovery across all books: al-hadees.com live (genuinely short/abridged at source for mustadrak, daraqutni, khuzaymah-low-HN, ahmad-cross-refs), islam360 (misaligned/ciphered), fawaz CDN live (redundant with local cache), sunnah.com ajax (403/500-blocked or redundant), HuggingFace bukhari mirror.

---

## 2. Per-book table

`backup` = recoverable from local files / git / local caches. `external` = recoverable only via live network fetch (tohed, quranohadith, HF). `needs rescrape` = total − recoverable (no scholarly source found for that lang@HN).

| Book | Total trunc | Recoverable (backup) | Recoverable (external) | Needs rescrape | Primary source |
|---|---:|---:|---:|---:|---|
| abdurrazzaq | 0 | 0 | 0 | 0 | — |
| abudawud | 985 | 764 | 0 | 221 | fawaz cache (canonical-4) |
| aladab-almufrad | 310 | 206 | 0 | 104 | alt repo `adab/{en,ur}.json` |
| bayhaqi | 4,843 | 68 | 0 | 4,775 | alt repo `bayhaqi/{ar,en,ur}.json` |
| bukhari | 2,907 | 2,334 | 0 | 573 | alt repo `bukhari/<lang>.json` (sunnah scrape) |
| bulugh-al-maram | 81 | 63 | 0 | 18 | `bulugh_almaram_final.json` (arabic-text match) |
| dehlawi | 0 | 0 | 0 | 0 | — |
| fath-al-rabbani | 4 | 1 | 0 | 3 | pre-scraped `ahmad_ur.json` (al-hadees capture) |
| ibnhibban | 1,134 | 0 | 1,108 | 26 | **tohed.com live** (en) |
| ibnmajah | 4,632 | 4,321 | 0 | 311 | fawaz cache `eng/urd-ibnmajah.min.json` |
| lulu-wal-marjan | 269 | 134 | 0 | 135 | fawaz `eng-bukhari`+`eng-muslim` (arabic substring match) |
| malik | 5,649 | 4,485 | 0 | 1,164 | `malik_final.json` + alt + fawaz-cache |
| mishkat | 134 | 133 | 0 | 1 | alt repo `mishkat/<lang>.json` |
| muajam-tabarani-saghir | 1,190 | 30 | 32 | 1,128 | quranohadith local backup + live |
| musannaf-ibn-abi-shaybah | 467 | 0 | 1 | 466 | **HuggingFace** (en, 1 row); rest unsourced |
| muslim | 10,720 | 9,151 | 0 | 1,569 | fawaz cache `fz_muslim` + alt |
| musnad-ahmad | 1,090 | 504 | 0 | 586 | alt `backup_pre_fix/ahmad/ur.json` |
| mustadrak | 664 | 71 | 0 | 593 | alt `hakim/` subdir + git `2e34386ffd` |
| nasai | 7,951 | 6,326 | 0 | 1,625 | fawaz cache + `nasai_final.json` (arabic-head match) |
| nasai-kubra | 18 | 17 | 0 | 1 | alt `nasaikubra/{en,ur}.json` |
| nawawi | 0 | 0 | 0 | 0 | — |
| qudsi | 1 | 0 | 0 | 1 | none (FR HN36, source genuinely short) |
| riyadussalihin | 3 | 3 | 0 | 0 | alt `riyadussalihin/en.json` |
| sahih-ibn-khuzaymah | 197 | 20 | 87 | 90 | **tohed.com live** (en) + alt UR + new |
| shamail-tirmidhi | 85 | 53 | 27 | 5 | `shamail_muhammadiyah_final.json` + `tirmazi_final` + **tohed live** |
| silsila-sahih | 22 | 0 | 0 | 22 | none scholarly (EN is AI; UR source lacks high HNs) |
| sunan-al-daraqutni | 2,517 | 232 | 0 | 2,285 | git `352319d6c6` (pre-normalization) |
| sunan-darimi | 106 | 70 | 0 | 36 | alt `darimi/{en,ur,ar}.json` + `darimi_final.json` |
| tirmidhi | 13,179 | 9,960 | 0 | 3,219 | `tirmidhi_final.json` + alt + fawaz cache (arabic LCP match) |
| virtues | 0 | 0 | 0 | 0 | — |
| **TOTAL** | **59,158** | **38,946** | **1,255** | **18,957** | |

---

## 3. Numbering-mapping reference (repo HN → source HN)

- **alt repo `{hadithnumber,text}`** — direct: `source.hadithnumber == repo HN`. Exceptions:
  - `malik`: alt key is `refnum` or `refnum.sub`; repo HN `183602` → alt `1836.2`; repo HN `958` → `958`. Repo HN >5000 → `HN//100`.
  - `bukhari`: pure numeric == repo HN; `b`/`c` suffix → parent (combined concatenated); roman-ur keyed under `ro`.
- **new `<book>_final.json`** — keyed by HN string == repo HN, except:
  - `muslim`, `nasai` (appendix region): sunnah per-book HN, NOT repo HN — **EXCLUDED** (offset varies per hadith; injecting would paste wrong text). Do not use without a URN/anchor crosswalk.
  - `bulugh`, `shamail_muhammadiyah` (appendix), `shamail_tirmazi_final`: map by **normalized-arabic exact match** (strip opener/diacritics); 410/417 exact for shamail, 3 prefix-matched, appendix HN 403-417 → source 388-402.
  - `malik`: `refnum` string; repo HN >5000 → `HN//100`.
  - `riyadussalihin`: DIFFERENT (final HN1 = repo HN680) — use `riyadussalihin_map_direct.json` or alt instead.
- **fawaz CDN cache/clone `<lang3>-<book>.min.json`** — `hadiths[].hadithnumber`:
  - SAME for abudawud, ibnmajah, muslim, nawawi, qudsi, malik (sequential == refnum).
  - bukhari: pure numeric SAME; `b` encoded as `N.2`, `c` as `N.3` (e.g. 402b → 402.2).
  - **tirmidhi, nasai**: DIFFERENT_SCHEME (fawaz own HN, no constant offset; nasai has OFFSET(-1) in scattered ranges + appendix divergence). Map by **normalized arabic head (opener-stripped, first 80 chars) LCP ≥ 200** (tirmidhi) / exact head (nasai). 3575/3955 tirmidhi mapped.
- **fawaz live (canonical-4)** — identical to local cache; no mapping needed beyond cache.
- **git history `.toon`** — SAME (hadithnumber == repo HN) in all cases. For daraqutni use pre-normalization commit `352319d6c6`.
- **islam360 sqlite** — SAME HN but abudawud content **MISALIGNED** (different hadith at same HN; longer text is `Narrated X:` prefix inflation). **Do not use for abudawud.** silsila UR is custom-font ciphered — unusable.
- **tohed.com** — SAME: URL `<HN>` == repo HN (verified by arabic content match for ibnhibban HN116/139/1230, khuzaymah, shamail 10 sample HNs). khuzaymah HN >~3229 → 404 (out of tohed range).
- **al-hadees.com** — SAME (`Hadees Number` == repo HN). Page param is pagination (30/page). mustadrak renders **abridged** excerpt (~280 chars) — do not treat as full.
- **quranohadith.com (muajam-tabarani-saghir)** — DIFFERENT: source keyed by site_HN (1-1190); footer `عربی حدیث: N` maps site_HN → repo arabic HN (non-monotonic). Local `urdu.toon` covers HN 1-500 (site), live covers 501-1190.
- **HuggingFace musannaf** — DIFFERENT (`hadith_id` 1-37943, no constant offset; offsets −1155, −667, −12, …). Match by **arabic jaccard ≥ 0.6** to locate HF HN. No UR column.
- **sunnah.com ajax** — DIFFERENT: `hadithNumber` is per-book == sunnah global; crosswalk via `matchingArabicURN` → repo HN. Not used for bulk recovery (redundant or 403-blocked).
- **fath-al-rabbani** — COMBINED: repo HN178 → Musnad Ahmad HN3758 + HN3707, parsed from `(مسند أحمد: N)` refs embedded in the arabic row.

---

## 4. Existing scraper scripts inventory

All in `~/code/hadith-api-toon/` unless noted.

| Script | Scrapes | URL pattern | Books / langs |
|---|---|---|---|
| `scrape_sunnah_bukhari.py` | sunnah.com ajax + HTML | `https://sunnah.com/ajax/{english,urdu,bangla}/bukhari/<page>`, `https://sunnah.com/bukhari/<n>` | bukhari (en/ur/bn) |
| `scrape_ahmad_alhadees.py` | al-hadees.com index+pages | `https://al-hadees.com/hadees-name/musnad-ahmed/0` → per-HN pages | musnad-ahmad (ur/ar) |
| `scrape_alhadees_full.py` | al-hadees.com, generic book | `https://al-hadees.com` book_id driven | musnad-ahmad, bayhaqi (parameterized) |
| `scrape_bayhaqi_alhadees.py` | al-hadees.com bayhaqi | `https://al-hadees.com/hadees-name/bayhaqi/0` → `~/code/hadith-api-toon/sunnah.com-download/bayhaqi/` | bayhaqi (ur/ar) |
| `scrape_ibnhibban_urdu.py` | (urdu fill for ibnhibban) | — | ibnhibban ur |
| `sunnah.js` | sunnah.com ajax (node) | `/ajax/<lang>/<book>/<page>` | generic sunnah collections |
| `recover_glm_en.py` | **LLM** (local glm-5-2 gateway) — NOT scholarly | `http://localhost:8317/v1/chat/completions` | lulu-wal-marjan + silsila-sahih EN inserts (AI-badged) |
| `recover_llm_en.py` | **LLM** (openrouter free models) — NOT scholarly | openrouter API | lulu / silsala EN (AI-badged) |
| `recover_silsila_en.py` | **LLM** fill — NOT scholarly | — | silsila-sahih EN |
| `test_sunnah_ajax*.py`, `test_sunnah_*.py`, `test_pagination*.py`, `test_page_*.py`, `test_subjects.py`, `test_scraper_dom.py` | probes | sunnah ajax endpoints | diagnostic only |
| `scripts/convert_ibnhibban_urdu.py`, `scripts/descramble_urdu_translations.py`, `scripts/realign_tabarani_english.py`, `scripts/strip_ocr_footnotes.py` | post-processing | — | urdu descramble, tabarani realign |

**Gap: no scraper exists for** tohed.com, quranohadith.com (muajam live pages 501-1190), HuggingFace (musannaf parquet), or sunnah.com collections beyond bukhari. Recovery from external sources (ibnhibban/khuzaymah/shamail via tohed, muajam via quranohadith, musannaf via HF) will require new one-off fetch scripts (patterns below).

---

## 5. Recommended recovery execution plan (priority order)

Pull from the **first source that holds a fuller scholarly text** per book. Local backups first (no network), then external.

1. **tirmidhi** (9,960) — `~/code/hadith-api-toon-new/tirmidhi_final.json` (SAME-keyed, primary) → alt `tirmidhi/<lang>.json` → fawaz cache `scripts/cache/<lang3>-tirmidhi.min.json` (arabic LCP≥200 map) → `~/hadith-api-1/editions`. 3,219 remainder: no scholarly source (sunnah urdu/bangla ajax 500; al-hadees empty body).
2. **muslim** (9,151) — fawaz cache `scripts/cache/fz_muslim.json` + `<lang3>-muslim.min.json` (SAME HN) → alt `muslim/<lang>.json` (577 extra). 1,569 remainder unsourced.
3. **nasai** (6,326) — fawaz cache `<lang3>-nasai.min.json` (arabic-head match, ~4752 SAME + scattered −1 + appendix) → `nasai_final.json` (1,083, DIFFERENT scheme, arabic match) → git history (3). 1,625 remainder: tohed.com live viable for en + partial ur (not yet bulk-fetched); islam360 sqlite potential tr/ur (not loaded).
4. **malik** (4,485) — `~/code/hadith-api-toon-new/malik_final.json` (4,089) → alt `malik/<lang>.json` (1,357) → fawaz cache/local (395). Aggregate-pick longest per row. 1,164 remainder unsourced.
5. **ibnmajah** (4,321) — fawaz cache `scripts/cache/eng-ibnmajah.min.json` + `urd-ibnmajah.min.json` (canonical-4, SAME HN). 311 remainder unsourced (sunnah redundant/403).
6. **bukhari** (2,334) — alt `bukhari/<lang>.json` (sunnah scrape, 7,277 capacity) → `bukhari_final.json` → fawaz cache/clone → git history (2 roman-ur). 573 remainder: sunnah ajax live needs URN crosswalk (not done).
7. **sunan-al-daraqutni** (232) — git commit `352319d6c6` (pre-normalization, SAME HN). 2,285 remainder: al-hadees live == repo (short at source); no scholarly source for UR — **rescrape needed**.
8. **bayhaqi** (68) — alt `bayhaqi/{ar,en,ur}.json` (SAME, ignore text-embedded −6 display offset, use `hadithnumber` field). 4,775 remainder: al-hadees ur == repo (already truncated); no scholarly source — **rescrape needed**.
9. **abudawud** (764) — fawaz cache `scripts/cache/eng-abudawud.min.json` (canonical-4) + alt + pre-conversion final. 221 remainder unsourced (islam360 MISALIGNED — excluded).
10. **aladab-almufrad** (206) — alt `adab/{en,ur}.json` (203) → `aladab_almufrad_final.json` (12) → `ahmed_aladab_almufrad.json` (2). 104 remainder: sunnah.com ajax 403, fawaz/tohed/HF all absent — **rescrape needed**.
11. **musnad-ahmad** (504) — alt `backup_pre_fix/ahmad/ur.json` (504) → `ahmad_final.json` (16) → alt `ahmad/ur.json` (11). 586 remainder: sunnah urdu 500; al-hadees gives cross-ref placeholders at source — **rescrape needed**.
12. **musannaf-ibn-abi-shaybah** (1) — HuggingFace `freococo/musannaf_ibn_abi_shaybah` parquet (arabic jaccard≥0.6; en only; repo HN1612 → HF 1602). 466 remainder: tohed DIFFERENT_SCHEME (no per-HN map); new-final different edition — **rescrape needed**.
13. **muajam-tabarani-saghir** (62) — local `scraped_data/muajam-tabarani-saghir/urdu.toon` (30, site_HN 1-500 via footer map) → quranohadith.com live (32, site_HN 501-1190). **New live-fetch script needed** (footer-parse map). 1,128 remainder: EN has no translation body anywhere — **rescrape needed**.
14. **ibnhibban** (1,108) — **tohed.com live** (`https://en.tohed.com/ibnhibban/<HN>`, SAME HN). **New tohed fetch script needed.** 26 remainder (high HNs / ur).
15. **sahih-ibn-khuzaymah** (107) — alt `ur.json` (al-hadees human UR, 9) + new final (11) + **tohed.com live** (87, `https://en.tohed.com/sahih-ibn-khuzaymah/<HN>`, HN ≤~3229). 90 remainder: alt `en.json` is MT (excluded); high HNs >3229 not on tohed — **rescrape needed**.
16. **shamail-tirmidhi** (80) — `shamail_muhammadiyah_final.json` (48, arabic match) → `shamail_tirmazi_final.json` (5) → **tohed.com live** EN `https://en.tohed.com/shamail-tirmidhi/<HN>` (50) + UR `https://tohed.com/shamail-tirmidhi/<HN>` (25). 5 remainder unsourced.
17. **lulu-wal-marjan** (134) — fawaz clone `eng-bukhari.min.json` (121, arabic substring match to lulu HN) + `eng-muslim.min.json` (13). 135 remainder unsourced (EN truncated at first import; UR never truncated).
18. **bulugh-al-maram** (63) — `bulugh_almaram_final.json` (sunnah scrape, globalNum→repo HN by normalized-arabic match) + `ahmed_bulugh_almaram.json`. 18 remainder unsourced (sunnah ajax 403).
19. **sunan-darimi** (70) — alt `darimi/{en,ur,ar}.json` (64) → `darimi_final.json` (6). 36 remainder unsourced.
20. **mustadrak** (71) — alt `hakim/` subdir (69, SAME HN 1-8803) → git `2e34386ffd` (68). 593 remainder: al-hadees abridged at source (~280 chars) — **rescrape needed**.
21. **mishkat** (133) — alt `mishkat/<lang>.json` (132) → `mishkat` new final (1). 1 remainder (UR HN1, no fuller in git/alt).
22. **nasai-kubra** (17) — alt `nasaikubra/{en,ur}.json` (SAME 1..11385). 1 remainder (ur HN307).
23. **riyadussalihin** (3) — alt `riyadussalihin/en.json` (SAME, all 1,896 HNs). 0 remainder.
24. **fath-al-rabbani** (1) — pre-scraped `~/code/hadith-api-toon-alt/.../ahmad_ur.json` (al-hadees capture), repo HN178 → Musnad-Ahmad HN3758+3707 via embedded `(مسند أحمد: N)` refs. 3 remainder (UR) — **rescrape needed**.
25. **silsila-sahih** (0 scholarly) — EN is entirely AI-translated (badged); UR source (quranohadith/al-hadees) lacks HN>500. 22 remainder — **scholarly rescrape needed** (no scholarly EN ever existed).
26. **qudsi** (0) — 1 FR truncation (HN36); all sources have the same 738-char text. **Scholarly rescrape needed** (French).
27. **abdurrazzaq / dehlawi / nawawi / virtues** — 0 truncations; nothing to do.

New scripts to write (one-off, small): tohed fetcher (`en.tohed.com` + `tohed.com`), quranohadith live fetcher (site_HN 501-1190 with footer-parse), HF parquet loader for musannaf. Each <60 lines following `scrape_bayhaqi_alhadees.py` shape.

---

## 6. Hard cases — NO scholarly source exists for the truncated language@HN

These **must not** be LLM-filled. They require scholarly human rescrape (or acceptance of permanent gap). Listed by book with the gap:

| Book | Gap (needs rescrape) | Lang | Why no source |
|---|---:|---|---|
| **bayhaqi** | 4,775 | en/ur | al-hadees.com ur == repo (already truncated at source); fawaz/tohed/sunnah do not carry bayhaqi; `bayhaqi_final.json` en misaligned + ur mojibake (pre-descramble). Only scholarly path: human UR translation of the 4,775 arabic rows. |
| **sunan-al-daraqutni** | 2,285 | ur | al-hadees live UR == repo exactly (short at source); meta-description maps to a *different* hadith (narrator mismatch); fawaz/tohed/sunnah absent. Scholarly UR rescrape required. |
| **muajam-tabarani-saghir** | 1,128 | en (+ ur remainder) | EN has *no translation body anywhere* (local + live quranohadith EN is header stub only); `final.json` "ur" is arabic-with-diacritics mislabeled. Scholarly EN rescrape required. |
| **mustadrak** | 593 | en/ur | al-hadees renders abridged ~280-char excerpt (truncation at source); fawaz/tohed/sunnah/islam360 absent for mustadrak. Scholarly rescrape of full matn required. |
| **musannaf-ibn-abi-shaybah** | 466 | en/ur | tohed DIFFERENT_SCHEME (no per-HN map, no urdu block); `new-final` is a different edition (arabic jaccard<0.3); alt-repo IS the truncation source; HF has en-only + 1 match. Scholarly rescrape required. |
| **silsila-sahih** | 22 | en/ur | EN is entirely AI-translated (no scholarly EN ever existed — git sections were empty placeholders before the AI-fill commit `6b65fcf25e`); UR source (quranohadith=al-hadees) lacks HN>500. Scholarly EN+UR rescrape required (or accept AI-badged EN). |
| **muslim** | 1,569 | (mixed) | fawaz cache + alt cover 9,151; remainder rows have no fuller scholarly source (fawaz empty at those HNs; final.json DIFFERENT scheme; sunnah 403/URN-crosswalk needed). Scholarly rescrape for remainder. |
| **tirmidhi** | 3,219 | ur/bn | sunnah urdu/bangla ajax HTTP 500; al-hadees empty body; tohed ur not probed for bulk. Scholarly UR/BN rescrape required for remainder. |
| **nasai** | 1,625 | (mixed) | tohed live viable for en+partial ur but not yet bulk-fetched; islam360 sqlite potential tr/ur (not loaded). Rescrape-or-load needed for remainder after tohed pass. |
| **malik** | 1,164 | (mixed) | final/alt/fawaz cover 4,485; remainder unsourced. Scholarly rescrape for remainder. |
| **ibnmajah** | 311 | (mixed) | fawaz empty at those HNs; sunnah redundant/403. Scholarly rescrape for remainder. |
| **bukhari** | 573 | (mixed) | alt/final/fawaz cover 2,334; remainder needs sunnah URN→repoHN crosswalk (not built) or scholarly rescrape. |
| **abudawud** | 221 | (mixed) | fawaz empty at those HNs; islam360 misaligned (excluded); sunnah redundant. Scholarly rescrape for remainder. |
| **aladab-almufrad** | 104 | en/ur | sunnah ajax 403; fawaz/tohed/HF all 404 for adab. Scholarly rescrape required. |
| **musnad-ahmad** | 586 | ur | sunnah urdu 500; al-hadees gives short cross-ref placeholders at source (verified HN21584 identical in git `9947afede6`). Scholarly UR rescrape required. |
| **lulu-wal-marjan** | 135 | en | EN truncated at first import (never full in git history, 7 commits same lengths); UR never truncated; sunnah 403. Scholarly EN rescrape required. |
| **bulugh-al-maram** | 18 | en | sunnah ajax 403; final/ahmed cover 63; remainder unsourced. Scholarly rescrape. |
| **sunan-darimi** | 36 | en/ur | alt/final cover 70; remainder unsourced. Scholarly rescrape. |
| **fath-al-rabbani** | 3 | ur | only 1 recoverable via musnad-ahmad cross-ref; remainder UR unsourced. Scholarly rescrape. |
| **nasai-kubra** | 1 | ur | HN307 ur; alt covers all en. Scholarly rescrape. |
| **mishkat** | 1 | ur | HN1 ur; git/alt equal-or-shorter. Scholarly rescrape. |
| **qudsi** | 1 | fr | HN36 fr; all 6 sources carry identical 738-char text (genuinely short at source). Scholarly FR rescrape. |
| **sahih-ibn-khuzaymah** | 90 | en/ur | tohed covers HN≤3229; alt `en.json` is MT (excluded); high HNs not on tohed. Scholarly rescrape for high-HN remainder. |

**Biggest scholarly-rescrapable blocks by size:** bayhaqi (4,775), sunan-al-daraqutni (2,285), muajam-tabarani-saghir (1,128), muslim (1,569), mustadrak (593), musnad-ahmad (586), musannaf-ibn-abi-shaybah (466). These six account for ~10.6k of the 18,957 rescrape gap.

**Rule reaffirmed:** none of the 18,957 gaps should be filled by LLM/MT. The repo already carries AI-badged EN for `silsila-sahih` and `lulu`/`silsala` inserts via `recover_glm_en.py` / `recover_llm_en.py` / `recover_silsila_en.py`; those are explicit AI-translation tracks and must remain badged `[AI-translation]`. Scholarly recovery uses only the human-translation sources in §1.
