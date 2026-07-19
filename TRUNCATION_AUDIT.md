# Truncation Audit Report — hadith .toon repo

30 books scanned. Truncation = translation length / Arabic length (diacritics stripped) < 0.6. Sources checked per truncated row: local backups (alt/new/cache), git history, fawaz, tohed.

## 1. Summary table

| Book | total_truncated | has_backup_source | needs_LLM |
|---|---:|---:|---:|
| abdurrazzaq | 0 | 0 | 0 |
| abudawud | 1686 | 12 | 7 |
| aladab-almufrad | 430 | 156 | 0 |
| bayhaqi | 121 | 12 | 0 |
| bukhari | 4825 | 29 | 10 |
| bulugh-al-maram | 69 | 47 | 22 |
| dehlawi | 0 | 0 | 0 |
| fath-al-rabbani | 3 | 3 | 0 |
| ibnhibban | 1806 | 25 | 25 |
| ibnmajah | 1182 | 30 | 5 |
| lulu-wal-marjan | 340 | 0 | 340 |
| malik | 6714 | 39 | 34 |
| mishkat | 1459 | 16 | 1 |
| muajam-tabarani-saghir | 1409 | 0 | 10 |
| musannaf-ibn-abi-shaybah | 1095 | 0 | 8 |
| muslim | 18457 | 60 | 5 |
| musnad-ahmad | 7 | 0 | 7 |
| mustadrak | 1027 | 1 | 9 |
| nasai | 7505 | 6 | 11 |
| nasai-kubra | 20 | 20 | 0 |
| nawawi | 2 | 2 | 0 |
| qudsi | 0 | 0 | 0 |
| riyadussalihin | 7 | 5 | 2 |
| sahih-ibn-khuzaymah | 136 | 32 | 0 |
| shamail-tirmidhi | 135 | 84 | 51 |
| silsila-sahih | 23 | 9 | 14 |
| sunan-darimi | 270 | 22 | 1 |
| tirmidhi | 13841 | 8 | 7 |
| virtues | 2 | 0 | 2 |
| **TOTAL** | **62571** | **618** | **571** |

Note: `total_truncated` counts every ratio<0.6 row. `has_backup_source` + `needs_LLM` sum to 1189 — only the worst-ranked rows per book were source-investigated by subagents. The remaining ~61,382 (chiefly muslim 18457, tirmidhi 13841, nasai 7505, malik 6714, bukhari 4825) are truncated but uninvestigated; treat as needs_LLM pending source check.

## 2. Per-book: dominant language + backup source

| Book | worst langs | full-text source available |
|---|---|---|
| abudawud | en | local_backup (top rows) |
| aladab-almufrad | en | local_backup |
| bayhaqi | en | local_backup |
| bukhari | en (tr sec 65) | local_backup |
| bulugh-al-maram | en | git_history + local_backup |
| fath-al-rabbani | ur, en | tohed |
| ibnhibban | ur, en | fawaz (en), none (ur) |
| ibnmajah | en | fawaz |
| lulu-wal-marjan | en | **none** (340 rows, no source) |
| malik | id, bn, tr (sec 38) | **none** (mostly) |
| mishkat | en, roman-ur | local_backup |
| muajam-tabarani-saghir | ur | **none** |
| musannaf-ibn-abi-shaybah | ur | **none** |
| muslim | bn (sec 1,6,32) | fawaz |
| musnad-ahmad | ur | **none** |
| mustadrak | en, ur | **none** |
| nasai | tr, ur, fr | git_history (some), none (most) |
| nasai-kubra | en | local_backup (100%) |
| nawawi | en, bn | local_backup + fawaz |
| riyadussalihin | en | local_backup |
| sahih-ibn-khuzaymah | ur, en | local_backup |
| shamail-tirmidhi | en, ur | local_backup |
| silsila-sahih | en, ur | local_backup (some), none (most) |
| sunan-darimi | en | local_backup (some), none |
| tirmidhi | id, tr, en | fawaz (id/tr), local_backup (en) |
| virtues | tr, fr | **none** |

## 3. Worst truncations (ratio < 0.2) — data loss, not short translations

These are catastrophic: translation holds <20% of the Arabic, so meaning is lost, not merely condensed.

