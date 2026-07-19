export const meta = {
  name: 'toon-source-recovery',
  description: 'Scrape all external sources (sunnah, al-hadees, fawaz, HF, tohed, git history) for 56K truncated translations. Map numbering. Report recoverable. No apply, no LLM, no hadithunlocked.',
  phases: [
    { title: 'Scan', detail: 'subagents per source-book read scripts, probe sources, map HN numbering, report recoverable truncations' },
    { title: 'Synthesize', detail: 'merge into RECOVERY_REPORT.md with per-source coverage + numbering mapping' },
  ],
}
const REPO = '/home/saboor/code/hadith-api-toon'
const ED = `${REPO}/editions`
const ALT = '/home/saboor/code/hadith-api-toon-alt'
const NEW = '/home/saboor/code/hadith-api-toon-new'
const CACHE = `${REPO}/scripts/cache`

const BOOKS = [
  'abdurrazzaq','abudawud','aladab-almufrad','bayhaqi','bukhari','bulugh-al-maram',
  'dehlawi','fath-al-rabbani','ibnhibban','ibnmajah','lulu-wal-marjan',
  'malik','mishkat','muajam-tabarani-saghir','musannaf-ibn-abi-shaybah','muslim',
  'musnad-ahmad','mustadrak','nasai','nasai-kubra','nawawi','qudsi','riyadussalihin',
  'sahih-ibn-khuzaymah','shamail-tirmidhi','silsila-sahih','sunan-al-daraqutni',
  'sunan-darimi','tirmidhi','virtues'
]
const LANGS = ['en','ur','bn','fr','hi','id','tr','ta','ru','roman-ur']

const FIND_SCHEMA = {
  type: 'object', properties: {
    book: { type: 'string' },
    sources_checked: { type: 'array', items: { type: 'object', properties: {
      source: { type: 'string' },
      url_or_path: { type: 'string' },
      available: { type: 'boolean' },
      lang_coverage: { type: 'array', items: { type: 'string' } },
      hn_numbering: { type: 'string', description: 'how HN maps to this source (same / offset / different scheme)' },
      full_text_samples: { type: 'number', description: 'how many truncated HNs have full text in this source' },
    }, required: ['source','available','hn_numbering'] } },
    truncations_recoverable: { type: 'array', items: { type: 'object', properties: {
      lang: { type: 'string' }, sec: { type: 'string' }, hn: { type: 'string' },
      current_tr_len: { type: 'number' },
      source: { type: 'string' },
      source_location: { type: 'string' },
      source_text_len: { type: 'number' },
      source_hn: { type: 'string', description: 'HN in the source (may differ from repo HN)' },
    }, required: ['lang','hn','source'] } },
    total_recoverable: { type: 'number' },
    total_truncated: { type: 'number' },
    numbering_notes: { type: 'string' },
  }, required: ['book','sources_checked','total_recoverable','total_truncated'],
}

