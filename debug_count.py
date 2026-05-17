import os

fp = '/home/saboor/code/hadith-api-toon/editions/sahih-ibn-khuzaymah/sections/2.toon'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find(':')
data = content[idx+1:]

# Show first 500 chars
print('First 500:', repr(data[:500]))
print()
print('Last 500:', repr(data[-500:]))
print()

# Show transitions looking for pattern "number," 
# Find positions of number+comma sequences
# Just print the first couple splits
# Try: split by ", and look at what follows
# Actually let me see what happens around position 1000-1500
for pos in range(0, min(5000, len(data)), 200):
    chunk = data[pos:pos+200]
    # Check if chunk starts with a number after cleaning
    cleaned = chunk.lstrip(' \n\r\t')
    if cleaned and (cleaned[0].isdigit() or cleaned.startswith('"')):
        first_bit = cleaned[:50]
        print(f'Pos {pos}: {repr(first_bit)}...')
