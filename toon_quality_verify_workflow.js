export const meta = {
  name: 'toon-source-quality-verify',
  description: 'Verify whether recovery sources (tohed ibnhibban EN, local nasai caches, fawaz FR/BN) carry real scholarly translations vs machine/AI slop',
  phases: [
    { title: 'Verify', detail: 'fetch real text per source, judge scholarly vs machine, compare to known reference' },
    { title: 'Synthesize', detail: 'per-source quality verdict + updated plan' },
  ],
}
const REPO='/home/saboor/code/hadith-api-toon'
const HOME='/home/saboor/code/hadith-api-toon'

phase('Verify')

const SCHOLARLY_CONTEXT = `You are verifying whether a hadith source carries REAL SCHOLARLY human translations or machine/AI-generated slop. This is critical: the repo refuses hadithunlocked.com because its translations are Google/machine-translated with [AI] prefix. We must NOT replace corrupt rows with more corrupt/AI text.

Signs of SCHOLARLY (human, trustworthy) translation:
- Formal, consistent hadith register ("It was narrated from X that the Messenger of Allah said: ...", "X reported that Allah's Messenger said:")
- Proper-noun transliteration conventions (Shu'ba, Abu Huraira, Ibn 'Abbas, 'Aisha with ayn-backticks)
- Chain-of-narrators (isnad) rendered in academic style
- English matched to the Arabic (same hadith, correct meaning)
- Matches well-known scholarly editions: Darussalam/Tahawi/English translations by Khan, Shakir, etc.
- No AI markers ("Here is", "Sure", "I apologize", "Translation:", "[AI]", "Voici", "Note:", meta-commentary)

Signs of MACHINE/AI slop:
- Awkward literal renderings, wrong idiom, missing honorifics
- Prefaces ("Here is the translation", "Translation:", "[AI]")
- Inconsistent transliteration, garbled names
- Over-fluent generic prose that loses hadith structure
- Identical to known Google-translate artifacts
- Repetition artifacts

For Arabic-source side checks: confirm the Arabic is real classical hadith text (not broken/garbled), not needed to judge the translation language quality unless asked.

You have Read and WebFetch. READ local files; WebFetch live URLs. Quote REAL text you observed, do not guess.`

const VERIFY_SCHEMA = {
  type:'object', properties:{
    source:{type:'string'},
    items:{type:'array', items:{type:'object', properties:{
      hadith_id:{type:'string'},
      fetched_text:{type:'string', description:'actual text you observed (<=800 chars)'},
      scholarly_verdict:{type:'string', enum:['scholarly','likely_scholarly','machine_slop','ai_slop','mixed','unclear']},
      evidence:{type:'string', description:'why you judged this — cite the specific phrasing/transliteration/markers'},
      known_reference_match:{type:'string', description:'if you recognize this hadith from a known scholarly edition (Khan/Shakir/etc), name it + how it matches'},
      recommendation:{type:'string', enum:['use','verify_more','reject','use_with_marker']},
    }, required:['hadith_id','fetched_text','scholarly_verdict','evidence','recommendation']}},
    overall_verdict:{type:'string', enum:['scholarly','likely_scholarly','machine_slop','ai_slop','mixed','unclear']},
    summary:{type:'string'},
  }, required:['source','items','overall_verdict','summary'],
}

