export const meta = {
  name: 'toon-gaps14',
  description: 'Investigate + verify all 14 completeness gaps by reading real files per edition; classify real-fix vs intentional vs already-fixed; produce audit + fix plan',
  phases: [
    { title: 'Investigate', detail: 'one agent per edition reads real files, reports findings for each of the 14 gap categories' },
    { title: 'Verify', detail: 'cross-check real-fix candidates against external source (sunnah/tohed/fawaz) + re-open cited files' },
    { title: 'Synthesize', detail: 'merge into verified audit + per-item fix plan' },
  ],
}

const REPO = '/home/saboor/code/hadith-api-toon'
const ED = `${REPO}/editions`

const EDITIONS = [
  'abdurrazzaq','abudawud','aladab-almufrad','bayhaqi','bukhari','bulugh-al-maram',
  'dehlawi','fath-al-rabbani','hisn','ibnhibban','ibnmajah','lulu-wal-marjan',
  'malik','mishkat','muajam-tabarani-saghir','musannaf-ibn-abi-shaybah','muslim',
  'musnad-ahmad','mustadrak','nasai','nasai-kubra','nawawi','qudsi','riyadussalihin',
  'sahih-ibn-khuzaymah','shamail-tirmidhi','silsila-sahih','sunan-al-daraqutni',
  'sunan-darimi','tirmidhi','virtues'
]

const FIND_SCHEMA = {
  type:'object', properties:{
    edition:{type:'string'},
    files_read:{type:'number'},
    gaps:{type:'array', items:{type:'object', properties:{
      gap:{type:'integer', description:'1-14 gap number'},
      present:{type:'boolean', description:'does this gap exist in this edition'},
      severity:{type:'string', enum:['high','medium','low','none']},
      classification:{type:'string', enum:['real_fix_needed','intentional','already_fixed','false_positive','needs_external_verify']},
      locations:{type:'array', items:{type:'string'}, description:'file:line or HN ranges, real'},
      evidence:{type:'string', description:'real bytes you observed by reading files'},
      fix:{type:'string', description:'exact fix or "document as intentional"'},
    }, required:['gap','present','classification','evidence']}},
    notes:{type:'string'},
  }, required:['edition','files_read','gaps','notes'],
}

const GAPS_DESC = `The 14 completeness gaps from the audit. For EACH, investigate by reading REAL files in this edition:

#1 cross_language_hadith_number_alignment: per-section, diff ordered HN list AR sections/N.toon vs each translations/<lang>/sections/N.toon. Flag where row k HN differs.
#2 cross_section_duplicate_hadith_text: identical Arabic across different section files (legit cross-chapter repetition vs misfile).
#3 info_toon_sections_index_vs_actual_bounds: info.toon sections[] index hadith_first/hadith_last vs actual section file first/last HN.
#4 section_boundary_numbering_continuity: last_HN(sec N)+1 != first_HN(sec N+1), gap not in info index.
#5 bidi_control_characters: U+200E/F, U+202A-E, U+2066-69 in data fields.
#6 unicode_normalization_nfc_nfd: content not in NFC form (unicodedata.normalize('NFC',s)!=s).
#7 intro_script_consistency: info.toon intro_<lang> wrong-script, runaway loops, truncation.
#8 schema_ld_or_json_leakage: mainEntityOfPage/@type/en.tohed/al-hadees in hadith rows (not metadata).
#9 non_numeric_hadith_numbers: HN like "1132b","75a","348a","12/13" (letter-suffix/range).
#10 trailing_scraping_residue: "Sahih X Hadees: N Arabic Hadees: M","Hadith arabe :","شمائل ترمذی حدیث:" appended to translation text.
#11 grade_value_canonicalization: grades outside canonical set; leading ":" ("[مرسل صحيح","No Data Available").
#12 count_literal_header: "hadiths[count]" instead of real row count.
#13 metadata_toon_sections_header: translations/<lang>/metadata.toon lacks "sections[" header.
#14 narrator_chain_content_validity: narrator_chain field (where populated) is numeric/garbage instead of isnad names.`

phase('Investigate')
log(`Investigating 14 gaps across ${EDITIONS.length} editions`)

async function retry(p,o,t=5){ for(let i=1;i<=t;i++){ const r=await agent(p,o); if(r) return r; log(`retry ${i}/${t} ${o.label}`);} return null }

