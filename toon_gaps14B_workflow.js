export const meta = {
  name: 'toon-gaps14-B',
  description: 'Phase B judgment fixes for gaps14 — per-instance agents fix structural defects (HN re-key, dups, column-shift, relocate), verify, document',
  phases: [
    { title: 'Fix', detail: 'one agent per judgment item, reads real file, applies fix, verifies' },
    { title: 'Verify', detail: 're-open fixed files, confirm no breakage' },
    { title: 'Document', detail: 'update KNOWN_ISSUES with intentional items' },
  ],
}
const REPO='/home/saboor/code/hadith-api-toon'
const ED=`${REPO}/editions`

const FIX_SCHEMA={type:'object',properties:{item_id:{type:'string'},files_changed:{type:'array',items:{type:'string'}},rows_fixed:{type:'number'},method:{type:'string'},verification:{type:'string'},issues_remaining:{type:'string'}},required:['item_id','files_changed','verification']}

const RULES=`You are fixing ONE structural defect in the hadith .toon repo at ${REPO}. Branch audit-fixes is checked out. Edit ONLY the files named in your item. Do NOT touch other editions, viewer.html, sunnah.js, or run git.

ABSOLUTE RULES:
- READ the cited file BEFORE editing. Use Edit/Write/Bash(python csv).
- Preserve toon CSV schema: translations = "hadithnumber","text" (2 fields); AR source = 7 fields. Escape inner double-quotes as "" (CSV standard). Update hadiths[N] header count to match actual rows.
- NEVER fabricate hadith content. If a row is genuinely missing text, leave empty + flag.
- After editing, re-Read the file to confirm: header valid, row count matches header N, no new field-count breakage.
- For CSV re-quoting: use python csv module with QUOTE_MINIMAL or manual escape (replace inner " with ""), NEVER string concat that breaks escaping.
- For duplicate removal: verify both rows are truly identical (same arabic + same HN) before deleting; keep one.`

const ITEMS=[
  { id:'B2-fath-dups', scope:`${RULES}
ITEM: fath-al-rabbani cross-section duplicates. Read editions/fath-al-rabbani/sections/2.toon and 3.toon. The audit found HN145 duplicated to 144, 153 to 152, 180 to 179 (within-section identical rows; source marker "۔ (۱۴۴، ۱۴۵)۔" suggests restructuring artifact).
Steps:
1. Read both files. Find rows where two adjacent HNs (144/145, 152/153, 179/180) have IDENTICAL arabic text.
2. If identical: delete the duplicate row (keep the lower HN), renumber subsequent rows? NO — HNs are hadith numbers, not sequence indices; do NOT renumber. Just delete the duplicate row.
3. If NOT identical (different text): do NOT delete — report as not-duplicate.
4. Update hadiths[N] header count to match remaining rows.
5. Verify: re-read, header count == row count.
Target: editions/fath-al-rabbani/sections/{2,3}.toon` },

  { id:'B2-muslim-dup7564', scope:`${RULES}
ITEM: muslim duplicate HN7564 in sections/0.toon. Read editions/muslim/sections/0.toon. Find all rows with hadithnumber "7564". If 2+ rows with identical arabic: delete duplicates keeping one. If different arabic: report (may be legit repeat-variant).
Steps: find "7564" rows, compare arabic, delete true duplicates, update header count. Verify.
Target: editions/muslim/sections/0.toon` },

  { id:'B3-sunan-darimi-quotes', scope:`${RULES}
ITEM: sunan-al-daraqutni... NO — sunan-darimi 34 rows with unescaped quotes (mixed escaped "" + bare " in arabic field causing 8-9 field split). Files: editions/sunan-darimi/sections/{0,1,2,5,11,12}.toon.
The defect: some rows have a bare " inside the arabic field (not escaped as ""), so csv split yields 8-9 fields instead of 7.
Steps:
1. For each flagged file, use python csv to RE-PARSE robustly: read raw line, find rows with !=7 fields via naive split, then re-quote: the arabic field (field 2) contains the bare " which should be escaped to "". Identify by: a row where naive split gives 8-9 fields AND fields 3-7 look like [grades, reference, intl, chain, chapter_intro].
2. Re-escape: replace the bare " inside the arabic field with "" (so the row has exactly 7 fields). Preserve grades/reference/intl/chain/chapter_intro from the tail fields.
3. CRITICAL: be careful — the bare " may be a quote MARK inside the hadith (like قال "..." ). Escape those to "". Do NOT delete any text.
4. Verify: every row in each fixed file parses to exactly 7 fields via csv.reader. Header count == row count.
Target: editions/sunan-darimi/sections/{0,1,2,5,11,12}.toon` },

  { id:'B3-mishkat-colshift', scope:`${RULES}
ITEM: mishkat column-shift — 12 rows across sections {0,4,5,7,9,10,11,13,23,25,26,29}.toon where chapter name is in wrong column (col5 instead of col6). Read one flagged file first to understand: the audit said "move chapter name col5→col6".
Steps:
1. Read editions/mishkat/sections/0.toon. Find a row that is structurally wrong vs a good 7-field row in the same file. Determine the exact column-shift (e.g., narrator_chain has chapter name, chapter_intro empty).
2. If the pattern is "field 5 (narrator_chain) contains the chapter name, field 6 (chapter_intro) empty": move content from field 5 to field 6, set field 5 to "".
3. Apply to all affected rows in all 12 files. Verify each fixed row has 7 fields and chapter_intro populated.
4. Header count unchanged (row count same).
Target: editions/mishkat/sections/{0,4,5,7,9,10,11,13,23,25,26,29}.toon` },

  { id:'B3-mustadrak-hn9', scope:`${RULES}
ITEM: mustadrak sections/1.toon HN9 has broken grade commentary. Read editions/mustadrak/sections/1.toon, find row "9". The grade field contains broken commentary text. Fix: if grade field has multi-sentence commentary, extract just the grade term (Sahih/Hasan/Daif/etc) and move commentary to reference or empty it. Verify 7 fields.
Target: editions/mustadrak/sections/1.toon` },

  { id:'B3-shamail-hn45', scope:`${RULES}
ITEM: shamail-tirmidhi sections/5.toon HN45 has arabic commentary in the grade field. Read editions/shamail-tirmidhi/sections/5.toon, find "45". If grade field (3rd) contains arabic commentary instead of a grade: move it to reference field (4th) or chapter_intro (7th) if appropriate, set grade to "" or the canonical grade. Verify 7 fields.
Target: editions/shamail-tirmidhi/sections/5.toon` },

  { id:'B1-ibnhibban-sec0', scope:`${RULES}
ITEM: ibnhibban section 0 EN HN misalignment. AR sections/0.toon uses range-encoding (HN like "2 : 499", "12 : 196"), EN translations/en/sections/0.toon uses single numbers (0,22,23...). UR translations/ur/sections/0.toon already matches AR.
Steps:
1. Read editions/ibnhibban/sections/0.toon (AR) — note the HN column values (range-encoded).
2. Read editions/ibnhibban/translations/ur/sections/0.toon (UR) — confirm it matches AR HN column.
3. Read editions/ibnhibban/translations/en/sections/0.toon (EN) — it has different HNs.
4. Re-key EN: the EN hadithnumber column should match the AR/UR HN column (the range-encoded strings). Map EN rows to AR rows by POSITION (row k in EN = row k in AR), set EN HN = AR HN. Preserve EN text.
5. Update EN header hadiths[N] (count unchanged). Verify: EN HN list == AR HN list (same order).
Target: editions/ibnhibban/translations/en/sections/0.toon` },

  { id:'B1-nasai-id-missing', scope:`${RULES}
ITEM: nasai id section 36 missing HN3945, 3965. editions/nasai/translations/id/sections/36.toon has 25 rows (AR/en/ur/bn/fr have 27). HN 3945 and 3965 absent in id.
Steps:
1. Read editions/nasai/sections/36.toon (AR) to get arabic text for HN3945 and 3965.
2. Use the local glm-5-2 gateway (localhost:8317/v1/chat/completions, model databricks-glm/glm-5-2, key sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh, no max_tokens) to translate each arabic to Indonesian (Bahasa Indonesia). Prompt: "Translate this Arabic hadith into Indonesian faithfully. No commentary. Output only the translation."
3. Insert as new rows in editions/nasai/translations/id/sections/36.toon at the correct positions (between existing rows to keep HN order), prefixed "[AI-translation] ". Update header hadiths[27].
4. Verify: 27 rows, HN order 3939-3965 contiguous.
Target: editions/nasai/translations/id/sections/36.toon` },
]

