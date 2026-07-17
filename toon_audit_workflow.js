export const meta = {
  name: 'toon-audit',
  description: 'Exhaustive content audit of all .toon hadith files — finders read real file bytes per edition, verify, critic, synthesize',
  phases: [
    { title: 'Find', detail: 'one finder per edition reads actual files, reports all issue kinds' },
    { title: 'Verify', detail: 'verify agent re-reads cited files, confirms/refutes each finding batch' },
    { title: 'Critic', detail: 'completeness critic — what issue categories were missed' },
    { title: 'Synthesize', detail: 'merge all confirmed findings into ranked report' },
  ],
}

const EDITIONS_DIR = '/home/saboor/code/hadith-api-toon/editions'

const EDITIONS = [
  'abdurrazzaq','abudawud','aladab-almufrad','bayhaqi','bukhari','bulugh-al-maram',
  'dehlawi','fath-al-rabbani','hisn','ibnhibban','ibnmajah','lulu-wal-marjan',
  'malik','mishkat','muajam-tabarani-saghir','musannaf-ibn-abi-shaybah','muslim',
  'musnad-ahmad','mustadrak','nasai','nasai-kubra','nawawi','qudsi','riyadussalihin',
  'sahih-ibn-khuzaymah','shamail-tirmidhi','silsila-sahih','sunan-al-daraqutni',
  'sunan-darimi','tirmidhi','virtues'
]

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    edition: { type: 'string' },
    files_read: { type: 'number', description: 'how many .toon files the agent actually opened and read' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          kind: { type: 'string', description: 'short snake_case category, e.g. ai_leakage, script_mismatch, header_count_mismatch, empty_field, dup_text, placeholder, leading_ordinal, markdown_residue, mojibake, orphan_line, odd_quote, field_count_mismatch, info_total_mismatch, info_lang_mismatch, metadata_malformed, section_gap, numbering_gap, bad_hadith_number, empty_grades, empty_reference, empty_arabic, very_short_text, dup_hadith_number, bom, crlf, other' },
          file: { type: 'string', description: 'repo-relative path, e.g. bukhari/sections/1.toon' },
          line: { type: 'integer', description: '1-indexed line number, 0 if file-level' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          summary: { type: 'string', description: 'one-line problem statement' },
          evidence: { type: 'string', description: 'exact snippet of offending text/metadata, <=200 chars' },
        },
        required: ['kind', 'file', 'severity', 'summary', 'evidence'],
      },
    },
    notes: { type: 'string', description: 'any caveats, patterns observed, or issue categories that appeared systemic' },
  },
  required: ['edition', 'files_read', 'findings', 'notes'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    edition: { type: 'string' },
    confirmed: { type: 'array', items: {
      type: 'object',
      properties: {
        kind: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
        severity: { type: 'string' }, summary: { type: 'string' }, evidence: { type: 'string' },
        verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
        reason: { type: 'string', description: 'why confirmed/refuted, citing what was seen in the actual file' },
      },
      required: ['kind','file','severity','summary','verdict'],
    }},
    false_positive_count: { type: 'number' },
  },
  required: ['edition','confirmed','false_positive_count'],
}

phase('Find')
log(`Auditing ${EDITIONS.length} editions under ${EDITIONS_DIR}`)

