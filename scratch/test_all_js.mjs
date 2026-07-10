// ============================================================
// TEST 1: README.md — Step 1: Load the book index
// ============================================================
console.log("=== TEST 1: Load book index (README Step 1) ===");

function parseToonLine(line) {
  const result = [];
  let current = '', inQuotes = false, i = 0;
  while (i < line.length) {
    const char = line[i];
    if (inQuotes) {
      if (char === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') { current += '"'; i += 2; }
        else { inQuotes = false; i++; }
      } else { current += char; i++; }
    } else {
      if (char === '"') { inQuotes = true; i++; }
      else if (char === ',') { result.push(current); current = ''; i++; }
      else { char !== '\r' ? current += char : null; i++; }
    }
  }
  result.push(current);
  return result;
}

const response = await fetch('https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon');
const text = await response.text();
const lines = text.split('\n').filter(l => l.trim());

const header = lines[0];
const cols = header.match(/\{(.+)\}/)[1].split(',').map(c => c.trim());

const books = lines.slice(1).map(line => {
  const vals = parseToonLine(line);
  return Object.fromEntries(cols.map((col, i) => [col, vals[i] || '']));
});

console.log(`✅ Loaded ${books.length} books`);
console.log("First book:", JSON.stringify(books[0]));
if (books.length === 0) throw new Error("FAIL: no books loaded");
if (!books[0].id) throw new Error("FAIL: missing id field");
if (!books[0].name) throw new Error("FAIL: missing name field");
console.log("");

// ============================================================
// TEST 2: README.md — Step 2: Load book metadata
// ============================================================
console.log("=== TEST 2: Load book metadata (README Step 2) ===");
const bookInfo = await fetch(`https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/info.toon`);
const bookInfoText = await bookInfo.text();
console.log(`✅ Fetched bukhari info.toon: ${bookInfoText.length} bytes`);
if (bookInfoText.length < 100) throw new Error("FAIL: info.toon too small");
console.log("");

// ============================================================
// TEST 3: README.md — fetchSection (Arabic section)
// ============================================================
console.log("=== TEST 3: fetchSection — Arabic section ===");

async function fetchSection(book, sectionId) {
  const url = `https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/${book}/sections/${sectionId}.toon`;
  const text = await fetch(url).then(r => r.text());
  
  const headerMatch = text.match(/^([A-Za-z_]+)\[(?:count|\d+)\]\{([^}]+)\}\s*:/);
  if (!headerMatch) return null;
  
  const cols = headerMatch[2].split(',').map(f => f.trim());
  const rest = text.substring(headerMatch[0].length);
  
  const lines = rest.split('\n');
  const hadiths = [];
  let currentRebuiltRow = '';
  let inQuote = false;
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
    currentRebuiltRow += (currentRebuiltRow ? '\n' : '') + line;
    const quotesCount = (trimmed.replace(/""/g, '').match(/"/g) || []).length;
    if (quotesCount % 2 === 1) inQuote = !inQuote;
    
    if (!inQuote) {
      const vals = parseToonLine(currentRebuiltRow);
      const row = {};
      cols.forEach((col, i) => (row[col] = vals[i] || ''));
      hadiths.push(row);
      currentRebuiltRow = '';
    }
  }
  return { columns: cols, hadiths };
}

const { hadiths } = await fetchSection('bukhari', '1');
console.log(`✅ Loaded ${hadiths.length} hadiths from bukhari/sections/1`);
console.log("hadiths[0].arabic:", hadiths[0].arabic?.substring(0, 80));
console.log("hadiths[0].hadithnumber:", hadiths[0].hadithnumber);
console.log("hadiths[0].grades:", hadiths[0].grades?.substring(0, 60));
if (!hadiths[0].arabic) throw new Error("FAIL: no arabic text");
if (!hadiths[0].hadithnumber) throw new Error("FAIL: no hadithnumber");
console.log("");

