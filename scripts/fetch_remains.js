const fs = require('node:fs');

const targets = [
  { ref: 'abudawud:3014', key: 'abudawud:3014' },
  { ref: 'abudawud:1840', key: 'abudawud:1840' },
  { ref: 'abudawud:615', key: 'abudawud:615' },
  { ref: 'adab:646', key: 'adab:646' },
  { ref: 'lulu-marjan:1853', key: 'lulu-marjan:1853' },
  { ref: 'tirmidhi:3760', key: 'tirmidhi:3760' },
  { ref: 'muslim:596', key: 'muslim:1351' }, // Local Muslim 1351 is Arabic 596
  { ref: 'muslim:275', key: 'muslim:638' },  // Local Muslim 638 is Arabic 275
  { ref: 'muslim:598', key: 'muslim:1355' }, // Local Muslim 1355 is Arabic 598
  { ref: 'muslim:2935', key: 'muslim:7371' } // Local Muslim 7371 is Arabic 2935
];

const outPath = '/home/saboor/code/hadith-api-toon/scripts/cache/fetched_remains.json';

(async () => {
  const results = {};
  
  for (let i = 0; i < targets.length; i++) {
    const target = targets[i];
    const url = `https://hadithunlocked.com/${target.ref}`;
    console.log(`[${i + 1}/${targets.length}] Loading ${url}...`);
    
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      
      const data = await page.evaluate(() => {
        const article = document.querySelector("article.row");
        if (!article) return null;
        const columns = Array.from(article.querySelectorAll("section.col-md-6"));
        if (columns.length < 2) return null;
        
        const colEn = columns[0];
        const colAr = columns[1];
        
        const chainEn = colEn.querySelector(".chain")?.innerText.trim() || "";
        const bodyEn = colEn.querySelector(".hadith-body-content")?.innerText.trim() || "";
        const gradeEn = colEn.querySelector(".grade")?.innerText.trim() || "";
        
        const chainAr = colAr.querySelector(".chain")?.innerText.trim() || "";
        const bodyAr = colAr.querySelector(".hadith-body-content")?.innerText.trim() || "";
        const gradeAr = colAr.querySelector(".grade")?.innerText.trim() || "";
        
        return {
          arabic_body: bodyAr,
          arabic_chain: chainAr,
          english_body: bodyEn,
          english_chain: chainEn,
          grade: gradeAr,
          grade_en: gradeEn
        };
      });
      
      if (data) {
        results[target.key] = data;
        console.log(`  Success! Arabic body length: ${data.arabic_body.length}`);
      } else {
        console.log(`  Could not parse structure for ${target.ref}`);
      }
    } catch (err) {
      console.error(`  Error: ${err.message}`);
    }
    
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2), 'utf8');
  console.log(`Saved results to ${outPath}`);
})();
