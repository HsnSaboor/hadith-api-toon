# How to Use Hadith API (Toon Format)

This database is built using the `.toon` format—a compact, positional, CSV-like text format optimized for rapid client-side parsing and minimal network overhead.

---

## 🛰️ 1. CDN Endpoint Guide

The database is hosted on GitHub and served dynamically via **jsDelivr** (with automatic Brotli compression).

### Base URL:
```
https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/
```

### Endpoints:
1. **API Registry / Book Directory**: Get a listing of all 31 available books, their hadith counts, supported translation languages, and subfolder paths:
   ```
   https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon
   ```
2. **Book Metadata & Chapters**: Get the author info, book introduction, translation list, and all chapter boundaries for a specific book (e.g., Sahih al-Bukhari):
   ```
   https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/info.toon
   ```
3. **Arabic Text & Scholar Grades**: Get sections of the original Arabic hadiths (e.g., Bukhari, Section 1):
   ```
   https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/sections/1.toon
   ```
4. **Translations**: Get translations for a specific language and section (e.g., Urdu translation for Bukhari, Section 1):
   ```
   https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/translations/ur/sections/1.toon
   ```

---

## 🛠️ 2. Stateful Parser Examples

Since `.toon` records are CSV-compliant but contain multi-line quoted text block payloads (especially in Arabic text, narrators, and translations), **simple line-by-line splitting is incorrect** and will break on internal newlines. You must track quotes statefully.

### Python Parser (Stateful CSV Reader)
```python
import csv
import io
import urllib.request

def parse_toon_url(url):
    # Fetch content
    with urllib.request.urlopen(url) as response:
        text = response.read().decode('utf-8')
    
    # 1. Parse header block structure: hadiths[count]{fields}:
    import re
    header_match = re.search(r'^([A-Za-z_]+)\[(?:count|\d+)\]\{(.*?)\}\s*:', text, re.DOTALL)
    if not header_match:
        raise ValueError("Invalid .toon format header")
        
    block_name = header_match.group(1)
    fields = [f.strip() for f in header_match.group(2).split(',')]
    rest_data = text[header_match.end():]
    
    # 2. Parse data rows statefully using csv.reader
    reader = csv.reader(io.StringIO(rest_data))
    records = []
    for row in reader:
        if not row:
            continue
        # Align rows with schema fields
        if len(row) < len(fields):
            row += [''] * (len(fields) - len(row))
        records.append(dict(zip(fields, row)))
        
    return block_name, records

# Example Usage:
block_name, hadiths = parse_toon_url("https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/editions/bukhari/sections/1.toon")
print(f"Loaded {len(hadiths)} hadiths from block '{block_name}'")
print("First Hadith:", hadiths[0]['arabic'][:80])
```

### JavaScript / Browser Client Parser
```javascript
// A simple stateful quote-aware CSV splitter for JS
function parseToonLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    let i = 0;
    
    while (i < line.length) {
        const char = line[i];
        if (inQuotes) {
            if (char === '"') {
                if (i + 1 < line.length && line[i + 1] === '"') {
                    current += '"';
                    i += 2;
                } else {
                    inQuotes = false;
                    i++;
                }
            } else if (char === '\\' && i + 1 < line.length) {
                const next = line[i + 1];
                if (next === 'n') current += '\n';
                else if (next === 't') current += '\t';
                else if (next === '"') current += '"';
                else if (next === '\\') current += '\\';
                else current += next;
                i += 2;
            } else {
                current += char;
                i++;
            }
        } else {
            if (char === '"') {
                inQuotes = true;
                i++;
            } else if (char === ',') {
                result.push(current);
                current = '';
                i++;
            } else {
                current += char;
                i++;
            }
        }
    }
    result.push(current);
    return result;
}

// Fetch and parse a section file in JS
async function fetchAndParseToon(url) {
    const response = await fetch(url);
    const text = await response.text();
    
    // Match schema: name[type]{fields}:
    const headerMatch = text.match(/^([A-Za-z_]+)\[(?:count|\d+)\]\{([^}]+)\}\s*:/);
    if (!headerMatch) return null;
    
    const fields = headerMatch[2].split(',').map(f => f.trim());
    const rest = text.substring(headerMatch[0].length);
    
    // Read stateful rows
    const lines = rest.split('\n');
    const records = [];
    let currentRebuiltRow = '';
    let inQuote = false;
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        
        currentRebuiltRow += (currentRebuiltRow ? '\n' : '') + line;
        
        // Count unescaped double quotes in the segment
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
```
