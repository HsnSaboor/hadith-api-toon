export const meta = {
  name: 'toon-sourcefind',
  description: 'Find recovery sources for KNOWN_ISSUES data-loss items across sunnah.com/al-hadees/fawazahmed0/HF/tohed, + LLM fallback; produce fix plan (no apply)',
  phases: [
    { title: 'Probe', detail: 'agents probe each source per recovery item via WebFetch, confirm real hadith text exists' },
    { title: 'Synthesize', detail: 'merge into SOURCE_RECOVERY_PLAN.md with per-item source+method+confidence' },
  ],
}

const REPO = '/home/saboor/code/hadith-api-toon'

// Recovery items from KNOWN_ISSUES (the unrecoverable data-loss set).
const RECOVERY = [
  { id: 'ibnhibban-en-jsonld', edition: 'sahih-ibn-hibban', lang: 'en', hns: [1139, 3610, 5690, 7174], kind: 'JSON-LD scrape residue replaced real EN translation' },
  { id: 'ibnhibban-en-truncated', edition: 'sahih-ibn-hibban', lang: 'en', hns: [1517, 1615, 1714, 1845, 2128, 2505, 3784, 3812, 5905, 6142, 6971, 7402], kind: 'EN text truncated mid-word' },
  { id: 'ibnmajah-fr-ai', edition: 'ibnmajah', lang: 'fr', hns: [597, 1311, 1855, 2271, 2291, 2520, 4316], kind: 'AI preamble replaced real FR translation' },
  { id: 'lulu-en-missing', edition: 'lulu-wal-marjan', lang: 'en', hns: [], kind: '281 missing HNs across all 55 sections (1625 vs 1906) — full re-pull needed', note: 'AR/UR intact at 1906; EN only' },
  { id: 'nasai-sec36', edition: 'nasai', lang: 'all', hns: [], kind: 'section 36 entirely absent (HN ~3939-3965) from AR + all 8 translations', note: 'AR source must be recovered first, then 8 langs' },
  { id: 'musannaf-ur-gibberish', edition: 'musannaf-ibn-abi-shaybah', lang: 'ur', hns: [5898, 22496], kind: 'plvvlqj gibberish, real UR lost' },
  { id: 'shamail-ur-161', edition: 'shamail-tirmidhi', lang: 'ur', hns: [161], kind: 'AI self-monologue repetition loop, genuine completion lost' },
  { id: 'khuzaymah-index', edition: 'sahih-ibn-khuzaymah', lang: 'ar', hns: [], kind: '1059/1073 info.toon index rows malformed + 320 chapter_intro Urdu-contaminated', note: 're-derive from a clean section index / re-pull metadata' },
  { id: 'silsila-en-empty', edition: 'silsila-sahih', lang: 'en', hns: [], kind: '~3182 of 3550 EN rows now empty after scraper-residue strip — real EN was never present', note: 'was ~90% scrape residue; needs genuine EN source' },
  { id: 'abudawud-bn-4588', edition: 'abudawud', lang: 'bn', hns: [4588], kind: 'Bengali vowel corruption' },
]