const TASKS = [
  {
    source:'tohed.com — ibnhibban EN',
    prompt:`${SCHOLARLY_CONTEXT}

Verify the English translations on tohed.com for Ibn Hibban. Fetch these URLs with WebFetch and extract the actual English hadith text (the rendered translation body, not page chrome):
- https://en.tohed.com/hadith/sahih-ibn-hibban/1139/
- https://en.tohed.com/hadith/sahih-ibn-hibban/3610/
- https://en.tohed.com/hadith/sahih-ibn-hibban/5690/
- https://en.tohed.com/hadith/sahih-ibn-hibban/7174/
- https://en.tohed.com/hadith/sahih-ibn-hibban/1517/

For each, ask WebFetch to "return the full English translation of this hadith, verbatim, including the chain of narrators if present." Then judge scholarly vs machine/AI. Note if tohed appears to source its EN from a known edition (e.g. Shuaib Karim / Darussalam / sunnah.com's Khan & Hilali). Quote what you actually got.`,
  },
  {
    source:'tohed.com — musannaf-ibn-abi-shaybah UR (for HN 5898, 22496)',
    prompt:`${SCHOLARLY_CONTEXT}

Verify tohed.com Urdu translations for Musannaf Ibn Abi Shaybah (needed for HN 5898 and 22496). Fetch with WebFetch, extract the Urdu hadith body verbatim:
- https://en.tohed.com/hadith/musannaf-ibn-abi-shaybah/5898/
- https://en.tohed.com/hadith/musannaf-ibn-abi-shaybah/22496/

Judge whether the Urdu is a real scholarly Urdu tahriri translation (academic, consistent, proper isnad) or machine/AI slop. Quote actual text. Note any AI markers.`,
  },
  {
    source:'LOCAL nasai caches — scripts/cache/*-nasai.min.json (for sec36, 9 langs)',
    prompt:`${SCHOLARLY_CONTEXT}

Verify the quality of local fawaz caches for Nasai (needed to rebuild section 36). These are at /home/saboor/code/hadith-api-toon/scripts/cache/:
- ara-nasai.min.json (Arabic source)
- eng-nasai.min.json (English — likely Khan/Darussalam)
- fra-nasai.min.json (French)
- urd-nasai.min.json (Urdu)
- ben-nasai.min.json (Bengali)
- tur-nasai.min.json (Turkish)
- ind-nasai.min.json (Indonesian)
- rus-nasai.min.json (Russian)
Check if tam-nasai (Tamil) exists too.

For each language present: READ the JSON, find hadiths in the section-36 HN range (~3857-3965 — confirm exact range by scanning hadithNumbers around there), extract 2-3 actual text samples, and judge scholarly vs machine/AI. The English especially: does it match the known Darussalam/Khan Sunan an-Nasa'i translation? Quote real text. Report overall verdict per language.`,
  },
  {
    source:'LOCAL fawaz fra-ibnmajah + ben-abudawud (for items 3,10)',
    prompt:`${SCHOLARLY_CONTEXT}

Verify quality of local fawaz caches used for ibnmajah FR (item 3) and abudawud BN (item 10):
- /home/saboor/code/hadith-api-toon/scripts/cache/fra-ibnmajah.min.json — READ, find HN 597, 1311, 4316, quote actual French text. Judge: is this a real scholarly French hadith translation (e.g. from a published French edition) or machine/AI? French scholarly hadith translations use formal register ("Le Messager d'Allah a dit", "D'après..."), proper transliteration.
- /home/saboor/code/hadith-api-toon/scripts/cache/ben-abudawud.min.json — READ, find HN 4588 (and a couple neighbors), quote actual Bengali text. Judge: scholarly Bengali (Tafseer/eTranslate academic style, proper Islamic Bengali register) vs machine/AI.

Quote real text. Note if fawaz credits a source/translator in metadata (read top of JSON for 'source'/'translator' fields).`,
  },
]

const out=[]
const BATCH=2
for(let i=0;i<TASKS.length;i+=BATCH){
  const b=TASKS.slice(i,i+BATCH)
  log(`Verify batch ${Math.floor(i/BATCH)+1}: ${b.map(x=>x.source).join(' | ')}`)
  const r=await parallel(b.map(t=>()=>agent(t.prompt,{label:`verify:${t.source.slice(0,20)}`,phase:'Verify',schema:VERIFY_SCHEMA,effort:'high'})))
  for(const x of r) if(x) out.push(x)
  log(`Verify cumulative ${out.length}/${TASKS.length}`)
}

phase('Synthesize')
const synth=await agent(`You are writing an UPDATED source-recovery plan section based on QUALITY VERIFICATION results. The user wants to know: do the proposed recovery sources carry REAL scholarly translations or machine/AI slop?

Verification results (JSON):
${JSON.stringify(out,null,0)}

Produce:
1. A per-source quality verdict table: source → verdict (scholarly/likely_scholarly/mixed/machine_slop/ai_slop) → evidence → keep/replace/LLM-only.
2. For tohed.com specifically: is its English/Ibn Hibban content a scholarly human translation or machine-translated? Cite the evidence.
3. For local nasai caches: per-language verdict — which langs are scholarly, which are machine.
4. Which sources are now CONFIRMED safe to use, which need an LLM fallback instead (because machine/AI), which need a different scholarly source.
5. An updated recommendation for the recovery plan: if tohed EN is machine → ibnhibban EN may need LLM or a different scholarly source (check if sunnah.com/darussalam has ibnhibban EN — it does NOT list ibnhibban; so options: accept LLM, or find another scholarly source, or leave documented-missing). Be honest about tradeoffs.
Return { updated_section_md: "<markdown to append to SOURCE_RECOVERY_PLAN.md as a quality verdict + plan update>", safe_sources:[...], unsafe_sources:[...], llm_needed:[...] }.`,
  {label:'synthesize-quality',phase:'Synthesize',schema:{type:'object',properties:{updated_section_md:{type:'string'},safe_sources:{type:'array',items:{type:'string'}},unsafe_sources:{type:'array',items:{type:'string'}},llm_needed:{type:'array',items:{type:'string'}}},required:['updated_section_md']},effort:'max'})

return { verified: out.length, results: out, updated_section_md: synth.updated_section_md, safe_sources: synth.safe_sources, unsafe_sources: synth.unsafe_sources, llm_needed: synth.llm_needed }
