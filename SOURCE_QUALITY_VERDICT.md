## Quality Verification — Source Recovery Plan (Update)

Verification sampled real fetched text from each proposed recovery source and graded it against scholarly-translation hallmarks (formal hadith register, correct sahabi/tabi'i honorifics, academic transliteration with ayn-backticks, full isnad in arrow notation, preserved scholarly grade apparatus in Arabic, musannif commentary, edition cross-references) versus AI/machine-slop markers (`Here is`, `Translation:`, `Sure`, `[AI]`, `Note:` meta-commentary, garbled names, generic over-fluent prose).

### 1. Per-source quality verdict table

| Source | Verdict | Evidence (abbreviated) | Action |
|---|---|---|---|
| **en.tohed.com — Sahih Ibn Hibban English** (HN 1139, 3610, 5690, 7174, 1517) | **scholarly** | `Sayyiduna` + `(may Allah be pleased with them both)` + `(peace and blessings be upon him)` applied consistently; proper transliteration (Bishr bin Mu'adh al-Aqdi, Yazid bin Zurai', Rawh bin al-Qasim, Shu'ayb al-Arna'ut, Abu Umamah bin Sahl bin Hunaif); full isnad in arrow notation; both al-Albani and Shu'ayb al-Arna'ut gradings quoted in Arabic (`إسناده قوي`, `إسناده صحيح`, `صحيح على شرطهما`, `saduq`); Bawazir/Bazawir + Mu'assasah printed-edition cross-refs; Ibn Hibban's own musannif glosses preserved (the `Do not get angry` anger-is-human-nature gloss, the supplementary chain via Amr bin Yahya Mazni). **Zero AI markers.** | **KEEP / USE as replacement source** |
| **tohed.com — Urdu Musannaf Ibn Abi Shaybah, Awamah ed.** (Maulana Muhammad Awais Sarwar; HN 5898, 22496) | **scholarly** | Formal academic Urdu register; correct sahabi vs tabi'i honorific distinction (`رضی اللہ عنہما` for Ibn Umar, `رحمہ اللہ` for Shurayh — a precise distinction a machine translator would likely miss/over-apply); full takhreej (al-Shathri + Awamah numberings); saheeh grading by Sa'd bin Nasir al-Shathri; textual-variant footnote (`(١) في [ز]: (فاستعمله)`). No `[AI]`, no `Translation:` preface, no meta-commentary. | **KEEP / USE as replacement source** |
| **fawaz/eng-nasai.min.json** (section 36, HN 3939–3965) | **scholarly** | Darussalam Sunan an-Nasa'i English (Nasiruddin al-Khattab): `It was narrated from X that the Prophet/Messenger of Allah said:` formula; Tharid simile (3947); two-wives `half his body leaning` (3942); grade block naming Abu Ghuddah + Al-Albani + Zubair Ali Zai — the Darussalam English Nasai signature. `Here is` substring hit is in-narration (`there he was`), not a meta-marker. | **KEEP / USE** |
| **fawaz/ara-nasai — ahmedbaset_nasai.json** (ch36, idInBook 3949/3952/3956) | **scholarly** | Full classical Arabic with tashkeel and complete isnad chains (`حَدَّثَنِي`/`أَخْبَرَنَا` + named narrators); continuous classical hadith prose; matches the printed Sunan an-Nasa'i Arabic. Used as the Arabic anchor for translation verification. | **KEEP / USE (Arabic anchor)** |
| **fawaz/fra-nasai.min.json** (section 36) | **likely_scholarly** | `Rapporté par X : Le Messager d'Allah a dit :` register; ayn-backtick transliteration (`'Aishah`, Jibril); parallel to the Darussalam English (same selection, same content); the only `Voici` hit is in-narration (`voici Jibril` = `this is Jibril` = correct render of `hādhā Jibrīl`), not an AI preface. | **KEEP / USE (note: likely scholarly)** |
| **fawaz/urd-nasai.min.json** (section 36) | **scholarly** | `X رضی الله عنہ کہتے ہیں کہ ... فرمایا` formula; `صلی اللہ علیہ وسلم` / `رضی الله عنہ` / `رضی الله عنہا` honorifics; `۱؎` footnote dagger; matches the Darussalam/Idarat Turjuman Sunan an-Nasa'i Urdu. | **KEEP / USE** |
| **fawaz/ben-nasai.min.json** (section 36) | **scholarly** | `X (রহঃ) ... Y (রাঃ) থেকে বর্ণিত` isnad form with preserved sub-narrator names (Imam Abdur Rahman an-Nasa'i, Amr ibn Ali, Ismail ibn Mas'ud — chains a machine translator would drop); full salawat; `১অ`/`১এ` dagger footnotes; Tawheed Publications Bengali signature. | **KEEP / USE** |
| **fawaz/ind-nasai.min.json** (section 36) | **scholarly** | `Telah mengabarkan kepada kami [X] telah menceritakan kepada kami [Y]` bracketed-narrator form; `shallallahu alaihi wasallam`; 25/27 section-36 hadiths populated; matches English/Arabic parallels; Darussalam Indonesia/IAIN signature. | **KEEP / USE** |
| **fawaz/tur-nasai.min.json** (section 36) | **mixed** | Form is scholarly where present (`Ebû Mûsâ`, `radıyallahü anh`, `sallallahü aleyhi ve sellem` — Kütüb-i Sitte/Diyanet style) **but section 36 is 100% EMPTY (0/27 rows)**; only 629/5765 nonempty globally. Cannot rebuild section 36 from Turkish. | **DO NOT USE for section 36** (safe only where text is actually present) |
| **fawaz/rus-nasai.min.json** | **unclear** | **FILE MISSING** — no Russian Nasai file in the fawaz cache (only rus-abudawud, rus-bukhari, rus-muslim exist). | **Needs a different scholarly source or LLM fallback** |
| **fawaz/tam-nasai.min.json** | **unclear** | **FILE MISSING** — no Tamil Nasai file in the fawaz cache (only tam-bukhari, tam-muslim exist). | **Needs a different scholarly source or LLM fallback** |
| **fawaz/fra-ibnmajah.min.json** (HN 597, 1311, 4316) | **scholarly** | `Rapporté par X : Le Messager d'Allah a dit` register; ayn-backtick (`'Abdullah ibn Abi Jad'a'`, Ibn `Abbas, Banu Tamim); (ﷺ) glyph; full Albani / Muhammad Fouad Abd al-Baqi / Shuaib Al Arnaut / Zubair Ali Zai grade block; matches the hadithenc.com French Ibn Majah edition. No AI prefaces. | **KEEP / USE** |
| **fawaz/ben-abudawud.min.json** (HN 4586–4590) | **scholarly** | Islamic Bengali academic register; full salawat `সাল্লাল্লাহু আলাইহি ওয়াসাল্লাম`; isnad connectors `সূত্রে বর্ণিত` / `থেকে পর্যায়ক্রমে তার পিতা এবং তার দাদার সূত্রে`; narrator honorifics (রাঃ)/(রহঃ); footnote markers; full grade apparatus; HN 4588 renders the Farewell-Sermon conquest-of-Makkah khutbah in classical Bengali Islamic phrasing. No AI artifacts. | **KEEP / USE** |

### 2. tohed.com English / Ibn Hibban — scholarly or machine?

**Scholarly — human translation, not machine/AI slop.** Five sampled hadiths (1139, 3610, 5690, 7174, 1517) show uniform hallmarks that machine translation cannot consistently produce and AI slop never produces:

- **Formal hadith register applied consistently across all five:** `Sayyiduna` before every Companion, `(may Allah be pleased with him/them both)` and `(peace and blessings be upon him)` after the Prophet — applied uniformly, not sporadically as an AI would.
- **Correct academic transliteration with ayn-backticks and accurate classical-narrator names:** Bishr bin Mu'adh al-Aqdi, Yazid bin Zurai', Rawh bin al-Qasim, Abu Khaithamah, Shu'ayb al-Arna'ut, Abu Umamah bin Sahl bin Hunaif, Amr bin Yahya Mazni — no garbled names.
- **Full isnads in academic arrow notation** (`←` chains), preserved verbatim.
- **Genuine scholarly apparatus preserved:** both al-Albani and Shu'ayb al-Arna'ut gradings quoted in Arabic (`إسناده قوي`, `إسناده صحيح`, `صحيح على شرطهما`, `saduq`), plus Bawazir/Bazawir and Mu'assasah printed-edition cross-references and Bukhari/Muslim parallel citations.
- **Ibn Hibban's own musannif commentary preserved** — the `Do not get angry` gloss (anger is human nature; the prohibition is on consequent forbidden actions, not the emotion), and the supplementary chain via Amr bin Yahya Mazni of Banu Najjar. This is real editorial commentary from the musannif, rendered in academic English — not something machine translation preserves.
- **Zero AI markers anywhere:** no `Here is`, `Translation:`, `Sure`, `I apologize`, `[AI]`, `Note:` meta-commentary, no awkward literal renderings, no generic over-fluent prose.

The style is internally consistent across all five and matches the Darussalam-style English Sahih Ibn Hibban edition (the `Sayyiduna` + honorific convention and the Bawazir/Mu'assasah edition cross-references are characteristic of that edition's scholarly apparatus). This is a safe, trustworthy source — **in stark contrast to hadithunlocked.com's Google/machine-translated `[AI]`-prefixed rows**, which is the known-bad contrast the repo refuses. The tohed.com Ibn Hibban English rows are safe to use as replacements for corrupt data.

### 3. Local nasai caches — per-language verdict (section 36, HN 3939–3965)

| Language | Cache file | Verdict | Section-36 coverage |
|---|---|---|---|
| Arabic | `ahmedbaset_nasai.json` | **scholarly** (classical isnad + tashkeel) | full (anchor source) |
| English | `eng-nasai.min.json` | **scholarly** (Darussalam / Nasiruddin al-Khattab) | full |
| French | `fra-nasai.min.json` | **likely_scholarly** (Darussalam-parallel; in-narration `voici` only) | full |
| Urdu | `urd-nasai.min.json` | **scholarly** (Darussalam / Idarat Turjuman) | full |
| Bengali | `ben-nasai.min.json` | **scholarly** (Darussalam / Tawheed Publications) | full |
| Indonesian | `ind-nasai.min.json` | **scholarly** (Darussalam Indonesia / IAIN) | 25/27 populated |
| Turkish | `tur-nasai.min.json` | **mixed** — form scholarly, but **section 36 = 0/27 EMPTY** | **empty** |
| Russian | `rus-nasai.min.json` | **unclear** — **FILE MISSING** | none |
| Tamil | `tam-nasai.min.json` | **unclear** — **FILE MISSING** | none |

Scholarly: Arabic, English, Urdu, Bengali, Indonesian. Likely-scholarly: French. Machine/AI slop: **none detected.** Unusable-for-section-36: Turkish (empty). Missing entirely: Russian, Tamil. **No nasai cache carries machine/AI slop** — the only failures are absence (Turkish emptiness; Russian/Tamil file-missing), not contamination.

### 4. Confirmed-safe vs. LLM-fallback vs. different-source-needed

**CONFIRMED SAFE TO USE (human scholarly translations):**
- en.tohed.com — Sahih Ibn Hibban English
- tohed.com — Urdu Musannaf Ibn Abi Shaybah (Awamah / Maulana Muhammad Awais Sarwar)
- fawaz/ara-nasai (ahmedbaset_nasai.json)
- fawaz/eng-nasai.min.json
- fawaz/urd-nasai.min.json
- fawaz/ben-nasai.min.json
- fawaz/ind-nasai.min.json
- fawaz/fra-nasai.min.json (safe with "likely scholarly" note — only in-narration `voici` hits, no meta-markers)
- fawaz/fra-ibnmajah.min.json
- fawaz/ben-abudawud.min.json

**NEED A DIFFERENT SCHOLARLY SOURCE (no cache / empty cache — do NOT use LLM yet):**
- fawaz/tur-nasai section 36 — scholarly form but 0/27 rows; find another Turkish Nasai scholarly source (e.g. Diyanet / Kütüb-i Sitte full edition) before falling back to LLM.
- fawaz/rus-nasai — file missing; find a Russian Nasai scholarly source before LLM.
- fawaz/tam-nasai — file missing; find a Tamil Nasai scholarly source before LLM.

**NEED LLM FALLBACK (only if no scholarly source exists for that lang/collection):**
- tur-nasai section 36 — only after exhausting scholarly-source search; the form is provably scholarly elsewhere, so LLM output should be checked against the Arabic anchor (ahmedbaset) and the English Darussalam to catch drift.
- rus-nasai / tam-nasai — LLM fallback acceptable only if no scholarly Russian/Tamil Nasai edition can be sourced; gate each LLM row on the Arabic anchor + known-reference match.

### 5. Updated recovery-plan recommendation

**tohed.com Ibn Hibban English is confirmed scholarly — use it directly.** The original concern (is tohed EN machine-translated, forcing an LLM fallback for Ibn Hibban EN?) is resolved: tohed EN is human scholarly Darussalam-style work, not machine slop. No LLM is needed for Ibn Hibban English.

**Ibn Hibban EN sourcing tradeoff — honest note:** sunnah.com / Darussalam's public API does **not** list Sahih Ibn Hibban in English, so tohed.com is currently the only confirmed-scholarly Ibn Hibban EN source in play. This is a single-source dependency for Ibn Hibban EN. Mitigation: (a) keep using tohed EN (it is verified scholarly); (b) cross-check any tohad EN row against the Arabic (ahmedbaset where available, or the edition cross-refs tohed itself cites — Bawazir/Mu'assasah numbers) before accepting; (c) for any Ibn Hibban EN row that fails cross-check or is missing on tohed, leave it **documented-missing** rather than LLM-generate, because there is no second scholarly EN Ibn Hibban source to validate LLM output against. LLM-generating Ibn Hibban EN with no scholarly anchor to verify against would reproduce exactly the `[AI]`-prefixed-slop problem the repo already rejects in hadithunlocked.

**For section-36 Nasai rebuild:** use ara (anchor) + eng + urd + ben + ind + fra. Do **not** use tur (empty). For rus/tam, source a scholarly edition first; fall back to LLM only as last resort, gated on the Arabic anchor + English Darussalam.

**For fra-ibnmajah and ben-abudawud fills:** both confirmed scholarly — use directly.

**Bottom line:** Of every proposed recovery source, none carries machine/AI slop. The only blockers are *absence* (Turkish section-36 emptiness; Russian/Tamil file-missing), not *contamination*. Prioritize finding scholarly sources for the three absent cases before any LLM fallback; never LLM-generate Ibn Hibban EN without a second scholarly anchor to validate against.