// Confirmed working source facts (from main-thread probes).
const SOURCE_FACTS = `
KNOWN SOURCE ACCESS (main-thread verified):
- fawazahmed0/hadith-api CDN: https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/<lang>-<edition>.min.json  (lang: eng/fra/urdu/ben/ara; editions: abudawud, ibnmajah, malik, nasai ONLY — canonical 4). Returns JSON array of hadiths with metadata. JSON at @1/editions.json.
- tohed.com: https://en.tohed.com/hadith/<edition-slug>/<HN>/  returns full HTML page with Arabic + translations. Confirmed 200: nasai, shamail-tirmidhi, musannaf-ibn-abi-shaybah, sahih-ibn-khuzaymah, sahih-ibn-hibban. Slug for ibnhibban = "sahih-ibn-hibban". The page renders Arabic + (en/ur/fr per hadith) text.
- al-hadees.com: https://al-hadees.com/hadees/<book>/<page>/0  (Arabic + Urdu). Used by existing scrape_alhadees_full.py for musnad-ahmad, bayhaqi. Coverage of non-canonical collections partial.
- sunnah.com: root + /<collection>/ returns 403 (Cloudflare). BUT ajax endpoints work: https://sunnah.com/ajax/<lang>/<collection>/<page>  (lang: english/urdu/bangla). Existing scrape_sunnah_bukhari.py used these. Coverage: bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah, malik, nasai-kubra, shamail(?), ahmad. NOT ibnhibban, lulu, musannaf, silsila, khuzaymah, hisn, virtues, virtues.
- HuggingFace: dataset "fawazahmed0/hadith-data" mirrors the CDN (canonical 4). Other hadith datasets (AbderrahmanSkiredj1/hadiths_ar_fr..., arbml/Hadith) are partial/experimental — check per item.
- hadithunlocked.com: DO NOT USE — translations are Google/machine-translated and prefixed with "[AI]" per hadith (user-confirmed bad quality). Reject entirely.
- openrouter LLM: 6 API keys available for AI translation as LAST RESORT only where NO human source exists. Use a strong model; translate from intact AR source; mark output as "[AI-translation]" prefix per row so consumers know. Must be the absolute final fallback.

Do NOT probe hadithunlocked.com at all. Treat it as non-existent.
`

phase('Probe')
log(`Probing sources for ${RECOVERY.length} recovery items`)

