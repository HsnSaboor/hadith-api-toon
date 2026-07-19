export const meta = {
  name: 'toon-hardcase-sources',
  description: 'Find scholarly sources for 7 hard-case books with truncated translations. Probe sunnah, al-hadees, fawaz, HF, tohed, shumaila.ws, quranohadith. Map numbering. Report only.',
  phases: [
    { title: 'Probe', detail: 'subagents per book probe all sources, map HN numbering, report recoverable truncations' },
    { title: 'Synthesize', detail: 'merge into HARDCASE_RECOVERY_REPORT.md' },
  ],
}
const REPO = '/home/saboor/code/hadith-api-toon'
const ED = `${REPO}/editions`

const HARD_CASES = [
  { book: 'bayhaqi', truncated: 4775, note: 'Bayhaqi al-Sunan al-Kubra. AR+UR from al-hadees.com. EN truncated.' },
  { book: 'sunan-al-daraqutni', truncated: 2285, note: 'Sunan al-Daraqutni. Only 232 from git.' },
  { book: 'muajam-tabarani-saghir', truncated: 1128, note: "Mu'jam Tabarani Saghir. Only 62 from quranohadith." },
  { book: 'mustadrak', truncated: 593, note: 'Mustadrak al-Hakim. Only 71 from git baseline.' },
  { book: 'musannaf-ibn-abi-shaybah', truncated: 466, note: 'Musannaf Ibn Abi Shaybah. Only 1 recoverable.' },
  { book: 'silsila-sahih', truncated: 22, note: 'Silsilat al-Ahadith as-Sahihah by Al-Albani. EN was AI-translated, 0 scholarly source.' },
  { book: 'lulu-wal-marjan', truncated: 135, note: 'Lulu wal-Marjan (Bukhari+Muslim compilation). Only 134 from islam360.' },
]

const FIND_SCHEMA = {
  type: 'object', properties: {
    book: { type: 'string' },
    sources_checked: { type: 'array', items: { type: 'object', properties: {
      source: { type: 'string' },
      url_or_path: { type: 'string' },
      available: { type: 'boolean' },
      langs: { type: 'array', items: { type: 'string' } },
      hn_numbering: { type: 'string' },
      sample_hn_mapping: { type: 'string', description: 'concrete example: repo HN X = source HN Y' },
      truncations_covered: { type: 'number', description: 'how many of the truncated HNs have full text in this source' },
      sample_full_text: { type: 'string', description: 'one example of full text found for a truncated HN' },
    }, required: ['source','available','hn_numbering'] } },
    numbering_mapping: { type: 'string', description: 'how to map repo HN to each source HN (offset, same, formula, or lookup table)' },
    total_recoverable: { type: 'number' },
    total_truncated: { type: 'number' },
    unrecoverable: { type: 'number', description: 'truncations with NO source found anywhere' },
    notes: { type: 'string' },
  }, required: ['book','sources_checked','total_recoverable','total_truncated'],
}

