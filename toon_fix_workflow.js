export const meta = {
  name: 'toon-fix',
  description: 'Apply audit fixes per-edition: mechanical scripts + judgment agents, write KNOWN_ISSUES, verify',
  phases: [
    { title: 'Fix', detail: 'one fixer per edition applies mechanical+judgment fixes, writes per-edition KNOWN_ISSUES' },
    { title: 'Verify', detail: 're-read changed files, confirm fixes applied + no new breakage' },
    { title: 'Synthesize', detail: 'merge per-edition KNOWN_ISSUES + summary of what changed' },
  ],
}

const REPO = '/home/saboor/code/hadith-api-toon'
const EDITIONS_DIR = `${REPO}/editions`

const EDITIONS = [
  'abdurrazzaq','abudawud','aladab-almufrad','bayhaqi','bukhari','bulugh-al-maram',
  'dehlawi','fath-al-rabbani','ibnhibban','ibnmajah','lulu-wal-marjan',
  'malik','mishkat','muajam-tabarani-saghir','musannaf-ibn-abi-shaybah','muslim',
  'musnad-ahmad','mustadrak','nasai','nasai-kubra','nawawi','qudsi','riyadussalihin',
  'sahih-ibn-khuzaymah','shamail-tirmidhi','silsila-sahih','sunan-al-daraqutni',
  'sunan-darimi','tirmidhi','virtues'
]

// Per-edition known issues (from audit) to guide the fixer.
const AUDIT_NOTES = {
  'ibnmajah': 'fr: strip "Voici la traduction"/"Traduction:" AI preambles (32 sections). bidi marks in 10 files. intro_hi/intro_ur may be corrupt.',
  'muslim': 'tr: 49 synthetic "Hadith <name>:\\n Rüya:" rows in sections 1/15/32 — DELETE + renumber. bn: নarrated mojibake. cross-section dup legit. tr sec0 2 merged rows.',
  'shamail-tirmidhi': 'ur/25 HN161: AI self-monologue loop "PARAM? No, I think I\'m making a mistake…" — truncate to first clean sentence + [corrupt].',
  'tirmidhi': 'info.toon intro_hi: "छह में से" looped 384× — truncate loop keep first. roman-ur AI preambles. sec20/21 NOT swapped (that\'s mishkat).',
  'nasai': 'info.toon intro_ur: "پالیسٹائن سے" looped 134× — truncate. section 36 MISSING entirely (AR+8 langs) — DO NOT fabricate, document. bn leading ordinals.',
  'musnad-ahmad': 'sec19: HN 1740 → 22865 cliff (~21k missing) — DO NOT renumber, document as known-incomplete. bidi in 1 file. 60 cross-section dups mostly legit.',
  'sahih-ibn-khuzaymah': 'info.toon: 1059/1073 index rows malformed (embedded unescaped " in Arabic names) — RE-QUOTE: escape inner " to "". 420 cross-section dups legit.',
  'malik': '5-digit hadith numbers (14601 etc) across 1797 rows ×7 langs — DO NOT renumber (book-relative scheme), document. section 50-55 gap — document. leading "রেওয়ায়ত N." strip.',
  'ibnhibban': 'en: 6 rows with JSON-LD scrape (mainEntityOfPage/en.tohed) — DELETE rows, mark HN missing. 4 truncated EN rows — mark missing. 162 cross-section dups legit.',
  'lulu-wal-marjan': 'en: 281 merged/dropped hadiths, OCR garbage — DO NOT guess-split, document as known-bad. metadata claims 1906, en has 1625.',
  'mishkat': 'translation sections 20/21 SWAPPED vs AR (AR sec20=Foods, EN sec20=Hunting) — SWAP file contents back in ALL langs, verify AR parity. sec0 intentional gap.',
  'abdurrazzaq': 'chapter_intro off-by-one: sec2 carries sec1 name, etc, all 31 files — re-derive from info.toon section index, overwrite chapter_intro in every row.',
  'aladab-almufrad': 'EN whole tree corrupted: literal \\n, \\The/\\I asked backslash-escapes, trailing """""" — unescape \\, collapse """"""→"", truncate runaway loops (row548 "and two good deeds"×733). info_lang lists ar no dir.',
  'qudsi': 'bn/te/ta cross-script contamination (Korean Hangul in Tamil, Russian+Devanagari in Bengali) — strip obvious foreign-script runs or flag. 5 langs unsampled.',
  'abudawud': 'bn rows with raw English "narrator chain:"/"hadith body:" labels (sec 3,5,41,42) — DELETE labeled rows, renumber, verify AR parity. bn/41 row4595 vowel corruption. bidi in 2 files. info_lang lists ar no dir.',
  'muajam-tabarani-saghir': 'AR grades field contains Urdu in 25 rows — relocate to narrator_chain or empty. 18301/18326 rows empty grades+ref+chain (acceptable, leave as "").',
  'musannaf-ibn-abi-shaybah': 'AR: 281 rows with literal ?? mid-word — "?? " between names → "، "; mid-word ?? → [corrupt]. EN: 73 ?? rows. ur: "plvvlqj" gibberish (HN5898,22496) — flag. grades "No Data Available" 7272 rows → empty.',
  'bayhaqi': 'ur/10 HN10342: infinite "ہم کو" repetition — truncate loop. 1 cross-section dup legit.',
  'fath-al-rabbani': 'en/2: HN142&152 massive internal repetition, HN150 missing as row (mangled onto 149) — truncate loops, document HN150.',
  'sunan-al-daraqutni': 'ASCII ? corrupting Arabic/Urdu in chapter_intro sec3/11/15/28 — partial. grade "[مرسل صحيح" stray bracket → strip. trailing scraping residue.',
  'bukhari': 'ALL 97 AR + 5 tr files: hadiths[count] header → recompute real row count, write hadiths[N]. total 7563 vs actual 7277 — document. non-numeric HN "1132b" etc = Bukhari repeat-variant coding, INTENTIONAL, leave. tr sec0 2 merged rows. en/fr backtick `Urwa transliteration NOT markdown — do not strip.',
  'mustadrak': 'AR: ~4530 rows with stray literal "n" / "ن " between Arabic words (newline stripped to n) — strip context-gated (n surrounded by Arabic on both sides, not forming a word).',
  'nawawi': 'info.toon intro truncated "his migrati". bidi in 1 file. backslash-quote in all 42 bs+tr rows — unescape. info_lang lists ar no dir. total 42 vs 50.',
  'riyadussalihin': '339 EN rows backslash-quote artifact — unescape. 1 cross-section dup legit.',
  'musnad-ahmad': '(dup above)',
  'sunan-darimi': 'grade ": Sahih" leading colon → strip. intro_ur Latin "سunan". 2 cross-section dups legit.',
  'bulugh-al-maram': 'metadata_malformed — header optional, leave. sec5 "بًاب"(FATHATAN) vs "بَاب"(FATHA) normalization — document.',
  'dehlawi': 'grades empty (acceptable).',
  'fath-al-rabbani': '(dup above)',
  'virtues': 'intro truncated "respond to Alla". misplaced hadith 20 in section 2 instead of 7 — document. 11 cross-section dups legit.',
}

