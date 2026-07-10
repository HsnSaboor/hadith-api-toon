const fs = require('node:fs');
const path = require('node:path');

const toFetchPath = '/home/saboor/code/hadith-api-toon/scripts/cache/to_fetch.json';
const outPath = '/home/saboor/code/hadith-api-toon/scripts/cache/fetched_data.json';

if (!fs.existsSync(toFetchPath)) {
  console.error('to_fetch.json not found!');
  process.exit(1);
}

const items = JSON.parse(fs.readFileSync(toFetchPath, 'utf8'));
console.log(`Starting fetch of ${items.length} items...`);

const results = {};
for (let i = 0; i < items.length; i++) {
  const item = items[i];
  const ref = `${item.alias}:${item.hadithnumber}`;
  const url = `https://hadithunlocked.com/${ref}?json`;

  console.log(`[${i + 1}/${items.length}] Fetching ${ref}...`);
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const text = await page.evaluate(() => document.body.innerText);
    
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed) && parsed.length > 0) {
      results[ref] = {
        arabic_body: parsed[0].body,
        arabic_chain: parsed[0].chain,
        english_body: parsed[0].body_en,
        english_chain: parsed[0].chain_en,
        grade: parsed[0].grade_grade,
        grade_en: parsed[0].grade_grade_en
      };
      console.log(`  Success! Body length: ${parsed[0].body ? parsed[0].body.length : 0}`);
    } else {
      console.log(`  Empty or invalid response for ${ref}`);
    }
  } catch (err) {
    console.error(`  Error fetching ${ref}: ${err.message}`);
  }

  // Politeness delay
  await new Promise(resolve => setTimeout(resolve, 1500));
}

fs.writeFileSync(outPath, JSON.stringify(results, null, 2), 'utf8');
console.log(`Saved ${Object.keys(results).length} results to ${outPath}`);