phase('Fix')
log(`Fixing ${ITEMS.length} judgment items`)
async function retry(p,o,t=5){for(let i=1;i<=t;i++){const r=await agent(p,o);if(r)return r;log(`retry ${i}/${t} ${o.label}`)}return null}
const results=[]
const BATCH=3
for(let i=0;i<ITEMS.length;i+=BATCH){
  const b=ITEMS.slice(i,i+BATCH)
  log(`Fix batch ${Math.floor(i/BATCH)+1}: ${b.map(x=>x.id).join(', ')}`)
  const out=await parallel(b.map(it=>()=>retry(it.scope,{label:`fix:${it.id}`,phase:'Fix',schema:FIX_SCHEMA,effort:'high'})))
  for(const o of out) if(o) results.push(o)
  log(`Fix cumulative ${results.length}/${ITEMS.length}`)
}

phase('Verify')
const verify=await agent(`Verify gaps14-B fixes. For each item, re-open the cited files and confirm the fix landed + no new breakage (header valid, row count matches, field counts correct).
Results: ${JSON.stringify(results,null,0)}
Run via Bash: header invariant check on all changed files. Report {summary, passed:[], failed:[], new_breakage:[]}.`,
  {label:'verify-B',phase:'Verify',schema:{type:'object',properties:{summary:{type:'string'},passed:{type:'array',items:{type:'string'}},failed:{type:'array',items:{type:'string'}},new_breakage:{type:'array',items:{type:'string'}}},required:['summary','passed','failed']},effort:'high'})

phase('Document')
const doc=await agent(`Update ${REPO}/KNOWN_ISSUES.md: append a "GAPS14-B status" section documenting what was fixed (malik HN163502, fath dups, muslim dup7564, sunan-darimi quotes, mishkat colshift, mustadrak HN9, shamail HN45, ibnhibban sec0 re-key, nasai id sec36) and what remains (bukhari compound mapping, mustadrak en orphan rows, intros, C phase). Read current KNOWN_ISSUES first, append (don't rewrite). Do NOT run git. Return {summary}.`,
  {label:'document-B',phase:'Document',schema:{type:'object',properties:{summary:{type:'string'}},required:['summary']},effort:'medium'})

return {items_fixed:results.length,results,verify_summary:verify&&verify.summary,doc_summary:doc&&doc.summary}