const SOURCE_GUIDE = `
SOURCES TO PROBE (scholarly human translations ONLY — NO machine translation, NO hadithunlocked.com, NO LLM):

1. SUNNAH.COM (ajax endpoints — existing scripts had access):
   - https://sunnah.com/ajax/<lang>/<collection>/<page> (lang: english, urdu, bangla)
   - Collections to try: bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah, malik, nasai-kubra, ahmad
   - Also try: https://sunnah.com/<collection>/<page> (HTML page, may have Cloudflare)
   - Read scrape_sunnah_bukhari.py + test_sunnah_ajax*.py for exact URL patterns
   - CRITICAL: sunnah.com HN may differ from repo HN. Map by matching Arabic text or page structure.

2. AL-HADEES.COM (Arabic + Urdu — existing scrape scripts):
   - https://al-hadees.com/hadees-name/<book>/0 (book index page)
   - https://al-hadees.com/hadees-subjects/<book>/<page> (subject pages)
   - https://al-hadees.com/hadees/<book>/<page>/<num> (individual hadith pages)
   - Read scrape_alhadees_full.py, scrape_ahmad_alhadees.py, scrape_bayhaqi_alhadees.py for patterns
   - Books covered: musnad-ahmed, bayhaqi (confirmed). Try others.

3. FAWAZAHMED0/HADITH-API (CDN):
   - https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/<lang3>-<book>.min.json
   - lang3: eng, urd, ben, fra, ind, tur, rus
   - Also try non-standard slugs: ara-bayhaqi, eng-sunan-al-daraqutni, urd-musannaf-ibn-abi-shaybah, etc.
   - Check editions.json for full book list: https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions.json
   - Canonical-4: abudawud, ibnmajah, malik, nasai. Others may exist — PROBE ALL.

4. HUGGINGFACE DATASETS:
   - https://huggingface.co/api/datasets?search=hadith
   - https://huggingface.co/api/datasets?search=bayhaqi
   - https://huggingface.co/api/datasets?search=daraqutni
   - https://huggingface.co/api/datasets?search=tabarani
   - https://huggingface.co/api/datasets?search=mustadrak
   - https://huggingface.co/api/datasets?search=musannaf
   - https://huggingface.co/api/datasets?search=silsila+sahih
   - https://huggingface.co/api/datasets?search=lulu+marjan
   - Check each result for matching content.

5. TOHED.COM:
   - https://en.tohed.com/hadith/<slug>/<HN>/ (confirmed slugs: nasai, shamail-tirmidhi, musannaf-ibn-abi-shaybah, sahih-ibn-khuzaymah, sahih-ibn-hibban)
   - Try unconfirmed slugs: bayhaqi, sunan-al-daraqutni, mustadrak, silsila-sahih, lulu-wal-marjan, muajam-tabarani-saghir
   - Renders Arabic + EN + UR + FR per hadith page.

6. SHUMAILA.WS (if exists):
   - Try: https://shumaila.ws/ or https://www.shumaila.ws/
   - Try: https://shumaila.ws/hadith/ or similar paths
   - Probe for hadith content.

7. QURANOHADITH.COM:
   - Existing scrape data in ~/code/hadith-api-toon-alt/scraped_data/
   - Try: https://quranohadith.com/ or https://www.quranohadith.com/
   - Check for English/Urdu translations of these books.

8. OTHERS TO PROBE:
   - https://hadithenc.com/ (hadeethenc — known hadith translation site)
   - https://www.hadeethenc.com/
   - https://sunnah.com/hadith/<number> (direct hadith by global number)
   - https://islam360.com/ (existing islam360 sqlite in backups)
   - GitHub: search for "bayhaqi hadith english", "daraqutni english", "tabarani english", "mustadrak english", "musannaf english", "silsila sahiha english", "lulu marjan english"
   - GitHub API: https://api.github.com/search/code?q=bayhaqi+hadith+english+extension:json

NUMBERING ALIGNMENT (CRITICAL):
- For each source, determine EXACT mapping from repo HN to source HN:
  - SAME: source HN == repo HN
  - OFFSET: source HN = repo HN + N (find N)
  - DIFFERENT_SCHEME: source uses book+hadith, or per-companion, or global
  - LOOKUP: need a lookup table (map by Arabic text match)
- Verify mapping with 3+ sample HNs: find repo HN in source, confirm it's the SAME hadith (compare Arabic text).
- Report the mapping formula/table.

METHOD:
1. READ existing scraper scripts to understand URL patterns.
2. PROBE each source via curl/WebFetch — check if the book exists, which langs, sample HN.
3. For each truncated HN in the book, check if the source has full text.
4. Map repo HN → source HN (verify with 3+ samples).
5. Report: which sources cover which langs, how many truncations recoverable, the exact numbering mapping.
DO NOT apply fixes, use LLM, or use hadithunlocked.com.
`

phase('Probe')
log(`Probing sources for ${HARD_CASES.length} hard-case books`)