// ============================================================
// TEST 4: README.md — fetchSection (English translation)
// ============================================================
console.log("=== TEST 4: fetchSection — English translation ===");

const { hadiths: enHadiths } = await fetchSection('bukhari/translations/en', '1');
console.log(`✅ Loaded ${enHadiths.length} English translation hadiths`);
console.log("enHadiths[0].text:", enHadiths[0].text?.substring(0, 80));
console.log("enHadiths[0].hadithnumber:", enHadiths[0].hadithnumber);
if (!enHadiths[0].text) throw new Error("FAIL: no text in English translation");
if (!enHadiths[0].hadithnumber) throw new Error("FAIL: no hadithnumber in English translation");
console.log("");

// ============================================================
// TEST 5: README.md — parseBookInfoMetadata
// ============================================================
console.log("=== TEST 5: parseBookInfoMetadata ===");

function parseBookInfoMetadata(text) {
  const meta = {};
  const lines = text.split('\n');
  let inMetadata = false;
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === 'metadata:') {
      inMetadata = true;
      continue;
    }
    if (inMetadata) {
      if (trimmed.startsWith('translations[') || trimmed.startsWith('sections[')) {
        break;
      }
      const match = trimmed.match(/^(\w+):\s*"?([^"]*)"?$/);
      if (match) {
        meta[match[1]] = match[2];
      }
    }
  }
  return meta;
}

const meta = parseBookInfoMetadata(bookInfoText);
console.log("✅ Parsed metadata keys:", Object.keys(meta));
console.log("meta.book_id:", meta.book_id);
console.log("meta.book_name:", meta.book_name);
console.log("meta.intro_ur (first 60):", meta.intro_ur?.substring(0, 60));
if (!meta.book_id) throw new Error("FAIL: missing book_id");
if (!meta.book_name) throw new Error("FAIL: missing book_name");
console.log("");

// ============================================================
// TEST 6: USAGE.md — fetchAndParseToon
// ============================================================
console.log("=== TEST 6: fetchAndParseToon (USAGE.md JS) ===");

async function fetchAndParseToon(url) {
    const response = await fetch(url);
    const text = await response.text();
    
    const headerMatch = text.match(/^([A-Za-z_]+)\[(?:count|\d+)\]\{([^}]+)\}\s*:/);
    if (!headerMatch) return null;
    
    const fields = headerMatch[2].split(',').map(f => f.trim());
    const rest = text.substring(headerMatch[0].length);
    
    const lines = rest.split('\n');
    const records = [];
    let currentRebuiltRow = '';
    let inQuote = false;
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        
        currentRebuiltRow += (currentRebuiltRow ? '\n' : '') + line;
        
        const quotesCount = (trimmed.replace(/""/g, '').match(/"/g) || []).length;
        if (quotesCount % 2 === 1) {
            inQuote = !inQuote;
        }
        
        if (!inQuote) {
            const parts = parseToonLine(currentRebuiltRow);
            const record = {};
            fields.forEach((field, idx) => {
                record[field] = parts[idx] || '';
            });
            records.push(record);
            currentRebuiltRow = '';
        }
    }
    return records;
}

const records = await fetchAndParseToon("https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/sections/1.toon");
console.log(`✅ Loaded ${records.length} records via fetchAndParseToon`);
if (!records[0].arabic) throw new Error("FAIL: no arabic in fetchAndParseToon result");
console.log("");

// ============================================================
// TEST 7: Nawawi Urdu translation (stress test)
// ============================================================
console.log("=== TEST 7: Nawawi Urdu translation (stress test) ===");
const nawawi = await fetchAndParseToon("https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/nawawi/translations/ur/sections/1.toon");
console.log(`✅ Loaded ${nawawi.length} Nawawi Urdu hadiths`);
if (nawawi.length === 0) throw new Error("FAIL: nawawi urdu returned 0 records");
console.log("");

console.log("🎉 ALL 7 JS TESTS PASSED — ZERO ERRORS!");