const SOURCE_GUIDE = `
SOURCES TO CHECK (in priority order — scholarly human translations ONLY, NO machine translation, NO hadithunlocked.com):

1. LOCAL BACKUPS (check FIRST — fastest):
   - ~/code/hadith-api-toon-alt/<book>/<lang>.json — alt repo pre-fix, list of {hadithnumber,text}
   - ~/code/hadith-api-toon-new/<book>_final.json — pre-conversion source, dict keyed by HN, has 'translations' dict
   - ~/code/hadith-api-toon/scripts/cache/<lang3>-<book>.min.json — fawaz CDN cache (eng/urd/ben/fra/ind/tur/rus)
   - ~/code/hadith-api-toon-alt/hadith islam360/<book>.db — islam360 sqlite (hadees + hadees_languages tables)
   - ~/hadith-api-1/editions/<lang>-<book>.min.json — fawaz repo clone
   - ~/hadith-api-1/database/originals/<lang>-<book>.txt — raw scraped text

2. GIT HISTORY:
   - git log --oneline -- 'editions/<book>/translations/<lang>/sections/<N>.toon' — older versions may have full text
   - git show <commit>:editions/<book>/translations/<lang>/sections/<N>.toon — compare to current

3. FAWAZ CDN (live):
   - https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/<lang3>-<book>.min.json
   - canonical-4 only: abudawud, ibnmajah, malik, nasai (eng/urd/ben/fra/ind/tur/rus)
   - HN field = 'hadithNumber' (string), text = 'text' field

4. SUNNAH.COM (live — Cloudflare 403 on root, but ajax endpoints work from existing scripts):
   - https://sunnah.com/ajax/<lang>/<collection>/<page> (lang: english/urdu/bangla)
   - Collections: bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah, malik, nasai-kubra, ahmad
   - Existing scripts: scrape_sunnah_bukhari.py, test_sunnah_ajax*.py — READ THESE for URL patterns
   - HN numbering: sunnah uses its own hadithNumber per book; map to repo HN

5. AL-HADEES.COM (live — Arabic + Urdu):
   - https://al-hadees.com/hadees/<book>/<page>/0
   - Existing scripts: scrape_alhadees_full.py, scrape_ahmad_alhadees.py, scrape_bayhaqi_alhadees.py — READ THESE
   - Covers: musnad-ahmad, bayhaqi, and others (check scrape scripts for which books)

6. TOHED.COM (live — Arabic + EN + UR + FR):
   - https://en.tohed.com/hadith/<slug>/<HN>/ (slug: nasai, shamail-tirmidhi, musannaf-ibn-abi-shaybah, sahih-ibn-khuzaymah, sahih-ibn-hibban)
   - Renders Arabic + translations per hadith page

7. HUGGINGFACE DATASETS:
   - https://huggingface.co/api/datasets?search=hadith — check for any matching this book
   - https://huggingface.co/api/datasets?search=<book-name>

NUMBERING MAPPING (CRITICAL):
- Repo HN may differ from source HN. For each source, determine the mapping:
  - SAME: source HN == repo HN (direct match)
  - OFFSET: source HN = repo HN + N (constant offset)
  - DIFFERENT_SCHEME: source uses a completely different numbering (e.g. book+hadith vs global)
  - COMBINED: source combines multiple HNs into one row (e.g. "272, 273")
- For each truncated HN, find the corresponding source HN and verify the full text exists.

METHOD:
1. READ the existing scraper scripts (scrape_sunnah_bukhari.py, scrape_alhadees_full.py, etc.) to understand URL patterns + numbering.
2. Check LOCAL BACKUPS first (fastest). For each backup, load it, find matching HN, compare text length.
3. For books not in local backups, probe EXTERNAL SOURCES (fawaz CDN via curl, tohed via curl, sunnah ajax via existing scripts).
4. For each truncated row: if source has FULL text (source_len > 1.3 × current_tr_len AND source_len/ar_len >= 0.6), mark RECOVERABLE with source + location.
5. If no source has full text, mark NEEDS_RESRAPE (not LLM — we're not using LLM).
6. Report per-book: which sources have which langs, HN mapping, how many truncations recoverable.

DO NOT:
- Apply any fixes
- Use LLM for translation
- Use hadithunlocked.com
- Fabricate text
- Modify any .toon files
`

phase('Scan')
log(`Scanning sources for ${BOOKS.length} books`)

async function retry(p, o, t=5) { for (let i=1;i<=t;i++){ const r=await agent(p,o); if(r) return r; log(`retry ${i}/${t} ${o.label}`)} return null }