const FIXER_SCHEMA = {
  type: 'object',
  properties: {
    edition: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' }, description: 'repo-relative paths of files actually edited' },
    fixes_applied: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, fix: { type: 'string' }, count: { type: 'number' },
    }, required: ['file','fix','count'] } },
    known_issues: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string' }, kind: { type: 'string' },
      location: { type: 'string' }, description: { type: 'string' },
      action_needed: { type: 'string', description: 'manual rescrape/refill needed, or external verify' },
    }, required: ['severity','kind','location','description','action_needed'] } },
    notes: { type: 'string' },
  },
  required: ['edition','files_changed','fixes_applied','known_issues','notes'],
}

const phase_skip = {}

phase('Fix')
log(`Fixing ${EDITIONS.length} editions under ${EDITIONS_DIR}`)

const FIX_INSTRUCTIONS = (ed) => `You are fixing audit defects in the hadith .toon repo at ${REPO}. Branch audit-fixes is checked out. You own edition "${ed}" only — edit ONLY files under editions/${ed}/. Do NOT touch editions outside ${ed}, do NOT touch viewer.html/sunnah.js, do NOT run git.

CRITICAL RULES:
- READ each file with the Read tool BEFORE editing it. Edit with the Edit/Write tool. Preserve all valid data.
- Apply ONLY these fixes. Do not "improve" anything else.
- NEVER fabricate, machine-translate, or guess missing hadith content. Missing = document, not invent.
- NEVER renumber hadith numbers except when DELETING a garbage row and renumbering the surviving tail (and only when the audit note says to).
- NEVER auto-deduplicate cross-section/cross-chapter repeated hadiths — repetition across chapters is normal in hadith corpora. Leave them.
- For runaway repetition loops in a single row (phrase repeated 10s-100s of times): truncate to ONE instance of the phrase, append " [corrupt: repetition loop truncated]" — do not delete the row.
- For "intentional"/"external"/"gap"/"non-numeric HN" items: DO NOT modify the file. Instead write an entry into the known_issues array.
- After editing a file, re-Read it to confirm the edit landed and the file still has a valid header and parses.

FIXES TO APPLY (only those relevant to this edition per the audit note):
1. count_literal header: if a section file's header is "hadiths[count]{...}", count the data rows (lines after header that start with a quote), replace [count] with that real number. (bukhari)
2. Strip bidi control characters (U+200E/F, U+202A-E, U+2066-69) from data fields — leave structure intact.
3. Non-canonical grades: replace the grades field value "No Data Available" with "" (empty). Strip a leading "[" or leading ": " from grade values. Replace "None" with "".
4. info_lang_mismatch: if info.toon available_languages lists "ar" but there is NO editions/${ed}/translations/ar directory (AR lives in sections/), remove "ar" from available_languages. (only if audit note says so)
5. leading_ordinal: strip a leading ordinal from translation text — patterns: ^<digits>.<space>, ^<digits>)<space>, ^(<digits>)<space>, and the language-specific digit variants (Bengali ০-৯, Urdu/Persian ۰-۹, Devanagari ०-९, Tamil ௦-௯) followed by . or ) and a space — ONLY when the digits duplicate the hadith number of that row. Do NOT strip text that is not a redundant ordinal.
6. markdown_residue: strip markdown markers from translation text: leading "# " headings, "- " or "* " bullet leaders, surrounding "*...*" italics, surrounding "**...**" bold, backtick fences \`\`\`. KEEP content, drop markers. EXCEPTION (bukhari en/fr): a backtick before a capital letter starting a name like \`Urwa, \`Aisha is Arabic-ayn transliteration convention — DO NOT strip single backticks in bukhari.
7. trailing scraping residue: strip these scraper suffix patterns from the end of translation text: "Sahih <name> <N> Hadees: <M> Arabic Hadees: <M>", "Hadith arabe : <N>", "شمائل ترمذی حدیث:<N>". Strip from end only.
8. backslash-escape artifact: replace literal "\\W" where W is a capital letter (\\The, \\I, \\A) with "W"; replace literal "\\n" embedded in text with a real newline-free space; collapse runs of 4+ double-quotes """""" down to "" (escaped quote). (aladab-almufrad en, hisn en, nawawi bs/tr, riyadussalihin en)
9. hisn EN CSV-quoting: rows with runaway """""" that split one logical row into many fake fields — re-quote: collapse the quote runs so the row has exactly 2 fields (hadithnumber,text). Preserve all text content.
10. chapter_intro off-by-one / wrong: re-derive the correct chapter_intro for each section from the edition's info.toon section index (the translations[N]{language,sections,path} block or a sections index) and overwrite the chapter_intro field in every row of the section file. (abdurrazzaq: each section carries the PREVIOUS section's name; hisn: sections 67-132 all carry section 132's title). If info.toon has no usable per-section name index, document as known_issue instead of guessing.
11. muslim tr synthetic rows: delete rows whose text matches /^Hadith <name> ra:\\n? Rüya:/ (fabricated Turkish), renumber the surviving rows in that file sequentially from the first surviving number, verify the file still has a valid header count (update hadiths[N]).
12. ibnmajah fr AI preambles: delete rows whose text is entirely an AI preamble (/^Voici la traduction/ or /^Traduction[ :]/), renumber survivors, update header count.
13. ibnhibban en JSON-LD rows: delete rows whose text contains "mainEntityOfPage" or "en.tohed.com" (scrape residue, not a hadith), document the deleted HN as missing in known_issues.
14. abudawud bn labeled rows: delete rows whose bn text contains "narrator chain:" or "hadith body:" (raw English AI labels), renumber, update header count, verify AR row parity.
15. musannaf ?? corruption: replace " ?? " (space-??-space) between two Arabic/name tokens with "، " (Arabic comma+space). For ?? mid-word with no surrounding spaces, replace with "[corrupt]" — do not guess the letter.
16. mustadrak n-artifact: remove a standalone "ن " or "n " token that sits between two Arabic-script tokens (newline stripped to bare n). Be conservative: only remove when the token is exactly "ن" or "n" surrounded by spaces or Arabic words on both sides. Do NOT remove the Arabic letter ن that is part of a word.
17. muajam-tabarani-saghir grades-in-Urdu: where the grades field contains Urdu script (not a grade), move that text to the narrator_chain field if narrator_chain is empty, else set grades to "".
18. qudsi cross-script: in bn/te/ta translation rows, if the text contains obvious foreign-script runs (Korean Hangul, Cyrillic Russian, Devanagari) that are clearly not the target language, strip those runs. If the row is majority-foreign, do NOT guess — document as known_issue (needs rescrape).
19. Runaway repetition loops in a row (shamail ur HN161, bayhaqi ur HN10342, fath-al-rabbani en HN142/152, tirmidhi intro_hi, nasai intro_ur, aladab en row548): truncate the row/intro to the first clean instance of the repeated phrase, append " [corrupt: repetition loop truncated]". For intro fields in info.toon, truncate similarly.
20. mishkat swapped sections 20/21: for EACH translation language, swap the entire file contents of sections/20.toon and sections/21.toon (so EN/sec20 gets Foods, sec21 gets Hunting, matching AR). Use Read on both, Write swapped. Verify AR sec20/sec21 unchanged.

For ANY defect you cannot safely fix (data truly lost, ambiguous, needs external source, intentional numbering, missing section files, non-numeric HN that is intentional, gaps): do NOT modify the file. Instead add a known_issues entry with: severity (high/medium/low), kind, location (file:line or HN range), description (what is wrong, real evidence you saw), action_needed (one of: "manual rescrape from sunnah.com/origin", "external concordance verify", "intentional — leave as-is", "needs human review").

When done, return: edition, files_changed (real paths edited), fixes_applied (per file: what fix, how many rows), known_issues (the external/intentional/gap items you documented), notes.

Audit note for THIS edition (${ed}):
${AUDIT_NOTES[ed] || '(no specific note — apply only generic fixes 1-8 if present; if file is clean, report no changes)'}`

