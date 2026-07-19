export const meta = {
  name: 'toon-truncation-audit',
  description: 'Find all truncated translations (tr<60% of AR) across all books+langs, check backups/sources, report — no fixes',
  phases: [
    { title: 'Scan', detail: 'subagents per book read real files, find truncations, check local backups + git + external sources' },
    { title: 'Synthesize', detail: 'merge findings into report with source-availability per truncation' },
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
    truncations: { type: 'array', items: { type: 'object', properties: {
      lang: { type: 'string' }, section: { type: 'string' }, hn: { type: 'string' },
      ar_len: { type: 'number' }, tr_len: { type: 'number' }, ratio: { type: 'number' },
      ar_snippet: { type: 'string' }, tr_snippet: { type: 'string' },
      source_available: { type: 'string', enum: ['local_backup','git_history','fawaz','tohed','sunnah','none'] },
      source_location: { type: 'string', description: 'where the full text can be found' },
    }, required: ['lang','section','hn','ar_len','tr_len','ratio','source_available'] } },
    total_truncated: { type: 'number' },
    notes: { type: 'string' },
  }, required: ['book','truncations','total_truncated'],
}

const SOURCE_FACTS = `
LOCAL BACKUP SOURCES (check these for full pre-truncation translations):
- ~/code/hadith-api-toon-alt/<book>/en.json (or ur.json, etc) — alt repo pre-fix build
- ~/code/hadith-api-toon-new/<book>_final.json — pre-conversion source (has 'translations' dict per hadith)
- ~/code/hadith-api-toon/scripts/cache/<lang>-<book>.min.json — fawaz CDN cache (canonical 4 only)
- ~/code/hadith-api-toon-alt/hadith islam360/<book>.db — islam360 sqlite
- Git history: editions/<book>/translations/<lang>/sections/<N>.toon may have older full versions

EXTERNAL SOURCES:
- fawaz CDN: https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/<lang>-<book>.min.json (canonical 4: abudawud, ibnmajah, malik, nasai)
- tohed.com: https://en.tohed.com/hadith/<slug>/<HN>/ (renders AR+EN+UR+FR)
- sunnah.com ajax: https://sunnah.com/ajax/<lang>/<collection>/<page> (Cloudflare 403, existing scrape_*.py had access)

METHOD: for each truncated row, try the backup sources FIRST (local), then fawaz CDN (curl), then note 'none' if no source found.
`

phase('Scan')
log(`Scanning ${BOOKS.length} books for truncated translations`)

async function retry(p, o, t=5) { for (let i=1;i<=t;i++){ const r=await agent(p,o); if(r) return r; log(`retry ${i}/${t} ${o.label}`)} return null }

const results = []
const BATCH = 4
for (let i=0; i<BOOKS.length; i+=BATCH) {
  const b = BOOKS.slice(i, i+BATCH)
  log(`Scan batch ${Math.floor(i/BATCH)+1}: ${b.join(', ')}`)
  const out = await parallel(b.map(book => () => retry(
    `You are finding TRUNCATED translations in the hadith .toon repo at ${REPO}.
${SOURCE_FACTS}

YOUR BOOK: ${book}
For each translation language (en,ur,bn,fr,hi,id,tr,ta,ru,roman-ur), compare each hadith's translation text length vs the Arabic source text length.
A translation is TRUNCATED if: translation_len < 0.6 × arabic_len (after stripping Arabic diacritics from the AR text) AND arabic_len > 50 chars AND translation_len > 0 (not empty).

Steps:
1. Use Bash/python to scan ALL sections of ${book} for truncation candidates (tr_len/ar_len < 0.6, ar_len>50, tr_len>0).
   - Strip Arabic diacritics (unicodedata.normalize NFD, remove category Mn) before comparing.
   - For each candidate: record (lang, section, hn, ar_len, tr_len, ratio, ar_snippet[:100], tr_snippet[:100]).
2. For TOP candidates (most severe ratio), CHECK if a full translation exists in backup sources:
   - Try ~/code/hadith-api-toon-alt/${book}/<lang>.json (read, find matching HN, compare text length)
   - Try ~/code/hadith-api-toon-new/<final.json> (read, find 'translations.<lang>' for matching usid)
   - Try ~/code/hadith-api-toon/scripts/cache/<lang3>-<book>.min.json (fawaz 3-letter: eng/urd/ben/fra/ind/tur)
   - curl fawaz CDN for this book if canonical-4
   - git log for the section file to see if older version was full
3. For each truncation, set source_available: 'local_backup'|'git_history'|'fawaz'|'tohed'|'sunnah'|'none' + source_location.
4. Return ALL truncations found (not just samples) + total count + which have a backup source vs which need LLM.

Be thorough. Use Bash for bulk scanning, Read for inspecting backups. Quote real text.`,
    { label: `scan:${book}`, phase: 'Scan', schema: FIND_SCHEMA, effort: 'high' }
  )))
  for (const o of out) if (o) results.push(o)
  log(`Scan cumulative ${results.length}/${BOOKS.length}`)
}

phase('Synthesize')
const synth = await agent(`You are synthesizing the truncation audit report for the hadith .toon repo at ${REPO}.
${BOOKS.length} books scanned; each subagent compared translation vs Arabic text length (stripped diacritics), flagged ratio<0.6, and checked local backups + git + fawaz + tohed for full source.

Results (JSON):
${JSON.stringify(results.map(r => ({book:r.book, total:r.total_truncated, source_available: (r.truncations||[]).filter(t=>t.source_available!=='none').length, no_source: (r.truncations||[]).filter(t=>t.source_available==='none').length})), null, 0)}

Detail (top truncations per book):
${JSON.stringify(results.map(r => ({book:r.book, top3:(r.truncations||[]).slice(0,3).map(t=>({lang:t.lang,sec:t.section,hn:t.hn,ratio:t.ratio,src:t.source_available}))})), null, 0)}

Produce a report:
1. Summary table: book x total_truncated x has_backup_source x needs_LLM
2. Per book: which langs have the most truncations, which backup source has full text
3. The worst truncations (ratio<0.2) across all books — these are data-loss, not just short translations
4. Which truncations have a local scholarly source (recoverable) vs which need LLM re-translation
5. Recommended recovery: local_backup first (pull full text from alt/new/cache), then fawaz/tohed, then LLM for the rest
Return {report_md, total_truncated, recoverable_from_backup, needs_llm}.`,
  { label: 'synthesize-truncation', phase: 'Synthesize',
    schema: { type: 'object', properties: {
      report_md: { type: 'string' },
      total_truncated: { type: 'number' },
      recoverable_from_backup: { type: 'number' },
      needs_llm: { type: 'number' },
    }, required: ['report_md'] }, effort: 'max' })

return { books_scanned: results.length, results, report: synth.report_md, total: synth.total_truncated, backup: synth.recoverable_from_backup, llm: synth.needs_llm }
