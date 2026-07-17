export const meta = {
  name: 'toon-recover',
  description: 'Execute FINAL_RECOVERY_PLAN — scholarly rescrape + Option-B LLM for 10 KNOWN_ISSUES data-loss items',
  phases: [
    { title: 'Recover', detail: 'one agent per item, edits only its edition files, reads real source data, writes toon rows' },
    { title: 'Verify', detail: 're-audit changed editions, parse check, confirm fix landed' },
    { title: 'Document', detail: 'update KNOWN_ISSUES + info.toon notes' },
  ],
}

const REPO='/home/saboor/code/hadith-api-toon'
const ED=`${REPO}/editions`
const NEW='/home/saboor/code/hadith-api-toon-new'
const ALT='/home/saboor/code/hadith-api-toon-alt'
const CACHE=`${REPO}/scripts/cache`
const HAPI1='/home/saboor/hadith-api-1'

const ITEM_SCHEMA = {
  type:'object', properties:{
    item_id:{type:'string'},
    files_changed:{type:'array', items:{type:'string'}},
    rows_recovered:{type:'number'},
    method:{type:'string', description:'scholarly_rescrape | llm_translation | local_rebuild'},
    source_used:{type:'string'},
    llm_rows:{type:'number', description:'how many rows are [AI-translation]-prefixed LLM output (0 for scholarly)'},
    verification:{type:'string', description:'what you checked to confirm the fix landed (grep counts, re-read, header valid)'},
    issues_remaining:{type:'string'},
  }, required:['item_id','files_changed','rows_recovered','method','verification'],
}

const RULES = `You are executing ONE recovery item in the hadith .toon repo at ${REPO}. Branch audit-fixes is checked out. Edit ONLY the files named in your item. Do NOT touch other editions, viewer.html, sunnah.js, or run git.

ABSOLUTE RULES:
- READ source files (JSON/sqlite/tohed HTML) BEFORE writing. Never fabricate hadith text.
- Scholarly items: write the REAL fetched/read text verbatim into the toon row. No prefix.
- LLM items: translate intact Arabic via openrouter, prefix EVERY LLM row "[AI-translation] " so consumers know it's machine text.
- Preserve toon CSV schema: translations = "hadithnumber","text" (2 fields); AR source = 7 fields. Escape inner double-quotes in any field as "" (CSV standard). Update hadiths[N] header count to match actual rows.
- After writing, re-Read the file to confirm the edit landed + header valid + row count matches.
- Use Bash for python scripts, sqlite3, curl, openrouter calls. Use Read/Write/Edit for toon files.

OPENROUTER (for LLM items only): keys are in ${REPO}/.env (OPENROUTER_API_KEY) AND 6 keys hardcoded in ${ALT}/adab/translate_en_batch.py. Reuse that script's pattern: POST https://openrouter.ai/api/v1/chat/completions, model "openrouter/owl-alpha" (or a stronger model if you prefer), temperature 0, batch ~10-15 hadiths per request, 6 keys rotate, 20 retries on 429/5xx. Prompt: faithful Arabic->target translation, no commentary/preface, preserve hadith register and proper-name transliteration. Prefix output "[AI-translation] ".

TOON ROW FORMAT reminder:
- translation file line: "HN","text here"   (text may contain escaped "" for quotes)
- AR source line: "HN","arabic","grades","reference","intl","chain","chapter_intro"
- header: hadiths[N]{fieldnames}:`