async function agentRetry(prompt, opts, tries=5) {
  for (let t=1; t<=tries; t++) {
    const r = await agent(prompt, opts)
    if (r) return r
    log(`retry ${t}/${tries} ${opts.label}`)
  }
  return null
}

async function fixOne(ed) {
  return agentRetry(FIX_INSTRUCTIONS(ed), { label: `fix:${ed}`, phase: 'Fix', schema: FIXER_SCHEMA, effort: 'high' })
}

const BATCH = 4
const fixerResults = []
for (let i = 0; i < EDITIONS.length; i += BATCH) {
  const batch = EDITIONS.slice(i, i + BATCH)
  log(`Fix batch ${Math.floor(i/BATCH)+1}: ${batch.join(', ')}`)
  const out = await parallel(batch.map(ed => () => fixOne(ed)))
  for (const o of out) if (o) fixerResults.push(o)
  log(`Fix cumulative: ${fixerResults.length}/${EDITIONS.length}`)
}

phase('Verify')
// Light verify: a second agent re-reads a sample of changed files per edition to confirm no breakage.
const verifyResults = await parallel(fixerResults.slice(0, 0)) // placeholder; verification done by re-audit script in main thread
log(`Verify: deferred to main-thread toon_audit.py re-run`)

phase('Synthesize')
// Merge all per-edition known_issues into one KNOWN_ISSUES.md content; summarize changes.
const synthPrompt = `You are synthesizing the fix-run results into two things:
1. A full KNOWN_ISSUES.md markdown document — every external/intentional/gap/manual-rescrape item, grouped by edition, each with severity, location, description, and action_needed. Include a top summary table of counts by action_needed category. Be exhaustive — these are the items humans must act on (manual rescrape / external verify / intentional leave / human review). Include the unrecoverable data-loss items explicitly with their hadith number ranges.
2. A short summary of total fixes applied across all editions (counts by fix type).

Fix-run results (JSON):
${JSON.stringify(fixerResults, null, 0)}

Return {known_issues_md: "<full markdown>", fix_summary: "<short markdown>", total_files_changed: <number>, total_known_issues: <number>}.`

const synthesis = await agent(synthPrompt, {
  label: 'synthesize-fixes',
  phase: 'Synthesize',
  schema: { type: 'object', properties: {
    known_issues_md: { type: 'string' },
    fix_summary: { type: 'string' },
    total_files_changed: { type: 'number' },
    total_known_issues: { type: 'number' },
  }, required: ['known_issues_md','fix_summary'] },
  effort: 'max',
})

return {
  editions_fixed: fixerResults.length,
  fixers: fixerResults.map(f => ({ edition: f.edition, files_changed: (f.files_changed||[]).length, known_issues: (f.known_issues||[]).length })),
  total_files_changed: synthesis.total_files_changed,
  total_known_issues: synthesis.total_known_issues,
  known_issues_md: synthesis.known_issues_md,
  fix_summary: synthesis.fix_summary,
}