const results=[]
const BATCH=4
for(let i=0;i<EDITIONS.length;i+=BATCH){
  const b=EDITIONS.slice(i,i+BATCH)
  log(`Investigate batch ${Math.floor(i/BATCH)+1}: ${b.join(', ')}`)
  const out=await parallel(b.map(ed=>()=>retry(
    `${GAPS_DESC}\n\n=== YOUR EDITION: ${ed} ===\nRead REAL files under ${ED}/${ed} (info.toon, several sections, several translations). Use Bash for greps/python scans, Read for file inspection. For EACH of the 14 gaps, report present/classification/severity/locations/evidence/fix. Be rigorous — quote real bytes. If a gap is NOT present in this edition, mark present:false, classification:already_fixed or false_positive. If present but intentional (e.g. bukhari repeat-variant HN, cross-chapter hadith repetition), mark intentional. If a real defect, mark real_fix_needed with exact fix. Return structured findings.`,
    {label:`inv:${ed}`, phase:'Investigate', schema:FIND_SCHEMA, effort:'high'}
  )))
  for(const o of out) if(o) results.push(o)
  log(`Investigate cumulative ${results.length}/${EDITIONS.length}`)
}

// Aggregate real-fix candidates
const realFixes=[]
for(const r of results){
  for(const g of r.gaps||[]){
    if(g.classification==='real_fix_needed'||g.classification==='needs_external_verify'){
      realFixes.push({edition:r.edition, gap:g.gap, severity:g.severity, locations:g.locations, evidence:g.evidence, fix:g.fix, classification:g.classification})
    }
  }
}
log(`Real-fix candidates: ${realFixes.length}`)

phase('Verify')
// Verify the top real-fix candidates by re-opening cited files + cross-checking external source
const verifyTargets = realFixes.slice(0, 40)
// Build verify batches correctly:
const VB=[]
for(let i=0;i<verifyTargets.length;i+=8) VB.push(verifyTargets.slice(i,i+8))
const vres=[]
for(const batch of VB){
  const out=await parallel(batch.map(t=>()=>agent(
    `Verify this audit finding by reading the cited real files at ${ED} and (if needed) fetching an external source (sunnah.com ajax/tohed.com/fawazahmed0 CDN via curl) to confirm. JSON:\n${JSON.stringify(t)}\nReturn {gap,edition,verdict:'confirmed'|'refuted'|'uncertain',reason,fix_confirmed}. Default refuted if the cited file doesn't actually contain the claimed defect.`,
    {label:`verify:${t.edition}-${t.gap}`, phase:'Verify', schema:{type:'object',properties:{gap:{type:'integer'},edition:{type:'string'},verdict:{type:'string'},reason:{type:'string'},fix_confirmed:{type:'string'}},required:['gap','edition','verdict','reason']}, effort:'high'}
  )))
  for(const o of out) if(o) vres.push(o)
}

phase('Synthesize')
const synth=await agent(`You are producing the FINAL verified audit + fix plan for the 14 completeness gaps in the hadith .toon repo at ${REPO}. 31 finder agents read real files per edition; real-fix candidates were re-verified by agents that re-opened cited files + checked external sources.

Investigation results (per-edition, JSON):
${JSON.stringify(results.map(r=>({edition:r.edition,gaps:r.gaps})),null,0)}

Verify results (real-fix candidates):
${JSON.stringify(vres,null,0)}

Produce a markdown report:
1. Per-gap (1-14) verified status: present count, classification breakdown (real_fix/intentional/already_fixed/false_positive/needs_external), total files affected, confirmed-real fix needed.
2. For each CONFIRMED real-fix gap: the exact fix (file-level or batch), risk, and whether mechanical or judgment.
3. The "document as intentional" list (gap + which editions + why legit).
4. The "already fixed / false positive" list.
5. A prioritized execution plan (mechanical safe fixes first, then judgment, then document).
6. Notes on NFC normalization (#6, 3373 files) — risk assessment for repo-wide NFC.
Be precise. Cite real files. Return {report_md, confirmed_fixes:[{gap,files,fix_type}], intentional:[{gap,editions}], already_done:[{gap,editions}]}.`,
  {label:'synthesize-gaps', phase:'Synthesize',
    schema:{type:'object',properties:{report_md:{type:'string'},confirmed_fixes:{type:'array',items:{type:'object'}},intentional:{type:'array',items:{type:'object'}},already_done:{type:'array',items:{type:'object'}}},required:['report_md']}, effort:'max'})

return { editions_investigated: results.length, real_fix_candidates: realFixes.length, verified: vres.length, report_md: synth.report_md, confirmed_fixes: synth.confirmed_fixes, intentional: synth.intentional, already_done: synth.already_done }