const ITEMS = [
  { id:'A1-ibnmajah-fr', method:'scholarly_rescrape', scope:`${RULES}

ITEM A1: ibnmajah FR — recover 7 AI-preamble hadiths from fawaz cache.
Source: ${CACHE}/fra-ibnmajah.min.json (JSON, 'hadiths' array, each {hadithnumber,text}). VERIFIED clean for HN 597,1311,1855,2271,2291,2520,4316 (no "Voici"/"Traduction").
Steps:
1. Read ${CACHE}/fra-ibnmajah.min.json, build hadithnumber->text map for the 7 HNs.
2. For each HN, find the row in ${ED}/ibnmajah/translations/fr/sections/*.toon (grep the hadithnumber), replace the text field with the fawaz clean FR. Keep hadithnumber. Use Edit or a python script with proper CSV escaping.
3. Verify: grep -rn 'Voici la traduction\\|Traduction :' ${ED}/ibnmajah/translations/fr/sections/ -> 0. Re-read 1 edited file to confirm header + row count intact.
Target files: ${ED}/ibnmajah/translations/fr/sections/*.toon (only the files containing those 7 HNs).` },

  { id:'A2-abudawud-bn', method:'scholarly_rescrape', scope:`${RULES}

ITEM A2: abudawud BN HN4588 — recover vowel-corrupted Bengali from fawaz cache.
Source: ${CACHE}/ben-abudawud.min.json (hadiths array, {hadithnumber,text}). VERIFIED scholarly Bengali.
Steps:
1. Read ${CACHE}/ben-abudawud.min.json, get text for hadithnumber 4588 (KNOWN_ISSUES noted "was 4595" — check both 4588 and 4595 in the cache; the repo row to fix is the vowel-corrupted one; match by checking which HN exists in the repo file).
2. Find the corrupt row in ${ED}/abudawud/translations/bn/sections/*.toon (grep '"4588"' and '"4595"').
3. Replace the corrupt text with fawaz clean Bengali. Keep hadithnumber.
4. Verify: re-read the file, row parses, surrounding rows untouched.
Target files: ${ED}/abudawud/translations/bn/sections/<the file with HN4588/4595>.toon` },

  { id:'A3-nasai-sec36', method:'local_rebuild', scope:`${RULES}

ITEM A3: nasai section 36 — rebuild from fawaz/hadith-api-1 caches, 6 scholarly langs + AR.
Section 36 = Book 36 "Kind Treatment of Women", 27 hadiths, HN range = the hadithnumbers where reference.book==36 (stringified dict, parse with ast.literal_eval). IND has 25 (2 missing — leave those 2 absent in id/36.toon).
Sources:
- AR: ${HAPI1}/editions/ara-nasai.min.json (book36, 27 hadiths) — OR ${CACHE}/ahmedbaset_nasai.json. Use ara-nasai.min.json from ${HAPI1}.
- EN: ${CACHE}/eng-nasai.min.json (27)
- URD: ${CACHE}/urd-nasai.min.json (27)
- BEN: ${CACHE}/ben-nasai.min.json (27)
- IND: ${CACHE}/ind-nasai.min.json (25)
- FRA: ${CACHE}/fra-nasai.min.json (27)
Steps:
1. For each source, load JSON, filter hadiths where reference.book==36 (parse stringified ref), collect (hadithnumber, text) ordered by hadithnumber.
2. Confirm the 27 HNs are contiguous and match across langs (IND will have 25). Note exact first/last HN.
3. Create ${ED}/nasai/sections/36.toon: header hadiths[27]{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}: and 27 AR rows (7-field). For fields you don't have (grades/reference/etc), use "" empty unless the cache provides them (fawaz has grades+reference — include them).
4. Create ${ED}/nasai/translations/{en,ur,bn,fr}/sections/36.toon: header hadiths[27]{hadithnumber,text}: + 27 rows. id: hadiths[25] + 25 rows (leave 2 missing; do NOT fabricate).
5. Update ${ED}/nasai/info.toon section index: add section 36 entry (currently skips 35->37). Match the index format used by other sections in that info.toon.
6. Verify: each new file parses, header count matches rows. Re-read 1 file.
NOTE: do NOT create tr/ru/ta section 36 here — that's item C2 (LLM, separate agent).
Target files: ${ED}/nasai/sections/36.toon, ${ED}/nasai/translations/{en,ur,bn,id,fr}/sections/36.toon, ${ED}/nasai/info.toon` },

  { id:'A4-shamail-ur', method:'scholarly_rescrape', scope:`${RULES}

ITEM A4: shamail-tirmidhi UR HN161 — recover from local final.json (or tohed if local corrupt).
Source: ${NEW}/shamail-tirmazi_final.json (247K, has translations). If the Urdu for HN161 there is clean (no "PARAM" loop), use it. Else fetch https://en.tohed.com/hadith/shamail-tirmidhi/161/ via curl/WebFetch and parse the Urdu hadith body.
Steps:
1. Read ${NEW}/shamail-tirmazi_final.json, find hadith 161 (sections are keyed by number; iterate to find the section whose hadiths include HN161, or the structure is per-hadith — inspect first). Extract Urdu text.
2. Find HN161 row in ${ED}/shamail-tirmidhi/translations/ur/sections/25.toon, replace the AI-self-monologue text (the "PARAM? No, I think I'm making a mistake..." loop) with the clean Urdu. Append nothing — just the clean text. (The prior fix-run may have truncated it to "[corrupt: repetition loop truncated]" — replace that marker with the real text.)
3. Verify: grep 'PARAM\\|making a mistake' ${ED}/shamail-tirmidhi/translations/ur/sections/25.toon -> 0. Re-read file, header intact.
Target files: ${ED}/shamail-tirmidhi/translations/ur/sections/25.toon` },

  { id:'A5-khuzaymah-index', method:'local_rebuild', scope:`${RULES}

ITEM A5: sahih-ibn-khuzaymah info.toon index (1059 malformed rows) + 320 chapter_intro-contaminated sections.
Source: ${NEW}/sahih_ibn_khuzaymah_final.json (3.2M, clean section metadata).
Steps:
1. Read ${NEW}/sahih_ibn_khuzaymah_final.json. Extract per-section: section number, Arabic name, hadith_first, hadith_last, arabic_first, arabic_last (inspect structure — likely keyed by section number with these fields).
2. Rebuild the section index block in ${ED}/sahih-ibn-khuzaymah/info.toon: write each section row with PROPER CSV escaping — any inner double-quote in an Arabic name becomes "" (escaped). Use a python csv writer, NEVER string concatenation. Keep the metadata: block (book_id, book_name, total_hadiths, available_languages, intro) intact — only replace the translations/sections index portion.
3. For the ~320 chapter_intro-contaminated AR sections: re-derive each section's chapter_intro from its clean Arabic name in the final.json, then overwrite the chapter_intro field (7th field) in every row of ${ED}/sahih-ibn-khuzaymah/sections/<N>.toon. Identify which sections are contaminated by: section has Urdu-script characters in its chapter_intro, OR chapter_intro != the clean name from final.json. Overwrite all such.
4. Verify: parse 5 random index rows with python csv -> each yields the declared field count. grep for Urdu-script chars in ${ED}/sahih-ibn-khuzaymah/sections/*.toon chapter_intro fields -> 0 (or only legitimate). Re-read info.toon header valid.
Target files: ${ED}/sahih-ibn-khuzaymah/info.toon + ~320 ${ED}/sahih-ibn-khuzaymah/sections/*.toon` },

  { id:'A6-silsala-en', method:'scholarly_rescrape', scope:`${RULES}

ITEM A6: silsala-sahih EN ~3182 empty rows — fill from silsila.db sqlite.
Source: ${ALT}/hadith islam360/silsila.db (sqlite, table 'hadees' 3704 rows + 'hadees_languages' per-language text). Also fallback/verify: ${NEW}/silsila_sahih_final.json (translations.en).
Steps:
1. Open silsila.db with sqlite3: schema is hadees(record_id, hadees_number, arabic, ...) + hadees_languages(id, hadees, baab, kitab, ravi, Takhreej, wazahat, language_id, hadees_id) + language(id, name). Find the English language row, JOIN to get hadees_number -> English text. Build HN->EN map.
2. Verify HN alignment: compare silsila.db HN set vs ${ED}/silsila-sahih/sections AR HN set for 5 samples. If mismatch, use ${NEW}/silsila_sahih_final.json translations.en instead (inspect its structure: sections keyed by number, each hadith has 'translations' dict with 'en').
3. For each empty EN row in ${ED}/silsila-sahih/translations/en/sections/*.toon, write the English text from the map. Keep hadithnumber. Only fill rows that are currently empty/short; do not overwrite rows that already have good text.
4. Verify: re-run count of empty_text in silsala-sahih EN -> should drop sharply (was ~3182). Re-read 2 files.
Target files: ${ED}/silsila-sahih/translations/en/sections/*.toon` },

  { id:'B1-ibnhibban-en', method:'scholarly_rescrape', scope:`${RULES}

ITEM B1: ibnhibban EN — recover 16 hadiths (JSON-LD 4 + truncated 12) from tohed.com.
HNs: 1139, 3610, 5690, 7174, 1517, 1615, 1714, 1845, 2128, 2505, 3784, 3812, 5905, 6142, 6971, 7402.
Source: https://en.tohed.com/hadith/sahih-ibn-hibban/<HN>/ — VERIFIED scholarly (Darussalam-style, Sayyiduna honorifics, academic isnads, al-Arna'ut/Albani gradings, Bawazir/Mu'assasah edition refs).
Steps:
1. For each HN (polite: 2s sleep between fetches), fetch the tohed page with curl or WebFetch. Extract the English hadith body (the rendered translation block — not page chrome). The page has a hadith-app content area with Arabic + English (+Urdu/French per hadith). Parse out the English.
2. Find the row in ${ED}/ibnhibban/translations/en/sections/*.toon (grep the HN). Replace the text field (currently JSON-LD residue or truncated fragment, or "[corrupt]" marker) with the real English. Keep hadithnumber.
3. Verify: grep -rn 'mainEntityOfPage\\|en\\.tohed\\.com' ${ED}/ibnhibban/translations/en/sections/ -> 0 (1 may remain in metadata.toon index ref — that's fine). Re-read 2 edited files.
Target files: ${ED}/ibnhibban/translations/en/sections/*.toon (the ~6-8 files containing those 16 HNs)` },

  { id:'B2-musannaf-ur', method:'scholarly_rescrape', scope:`${RULES}

ITEM B2: musannaf UR HN 5898, 22496 — recover from tohed.com (Awamah/Awais Sarwar Urdu edition, VERIFIED scholarly).
Source: https://en.tohed.com/hadith/musannaf-ibn-abi-shaybah/<HN>/ — renders Urdu.
Steps:
1. Fetch tohed pages for HN 5898 and 22496 (2s sleep). Parse the Urdu hadith body.
2. Find the rows in ${ED}/musannaf-ibn-abi-shaybah/translations/ur/sections/*.toon (grep '"5898"' and '"22496"'). Replace the "plvvlqj" gibberish text with the clean Urdu. Keep hadithnumber.
3. Verify: grep -rn 'plvvlqj' ${ED}/musannaf-ibn-abi-shaybah/translations/ur/ -> 0. Re-read files.
Target files: ${ED}/musannaf-ibn-abi-shaybah/translations/ur/sections/<the 2 files>.toon` },

  { id:'C1-lulu-en', method:'llm_translation', scope:`${RULES}

ITEM C1: lulu-wal-marjan EN — LLM-translate 281 missing hadiths from intact Arabic. OPTION B.
AR source intact: ${ED}/lulu-wal-marjan/sections/*.toon has 1906 hadiths, all arabic nonempty.
Missing EN HNs (VERIFIED, 281): compute at runtime as (AR HN set) minus (EN HN set in ${ED}/lulu-wal-marjan/translations/en/sections/*.toon). Expected gap = 281; sample first/last: 2,9,11,12,15,21,27,35,36,46,52,53,56,60,64,69,79,95,100,102,...,1871,1881,1885,1886,1887,1890,1894,1896,1901,1903.
Steps:
1. Build AR HN->arabic map from ${ED}/lulu-wal-marjan/sections/*.toon (read each row, hadithnumber + arabic field).
2. Build EN existing HN set from ${ED}/lulu-wal-marjan/translations/en/sections/*.toon.
3. missing = AR - EN. Confirm len ~281.
4. Write a python script that: for each missing HN, takes its Arabic, batches ~10-15, calls openrouter (keys from ${REPO}/.env OPENROUTER_API_KEY, or the 6 keys in ${ALT}/adab/translate_en_batch.py; model openrouter/owl-alpha or stronger; temperature 0; 20 retries on 429), translates AR->EN faithfully (prompt: faithful hadith translation, no commentary/preface, preserve proper-name transliteration). Prefix every result "[AI-translation] ". 6 keys rotate, 6 workers.
5. Write each translated EN text into the missing HN row in ${ED}/lulu-wal-marjan/translations/en/sections/<N>.toon. If the row is merged/OCR-garbage, create a clean separate row for that HN (split merges so each HN has its own row, ordered by hadithnumber). Update each file's hadiths[N] header count to actual rows.
6. Add a note to ${ED}/lulu-wal-marjan/info.toon: EN translation is AI-translated for 281 hadiths (Option B), prefixed [AI-translation], pending scholarly replacement.
7. Verify: EN HN count rises from 1625 to ~1906. grep '[AI-translation]' count in lulu EN -> ~281. Re-read 2 files. headers valid.
Target files: ${ED}/lulu-wal-marjan/translations/en/sections/*.toon (the ~55 files) + ${ED}/lulu-wal-marjan/info.toon` },

  { id:'C2-nasai-tr-ru-ta', method:'llm_translation', scope:`${RULES}

ITEM C2: nasai section 36 TUR/RUS/TAM — LLM-translate 27 hadiths each from intact Arabic. OPTION B. (Item A3 creates AR/en/ur/bn/id/fr sec36; you create tr/ru/ta sec36.)
AR source for book36 = 27 hadiths from ${HAPI1}/editions/ara-nasai.min.json (filter reference.book==36). Or read ${ED}/nasai/sections/36.toon AFTER item A3 has run — but A3 runs in parallel; to be safe, read AR directly from ${HAPI1}/editions/ara-nasai.min.json.
Target languages: Turkish (tr), Russian (ru), Tamil (ta) — verify actual repo lang dir names under ${ED}/nasai/translations/ (likely tr, ru, ta; confirm with ls).
Steps:
1. Load ${HAPI1}/editions/ara-nasai.min.json, filter reference.book==36 (parse stringified ref), collect 27 (hadithnumber, arabic) ordered.
2. For each of tr/ru/ta: write a python script: batch ~10-15 Arabic hadiths, openrouter (keys from ${REPO}/.env + ${ALT}/adab/translate_en_batch.py 6 keys; model openrouter/owl-alpha or stronger; temperature 0; 20 retries; 6 workers; rotate keys). Prompt: faithful Arabic->target translation, use that language's Islamic register (Turkish "Peygamber (s.a.v.)", Russian "Пророк (ﷺ)", Tamil "நபி (ﷺ)"), no commentary/preface, preserve proper names. Prefix every result "[AI-translation] ".
3. Create ${ED}/nasai/translations/{tr,ru,ta}/sections/36.toon: header hadiths[27]{hadithnumber,text}: + 27 rows each prefixed [AI-translation] .
4. If a tr/ru/ta sections dir doesn't exist under ${ED}/nasai/translations/, create it.
5. Add note to ${ED}/nasai/info.toon: section 36 tr/ru/ta are AI-translated (Option B, [AI-translation]).
6. Verify: 3 new files exist, each 27 rows, all prefixed [AI-translation]. headers valid. Re-read 1 file.
Target files: ${ED}/nasai/translations/{tr,ru,ta}/sections/36.toon (new) + ${ED}/nasai/info.toon` },
]