const results = []
const BATCH = 4
for (let i=0; i<BOOKS.length; i+=BATCH) {
  const b = BOOKS.slice(i, i+BATCH)
  log(`Scan batch ${Math.floor(i/BATCH)+1}: ${b.join(', ')}`)
  const out = await parallel(b.map(book => () => retry(
    `You are sourcing recovery text for TRUNCATED translations in the hadith .toon repo at ${REPO}.
${SOURCE_GUIDE}

YOUR BOOK: ${book}

TASKS:
1. READ all existing scraper scripts in ${REPO}/ (scrape_sunnah_bukhari.py, scrape_alhadees_full.py, scrape_ahmad_alhadees.py, scrape_bayhaqi_alhadees.py, convert_bukhari_translations.py, discover_languages.py, and any test_sunnah*.py) to understand:
   - Which URL patterns each uses
   - How HN numbering maps between source and repo
   - Which langs each source covers
2. Scan ALL sections of ${book} for truncated translations (tr_len/ar_len < 0.5, ar_len>50, tr_len>0, diacritics-stripped). Use Bash/python for bulk scanning.
3. For each truncated HN, check LOCAL BACKUPS:
   - ~/code/hadith-api-toon-alt/${book}/<lang>.json
   - ~/code/hadith-api-toon-new/<book>_final.json (or the closest matching filename)
   - ~/code/hadith-api-toon/scripts/cache/<lang3>-${book}.min.json
   - ~/hadith-api-1/editions/<lang3>-${book}.min.json
   For each backup: load it, find matching HN (map if needed), compare text length. If backup text is fuller (backup_len > 1.3 × current AND backup_len/ar >= 0.6), it's RECOVERABLE.
4. Check GIT HISTORY for older full versions of truncated section files:
   - git log --oneline -- 'editions/${book}/translations/<lang>/sections/<N>.toon'
5. For books covered by fawaz CDN (canonical-4: abudawud, ibnmajah, malik, nasai), curl the CDN and check if the truncated HN has full text.
6. For books covered by tohed.com, curl the tohed page for a sample of truncated HNs and check if full text renders.
7. For books covered by sunnah.com ajax, check if the ajax endpoint returns full text for truncated HNs.
8. For each source, record: source name, URL/path, available (bool), lang coverage, HN numbering scheme, how many truncations have full text.
9. Return: per-book summary of sources checked + ALL recoverable truncations (with source + location + source HN).

Use Bash for bulk scanning + curl for external probes. Read for inspecting backups. Be thorough. Quote real evidence.`,
    { label: `src:${book}`, phase: 'Scan', schema: FIND_SCHEMA, effort: 'high' }
  )))
  for (const o of out) if (o) results.push(o)
  log(`Scan cumulative ${results.length}/${BOOKS.length}`)
}

phase('Synthesize')
const synth = await agent(`You are writing the RECOVERY_REPORT.md for the hadith .toon truncation audit.
${results.length} books scanned; each subagent read scripts, probed local backups + git + fawaz CDN + tohed + sunnah + al-hadees + HF datasets, mapped HN numbering, reported recoverable truncations.

Results (JSON summary):
${JSON.stringify(results.map(r => ({book:r.book, total_trunc:r.total_truncated, recoverable:r.total_recoverable, sources:r.sources_checked.map(s=>({src:s.source, avail:s.available, hn:s.hn_numbering, full:s.full_text_samples||0}))})), null, 0)}

Produce a markdown report:
1. Per-source availability table: source × books covered × langs × HN numbering scheme × truncations recoverable
2. Per-book table: total truncated × recoverable from backup × recoverable from external × needs rescrape (no source)
3. Numbering mapping reference: for each source, how to map repo HN to source HN
4. Existing scraper scripts inventory: which scripts exist, what they scrape, URL patterns, which books/langs
5. Recommended recovery execution plan: which source to pull from first per book, in priority order
6. The hard cases: books with NO scholarly source for truncated langs (these need scholarly rescrape, NOT LLM)

Be precise. Cite real URLs and file paths. Do NOT recommend LLM.
Return {report_md, total_recoverable, total_needs_rescrape, sources_with_coverage}.`,
  { label: 'synthesize-recovery', phase: 'Synthesize',
    schema: { type: 'object', properties: {
      report_md: { type: 'string' },
      total_recoverable: { type: 'number' },
      total_needs_rescrape: { type: 'number' },
      sources_with_coverage: { type: 'array', items: { type: 'string' } },
    }, required: ['report_md'] }, effort: 'max' })

return { books_scanned: results.length, results, report: synth.report_md, recoverable: synth.total_recoverable, needs_rescrape: synth.total_needs_rescrape }