async function retry(p, o, t=5) { for (let i=1;i<=t;i++){ const r=await agent(p,o); if(r) return r; log(`retry ${i}/${t} ${o.label}`)} return null }

const results = []
for (let i=0; i<HARD_CASES.length; i++) {
  const hc = HARD_CASES[i]
  log(`Probing ${hc.book} (${hc.truncated} truncated)`)
  const r = await retry(
    `You are finding scholarly translation sources for TRUNCATED hadiths in the .toon repo at ${REPO}.
${SOURCE_GUIDE}

YOUR BOOK: ${hc.book} — ${hc.note}
Truncated translations: ${hc.truncated}

TASKS:
1. READ all existing scraper scripts in ${REPO}/ to understand URL patterns.
2. Scan this book's sections for truncated translations (tr_len/ar_len < 0.5, ar_len>50). Use Bash/python.
3. PROBE each source for this book:
   a. curl fawaz CDN editions.json — check if ${hc.book} is listed (non-canonical books may exist).
   b. curl tohed.com with slug variants of ${hc.book}.
   c. curl sunnah.com ajax — try collection slug matching ${hc.book}.
   d. curl al-hadees.com — try book slug matching ${hc.book}.
   e. curl HuggingFace API — search for ${hc.book}.
   f. curl shumaila.ws, quranohadith.com, hadeethenc.com.
   g. curl GitHub code search API.
   h. Check ~/code/hadith-api-toon-alt/ for any backup of ${hc.book} that was missed.
   i. Check ~/code/hadith-api-toon-new/ for any final.json for ${hc.book}.
   j. Check git history for older full versions.
4. For each source that HAS the book: determine HN numbering mapping (verify with 3+ samples).
5. For each source: count how many truncated HNs have full text there.
6. Report: per-source availability, langs, HN mapping, truncations recoverable, sample full text.

Use Bash for curl probes + python scanning. Read for inspecting. Be thorough — try every source.
DO NOT apply fixes, use LLM, or hadithunlocked.com.`,
    { label: `probe:${hc.book}`, phase: 'Probe', schema: FIND_SCHEMA, effort: 'high' }
  )
  if (r) results.push(r)
  log(`Probe ${results.length}/${HARD_CASES.length}`)
}

phase('Synthesize')
const synth = await agent(`You are writing the HARDCASE_RECOVERY_REPORT.md for 7 hard-case hadith books.
${results.length} books probed; each subagent read scripts, probed sunnah/al-hadees/fawaz/HF/tohed/shumaila/quranohadith/hadeethenc/github, mapped numbering.

Results (JSON):
${JSON.stringify(results.map(r => ({book:r.book, trunc:r.total_truncated, rec:r.total_recoverable, unrec:r.unrecoverable, sources:r.sources_checked.map(s=>({src:s.source, avail:s.available, langs:s.langs, hn:s.hn_numbering, covered:s.truncations_covered||0}))})), null, 0)}

Produce a report:
1. Per-book: which sources found, which langs, HN mapping, how many truncations recoverable.
2. Sources that NEWLY cover these hard cases (not in the original RECOVERY_REPORT.md).
3. The numbering mapping for each source (exact formula/offset/lookup).
4. Which truncations are NOW recoverable that weren't before.
5. Which are STILL unrecoverable (no scholarly source anywhere — need new scrape).
6. Scraper scripts needed: for each source that covers a hard-case book but has no existing script, specify the URL pattern + what to scrape.
Return {report_md, new_recoverable, still_unrecoverable}.`,
  { label: 'synthesize-hardcase', phase: 'Synthesize',
    schema: { type: 'object', properties: {
      report_md: { type: 'string' },
      new_recoverable: { type: 'number' },
      still_unrecoverable: { type: 'number' },
    }, required: ['report_md'] }, effort: 'max' })

return { books_probed: results.length, results, report: synth.report_md, new_recoverable: synth.new_recoverable, still_unrecoverable: synth.still_unrecoverable }