phase('Recover')
log(`Recovering ${ITEMS.length} items`)

async function retry(p,o,t=5){ for(let i=1;i<=t;i++){ const r=await agent(p,o); if(r) return r; log(`retry ${i}/${t} ${o.label}`);} return null }

const results=[]
const BATCH=3
for(let i=0;i<ITEMS.length;i+=BATCH){
  const b=ITEMS.slice(i,i+BATCH)
  log(`Recover batch ${Math.floor(i/BATCH)+1}: ${b.map(x=>x.id).join(', ')}`)
  const out=await parallel(b.map(it=>()=>retry(it.scope, {label:`rec:${it.id}`, phase:'Recover', schema:ITEM_SCHEMA, effort:'high'})))
  for(const o of out) if(o) results.push(o)
  log(`Recover cumulative: ${results.length}/${ITEMS.length}`)
}

phase('Verify')
const changedEditions=[...new Set(results.flatMap(r=>(r.files_changed||[]).map(f=>f.split('/')[1]||f)))]
const verify=await agent(`You are verifying the recovery run. Re-audit the changed editions to confirm fixes landed and no new breakage. Run: cd ${REPO} && python3 toon_audit.py 2>/dev/null | tail -30. Also check:
- grep -rn 'Voici la traduction\\|Traduction :' ${ED}/ibnmajah/translations/fr/sections/ -> 0
- grep -rn 'mainEntityOfPage\\|en\\.tohed' ${ED}/ibnhibban/translations/en/sections/ -> 0
- grep -rn 'plvvlqj' ${ED}/musannaf-ibn-abi-shaybah/ -> 0
- grep -rln 'hadiths\\[count\\]' ${ED} -> 0 (none introduced)
- ls ${ED}/nasai/sections/36.toon ${ED}/nasai/translations/{en,ur,bn,id,fr,ta,ru}/sections/36.toon 2>/dev/null
- count of [AI-translation] in lulu EN + nasai tr/ru/ta
- regression: for every changed .toon, head -1 still matches hadiths[N]{...} and file non-empty
Run these via Bash. Report what passed, what failed, and any new breakage. Return {summary, passed:[], failed:[], new_breakage:[]}.`,
  {label:'verify-recovery', phase:'Verify', schema:{type:'object', properties:{summary:{type:'string'},passed:{type:'array',items:{type:'string'}},failed:{type:'array',items:{type:'string'}},new_breakage:{type:'array',items:{type:'string'}}}, required:['summary','passed','failed']}, effort:'high'})

phase('Document')
const doc=await agent(`Update documentation after recovery. Repo: ${REPO}.
Recovery results (JSON): ${JSON.stringify(results,null,0)}
Verify results: ${JSON.stringify(verify,null,0)}

Tasks:
1. Update ${REPO}/KNOWN_ISSUES.md: for the 9 scholarly-recovered items, mark RESOLVED with source. For lulu EN + nasai sec36 tr/ru/ta (LLM Option B), mark "resolved-via-LLM (Option B) [AI-translation]" with the note that scholarly replacement is welcome. Keep the header/structure.
2. Read the current KNOWN_ISSUES.md first, then Edit it (do not rewrite wholesale — preserve resolved items' context).
Return {known_issues_updated: true, summary: "<short markdown of what was recovered + what remains>"}.
Do NOT run git.`,
  {label:'document', phase:'Document', schema:{type:'object', properties:{known_issues_updated:{type:'boolean'}, summary:{type:'string'}}, required:['summary']}, effort:'high'})

return { items_recovered: results.length, results, verify, doc_summary: doc && doc.summary }