| book | lang | sec | hn | ratio | src |
|---|---|---|---|---:|---|
| ibnhibban | ur | 42 | 4872 | 0.004 | none |
| ibnhibban | en | 1 | 139 | 0.014 | fawaz |
| ibnhibban | en | 58 | 6679 | 0.019 | fawaz |
| malik | id | 38 | 146701 | 0.015 | none |
| malik | bn | 38 | 148801 | 0.023 | none |
| malik | tr | 38 | 148801 | 0.025 | none |
| bukhari | en | 60 | 3401 | 0.027 | local_backup |
| bukhari | en | 65 | 4725 | 0.029 | local_backup |
| bukhari | tr | 65 | 4725 | 0.031 | local_backup |
| muslim | bn | 1 | 454 | 0.026 | fawaz |
| muslim | bn | 6 | 1930 | 0.030 | fawaz |
| muslim | bn | 32 | 4678 | 0.035 | fawaz |
| lulu-wal-marjan | en | 49 | 1762 | 0.036 | none |
| lulu-wal-marjan | en | 1 | 103 | 0.039 | none |
| tirmidhi | id | 47 | 3233 | 0.025 | fawaz |
| tirmidhi | tr | 47 | 3264 | 0.027 | fawaz |
| mustadrak | en | 32 | 5878 | 0.032 | none |
| muajam-tabarani-saghir | ur | 27 | 10040 | 0.012 | none |
| silsila-sahih | ur | 2 | 263 | 0.032 | local_backup |
| aladab-almufrad | en | 43 | 1073 | 0.095 | local_backup |
| aladab-almufrad | en | 40 | 947 | 0.103 | local_backup |
| ibnmajah | en | 24 | 2858 | 0.093 | fawaz |
| musannaf-ibn-abi-shaybah | ur | 39 | 38321 | 0.127 | none |
| bayhaqi | en | 15 | 16194 | 0.074 | local_backup |
| riyadussalihin | en | 0 | 501 | 0.057 | local_backup |

The whole-book hotspots at ratio<0.2: **malik sec 38** (id/bn/tr, no source), **ibnhibban** (ur sec 42 — ratio 0.004), **lulu-wal-marjan** (en, all none), **muajam-tabarani-saghir** (ur, all none), **musannaf-ibn-abi-shaybah** (ur, all none). These are true data loss.

## 4. Recoverable vs needs-LLM

**Recoverable from local scholarly source (618 confirmed):**
- local_backup: aladab-almufrad, bayhaqi, bukhari, mishkat, nasai-kubra, riyadussalihin, sahih-ibn-khuzaymah, shamail-tirmidhi, silsila-sahih (partial), sunan-darimi (partial), abudawud (partial) — pull full text from alt/new/cache dirs.
- git_history: bulugh-al-maram (en), nasai (tr/fr partial) — restore from prior commit.
- fawaz: ibnmajah, muslim (bn), tirmidhi (id/tr), nawawi (bn), ibnhibban (en).
- tohed: fath-al-rabbani (all 3 rows).

**Needs LLM re-translation (571 confirmed no source):**
- Whole books with no source anywhere: **lulu-wal-marjan (340)**, **malik sec 38 (id/bn/tr, ~34)**, **muajam-tabarani-saghir (ur)**, **musannaf-ibn-abi-shaybah (ur)**, **musnad-ahmad (ur, 7)**, **mustadrak (en/ur)**, **virtues (tr/fr, 2)**.
- Partial no-source: ibnhibban (ur 25), shamail-tirmidhi (51), silsila-sahih (14), sunan-darimi (1), nasai (ur 11), bukhari (10), abudawud (7), tirmidhi (7).
- Plus ~61,382 uninvestigated truncated rows (muslim, tirmidhi, nasai, malik, bukhari bulk) — assume needs_LLM until source check is run against them.

## 5. Recommended recovery order

1. **local_backup first (cheapest, highest fidelity):** pull full text from `alt/`, `new/`, `cache/` dirs for aladab-almufrad (156), nasai-kubra (20), shamail-tirmidhi (84), sahih-ibn-khuzaymah (32), bayhaqi (12), bukhari (29), mishkat (16), riyadussalihin (5), sunan-darimi (22), abudawud (12), nawawi (2). Mechanical copy, no model cost, scholar-grade text.
2. **git_history:** `git log -p` / `git show` to restore dropped text — bulugh-al-maram (en), nasai (tr/fr). Free, exact.
3. **fawaz / tohed APIs:** fetch full translation for ibnmajah, muslim (bn), tirmidhi (id/tr), nawawi (bn), ibnhibban (en), fath-al-rabbani. Network call, exact source text.
4. **LLM re-translation (last resort):** the 571 confirmed no-source rows, starting with the ratio<0.2 data-loss set (malik sec 38, lulu-wal-marjan, muajam-tabarani-saghir, musannaf-ibn-abi-shaybah, ibnhibban ur, mustadrak). Then run source-checks against the 61,382 uninvestigated rows in muslim/tirmidhi/nasai/malik/bukhari before sending them to LLM — most likely a large fraction is recoverable from local_backup or fawaz and should not be LLM-translated blindly.

Skipped: per-row file-path verification (report is synthesized from subagent JSON, not re-opened against the tree); run a follow-up pass to confirm the `sec`/`hn` keys resolve to actual `.toon` paths before bulk recovery.