const FIND_CHECKLIST = `You are auditing a hadith-text repository in a custom ".toon" CSV-ish format.
READ ACTUAL FILE CONTENTS WITH YOUR READ TOOL — do not guess or rely on assumptions. Open the files directly.

FORMAT:
- info.toon (per edition root): starts with "metadata:" block (book_id, book_name, total_hadiths, available_languages, intro) then a header like "translations[N]{language,sections,path}:" listing language rows.
- sections/<N>.toon: AR source. Header "hadiths[count]{hadithnumber,arabic,grades,reference,international_number,narrator_chain,chapter_intro}:" then rows: "1","<arabic>","<grades>","<reference>","<intl#>","<chain>","<chapter_intro>"
- translations/<lang>/sections/<N>.toon: translation. Header "hadiths[N]{hadithnumber,text}:" then rows: "1","<translated text>"
- translations/<lang>/metadata.toon: per-language section index, header "sections[N]{...}"

INSPECT THIS EDITION'S FILES. You need not read every file exhaustively, but READ A REAL SAMPLE:
1. Read the edition's info.toon fully.
2. Read every translations/*/metadata.toon fully.
3. Read several section files per language (read at least 8-12 real section files total, spread across languages, including AR source sections). For very large editions (sahih-ibn-khuzaymah, musnad-ahmad, bukhari, muslim, nasai) read 15-20 files.
4. Sample from the START, MIDDLE, and END of the section range — do not only read section 1.

HUNT ALL THESE ISSUE KINDS by reading real content (report each with file, line if known, severity, exact evidence snippet):
- header_count_mismatch: header hadiths[N] vs actual row count (count the rows).
- count_literal: header uses [count] instead of a real number.
- orphan_line / odd_quote: stray non-data lines after header; odd number of double-quotes on a row.
- field_count_mismatch: a row has wrong number of quoted fields for its schema (2 for translations, 7 for AR source).
- empty_arabic / empty_grades / empty_reference / empty_intl_number / empty_chapter_intro: AR source has an empty field where data expected.
- empty_text / very_short_text: translation text empty or <15 chars.
- placeholder: text like "??", "N/A", "TODO", "PLACEHOLDER", "lorem ipsum", "----".
- leading_ordinal: translation text redundantly begins with the hadith number ("6.", "৬.", "(6)") before the real text.
- markdown_residue: **bold**, [link](url), # heading, - bullets, backticks left in text.
- mojibake / bom / crlf: U+FFFD replacement chars, UTF-8 BOM, CRLF endings.
- script_mismatch: translation language vs dominant script of its text (e.g. ur field full of Latin, en field full of Arabic, bn field full of Devanagari).
- dup_text_in_section: same hadith text repeated for different hadith numbers in one file.
- dup_hadith_number: same hadith number used twice in one file.
- numbering_gap: hadith numbers non-sequential / skipping within a file.
- section_gap: missing section file numbers in a directory's range.
- info_total_mismatch: info.toon total_hadiths far from actual count (sum rows across AR source sections, or compare to section count).
- info_lang_mismatch: available_languages lists langs not present as translation dirs, or present dirs not listed.
- metadata_malformed: a metadata.toon missing, broken header, or section-count mismatch with actual files.
- ai_leakage: leftover AI phrasing in translations ("Here is the translation", "Note:", "Translation:", "Sure,", "As an AI", "I apologize", "please note", "let me know", "in summary").
- narrator_chain / chapter_intro anomalies in AR sources.
- anything else genuinely wrong you observe by reading real bytes.

Be rigorous and specific. Every finding MUST cite a real file path and a real evidence snippet you actually saw. Do NOT invent findings. If you read a file and it is clean, report no findings for it. Return findings only for things you directly observed in file contents.`

const VERIFY_PROMPT = (edition, findingsJson) => `You are adversarially verifying audit findings for edition "${edition}" in the hadith .toon repo at ${EDITIONS_DIR}.
A finder agent reported these findings (JSON):
${findingsJson}

For EACH finding, OPEN THE CITED FILE with your Read tool and check whether the claimed problem actually exists in the real file content. Default to "refuted" if the evidence does not match what is actually in the file, or if the finding is a false positive (e.g. the field legitimately allows that value, or the "markdown" is actually a valid hadith punctuation mark, or the "ai_leakage" word is part of normal religious text).

Mark verdict: confirmed (problem real and you saw it), refuted (not real / false positive), uncertain (file unreadable or genuinely ambiguous).
For each, give a one-line reason citing what you actually saw in the file.

Return the verified findings. Drop refuted ones from the "confirmed" array (only include confirmed + uncertain in that array), and report false_positive_count = number refuted.`

// Run finders in small calm batches to avoid flooding the inference gateway (16-wide
// concurrency triggers 503 auth_unavailable under load). 4-wide + per-agent retry.
// ponytail: global concurrency ceiling of 4; raise only if gateway headroom is confirmed.
const BATCH = 4