const PROBE_SCHEMA = {
  type: 'object',
  properties: {
    item_id: { type: 'string' },
    sources: { type: 'array', items: { type: 'object', properties: {
      source: { type: 'string', description: 'sunnah.com | tohed.com | fawazahmed0 | al-hadees.com | huggingface | openrouter-llm | git-history | none' },
      url_pattern: { type: 'string', description: 'exact URL pattern to fetch each hadith' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low', 'none'] },
      coverage: { type: 'string', description: 'how many of the target HNs the source actually returns real text for (e.g. "7/7", "partial", "0")' },
      evidence: { type: 'string', description: 'what you observed by fetching: did real hadith text come back? quote a snippet' },
      language_match: { type: 'boolean', description: 'does source have the target language (en/fr/ur/bn)' },
      notes: { type: 'string' },
    }, required: ['source','url_pattern','confidence','coverage','evidence'] } },
    best_source: { type: 'string' },
    needs_llm_fallback: { type: 'boolean' },
    llm_fallback_scope: { type: 'string', description: 'which HNs/languages need LLM translation because no source exists' },
  },
  required: ['item_id','sources','best_source','needs_llm_fallback'],
}

const PROBE_PROMPT = (item) => `You are sourcing recovery data for a hadith .toon repository. An audit found this data is lost/corrupt and must be re-pulled from a clean source. DO NOT fix anything — only find and confirm sources, and report.

${SOURCE_FACTS}

YOUR RECOVERY ITEM:
- id: ${item.id}
- edition: ${item.edition}
- language needed: ${item.lang}
- target hadith numbers: ${item.hns.length ? item.hns.join(', ') : '(see note — full re-pull)'}
- what is wrong: ${item.kind}
${item.note ? '- note: ' + item.note : ''}

YOUR JOB:
1. Use WebFetch to probe EACH candidate source for this edition + language. For each target HN (sample 2-3 HNs if many), fetch the URL and confirm REAL hadith text comes back (not a 404, not a stub, not the same corrupt text). Quote a short snippet of what you found.
2. Candidate sources to try (in priority order, skip ones that clearly don't cover this edition):
   a. fawazahmed0 CDN: https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/<lang3>-<edition>.min.json — fetch it, check if edition is one of the canonical 4 (abudawud/ibnmajah/malik/nasai). lang3 = eng/fra/urdu/ben/ara.
   b. tohed.com: https://en.tohed.com/hadith/<edition-slug>/<HN>/  — for ibnhibban use slug "sahih-ibn-hibban". Check 2-3 HNs. Confirm Arabic + the language you need render.
   c. al-hadees.com: https://al-hadees.com/hadees/<book>/<page>/0  — primarily Arabic+Urdu; check if it covers this edition.
   d. sunnah.com ajax: https://sunnah.com/ajax/<lang>/<collection>/<page>  — may Cloudflare-block WebFetch (403); if so mark coverage 0 with note "blocked, existing scrape_*.py scripts had access — retry with those scripts".
   e. HuggingFace: check if "fawazahmed0/hadith-data" or another dataset has this edition+lang. https://huggingface.co/api/datasets?search=<edition>
3. For each source, record: source name, exact URL pattern, confidence (high/medium/low/none), coverage (how many target HNs return real text), evidence (snippet you observed), whether the source has the target LANGUAGE.
4. Pick best_source (the one with highest coverage of the target HNs in the right language).
5. If NO source returns real text for some HNs, set needs_llm_fallback=true and llm_fallback_scope = which HNs/langs need openrouter LLM translation (translate from intact AR source, prefix "[AI-translation]").
6. Also consider: is the AR source for these HNs intact in the repo? (You can Read editions/<edition>/sections/*.toon to check the Arabic field is present even if the translation is corrupt.) If AR is intact, LLM translation from AR is viable.

Be precise. Only report what you actually fetched and observed. Do not invent coverage. If a source returns the SAME corrupt text the repo has, that is coverage=0 for recovery purposes — note it.

Return the structured result.`

async function retry(p, opts, t=5){ for(let i=1;i<=t;i++){ const r=await agent(p,opts); if(r) return r; log(`retry ${i}/${t} ${opts.label}`);} return null }

const results = []
const BATCH = 3
for (let i = 0; i < RECOVERY.length; i += BATCH) {
  const batch = RECOVERY.slice(i, i + BATCH)
  log(`Probe batch ${Math.floor(i/BATCH)+1}: ${batch.map(b=>b.id).join(', ')}`)
  const out = await parallel(batch.map(item => () => retry(PROBE_PROMPT(item), { label: `probe:${item.id}`, phase: 'Probe', schema: PROBE_SCHEMA, effort: 'high' })))
  for (const o of out) if (o) results.push(o)
  log(`Probe cumulative: ${results.length}/${RECOVERY.length}`)
}

phase('Synthesize')
const synth = await agent(`You are synthesizing a SOURCE_RECOVERY_PLAN.md for the hadith .toon repository. This is a FIX PLAN ONLY — the user has explicitly said do not apply yet, just find sources and give the plan. The plan must tell a human exactly how to recover each item.

Recovery items + source-probe results (JSON):
${JSON.stringify(results, null, 0)}

Source access facts:
${SOURCE_FACTS}

Produce a markdown plan with:
1. Summary table: per recovery item → best source → coverage → action (rescrape / LLM-translate / leave-documented).
2. For EACH item, a detailed recovery procedure: exact source, exact URL pattern, what to fetch, how to map the fetched text back into the .toon row schema (hadithnumber,text for translations; 7-field for AR), how to handle per-HN cases, and whether the existing scrape_*.py scripts can be reused/adapted.
3. The LLM-translation fallback section: which items/HNs/languages have NO human source and must use openrouter (translate from intact AR, prefix "[AI-translation]"). List them explicitly.
4. A "do not recover / accept loss" section for any item where even AR is lost and no source exists (if any).
5. A recommended execution order (canonical-4 fawaz rescrape first since bulk+clean, then tohed, then al-hadees, then sunnah ajax via existing scripts, then LLM fallback last).
6. Risk notes (rate limits, Cloudflare, slug mismatches, HN numbering differences between sources).
Return { plan_md: "<full markdown>", action_counts: {rescrape: N, llm_translate: N, accept_loss: N} }.`,
  { label: 'synthesize-plan', phase: 'Synthesize', schema: { type:'object', properties: { plan_md:{type:'string'}, action_counts:{type:'object'} }, required:['plan_md'] }, effort: 'max' })

return { items_probed: results.length, results, plan_md: synth.plan_md, action_counts: synth.action_counts }
