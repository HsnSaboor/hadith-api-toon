const response = await fetch('https://cdn.jsdelivr.net/gh/HsnSaboor/hadith-api-toon@main/info.toon');
const text = await response.text();
const lines = text.split('\n').filter(l => l.trim());
console.log("Total filtered lines:", lines.length);
console.log("Header:", lines[0]);
console.log("Data lines:", lines.length - 1);
// Check which lines DON'T start with a quote
lines.slice(1).forEach((line, i) => {
  if (!line.startsWith('"')) {
    console.log(`  Line ${i+1} does NOT start with quote:`, line.substring(0, 80));
  }
});