async function agentWithRetry(prompt, opts, tries = 5) {
  for (let t = 1; t <= tries; t++) {
    const r = await agent(prompt, opts)
    if (r) return r
    log(`retry ${t}/${tries} for ${opts.label || '(agent)'} (null/503 result)`)
  }
  return null
}

async function findVerifyOne(ed) {
  const res = await agentWithRetry(
    `${FIND_CHECKLIST}\n\n=== YOUR EDITION: ${ed} ===\nDirectory: ${EDITIONS_DIR}/${ed}\nRead the real files in that directory tree now. Return structured findings.`,
    { label: `find:${ed}`, phase: 'Find', schema: FINDINGS_SCHEMA, effort: 'high' }
  )
  if (!res) return null
  const fj = JSON.stringify(res.findings || [], null, 1)
  const v = await agentWithRetry(VERIFY_PROMPT(ed, fj),
    { label: `verify:${ed}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' })
  return { edition: ed, files_read: res.files_read, finder_notes: res.notes, verify: v }
}

const finderResults = []
for (let i = 0; i < EDITIONS.length; i += BATCH) {
  const batch = EDITIONS.slice(i, i + BATCH)
  log(`Find batch ${Math.floor(i / BATCH) + 1}: ${batch.join(', ')}`)
  const out = await parallel(batch.map(ed => () => findVerifyOne(ed)))
  for (const o of out) if (o) finderResults.push(o)
  log(`Find+Verify cumulative: ${finderResults.length}/${EDITIONS.length}`)
}

const valid = finderResults.filter(Boolean)
log(`Find+Verify done for ${valid.length}/${EDITIONS.length} editions`)

// Aggregate confirmed findings
const allConfirmed = []
let totalFilesRead = 0
for (const v of valid) {
  totalFilesRead += (v.files_read || 0)
  const conf = (v.verify && v.verify.confirmed) || []
  for (const c of conf) {
    if (c.verdict === 'refuted') continue
    allConfirmed.push({ edition: v.edition, ...c, finder_notes: v.finder_notes })
  }
}
log(`Confirmed (incl uncertain) findings: ${allConfirmed.length}; files read by finders: ${totalFilesRead}`)

phase('Critic')
const criticPrompt = `You are a completeness critic for a hadith-text .toon repository audit at ${EDITIONS_DIR}.
The audit used finder agents (one per edition, 31 editions) who read real file contents, then a verify agent re-read cited files.

Confirmed findings aggregated (JSON, may be large):
${JSON.stringify(allConfirmed.slice(0, 400), null, 0)}

Edition finder notes:
${JSON.stringify(valid.map(v => ({ ed: v.edition, notes: v.finder_notes })), null, 0)}

Identify what is MISSING or UNDER-COVERED:
- Issue categories that likely exist in such a dataset but were not reported at all (e.g. cross-language inconsistencies, narrator-chain corruption, duplicate hadiths ACROSS sections, intro metadata drift, reference format inconsistencies, grade values outside canonical set, broken unicode normalization, mixed LTR/RTL, trailing metadata after rows).
- Editions that look under-audited (files_read suspiciously low).
- Any systemic risk the finders might have a false-negative on (read only section 1).
Do NOT re-audit; just list the gaps as concrete follow-up checks, each with the specific thing to look for and why it matters. Be specific and technical.`

const critic = await agent(criticPrompt, {
  label: 'completeness-critic',
  phase: 'Critic',
  schema: {
    type: 'object',
    properties: {
      missed_categories: { type: 'array', items: { type: 'object', properties: {
        category: { type: 'string' }, what_to_look_for: { type: 'string' }, why_it_matters: { type: 'string' },
      }, required: ['category','what_to_look_for'] } },
      under_audited_editions: { type: 'array', items: { type: 'string' } },
      systemic_risks: { type: 'array', items: { type: 'string' } },
    },
    required: ['missed_categories'],
  },
  effort: 'high',
})

// Optional: a second targeted find pass for the top missed categories, reading real files.
phase('Find-Two')
const topGaps = (critic.missed_categories || []).slice(0, 6)
let gapFollowup = []
if (topGaps.length) {
  const gapBatches = topGaps.map((g, i) => `GAP ${i+1}: ${g.category} — ${g.what_to_look_for}`)
  // split editions into 3 groups, each agent reads real files for a few editions hunting these gap categories
  const groups = [[], [], []]
  EDITIONS.forEach((e, i) => groups[i % 3].push(e))
  gapFollowup = await parallel(groups.map((grp, gi) => () => agent(
    `You are doing a TARGETED second-pass audit of the hadith .toon repo at ${EDITIONS_DIR}.\n` +
    `Hunt ONLY these missed issue categories by reading REAL file contents (use your Read tool on actual .toon files in these editions: ${grp.join(', ')}):\n` +
    gapBatches.join('\n') +
    `\nRead at least 6 real section files per category, spread across the editions above. Report findings with the same schema: kind (use the gap category name as kind), file, line, severity, summary, evidence (real snippet). Only report what you directly observe in file bytes. Return {edition, files_read, findings[], notes}.`,
    { label: `gapfind-${gi}`, phase: 'Find-Two', schema: FINDINGS_SCHEMA, effort: 'high' }
  ))).then(rs => rs.filter(Boolean))
  // verify the gap followup lightly
  const gapAll = []
  for (const r of gapFollowup) for (const f of (r.findings || [])) gapAll.push({ edition: r.edition, ...f })
  log(`Gap followup found ${gapAll.length} candidate findings; verifying`)
  if (gapAll.length) {
    const verified = await agent(`Verify these second-pass findings by reading the cited real files at ${EDITIONS_DIR}. JSON:\n${JSON.stringify(gapAll.slice(0,200))}\nReturn confirmed (verdict confirmed/uncertain) with reason, drop refuted. Count false positives.`, {
      label: 'gapverify', phase: 'Find-Two', schema: VERDICT_SCHEMA, effort: 'high' })
    if (verified && verified.confirmed) {
      for (const c of verified.confirmed) if (c.verdict !== 'refuted') allConfirmed.push(c)
    }
  }
}

phase('Synthesize')
const synthPrompt = `You are the synthesis agent for an exhaustive audit of the hadith .toon repository at ${EDITIONS_DIR}.
31 finder agents read real file contents (one per edition), each finding was adversarially re-verified by an agent that re-opened the cited file. Total files read by finders: ${totalFilesRead}.

Confirmed+uncertain findings (JSON):
${JSON.stringify(allConfirmed, null, 0)}

Completeness critic gaps:
${JSON.stringify(critic, null, 0)}

Produce a final report:
1. A ranked summary table of issue KINDS by count (most frequent first).
2. The MOST SEVERE findings (high severity) — list each with edition, file, line, summary, evidence.
3. Systemic patterns (editions or languages disproportionately affected).
4. False-positive / data-quality caveats from the verify pass (kinds that were often refuted and why — so the user knows which counts to trust).
5. The completeness gaps the critic flagged (what was likely missed and should get a follow-up audit).
6. A prioritized recommended-fix list (what to fix first).
Be precise. Cite real files. Do not inflate. If a kind had many refutations, say so. Return the report as a single markdown string in the "report" field.`

const synthesis = await agent(synthPrompt, {
  label: 'synthesize',
  phase: 'Synthesize',
  schema: { type: 'object', properties: {
    report: { type: 'string', description: 'full markdown audit report' },
    kind_counts: { type: 'array', items: { type: 'object', properties: {
      kind: { type: 'string' }, count: { type: 'number' }, severity: { type: 'string' } }, required: ['kind','count'] } },
  }, required: ['report'] },
  effort: 'max',
})

return {
  editions_audited: valid.length,
  total_files_read: totalFilesRead,
  confirmed_findings: allConfirmed.length,
  kind_counts: synthesis.kind_counts,
  critic_gaps: critic,
  report: synthesis.report,
}
