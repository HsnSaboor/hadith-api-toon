import os

editions_dir = 'editions'
books = os.listdir(editions_dir)

results = []

for book in sorted(books):
    book_path = os.path.join(editions_dir, book)
    if not os.path.isdir(book_path): continue
    
    langs = ['en', 'ur']
    status = {'book': book}
    
    for lang in langs:
        sections_path = os.path.join(book_path, 'translations', lang, 'sections')
        if os.path.isdir(sections_path):
            files = [f for f in os.listdir(sections_path) if f.endswith('.toon')]
            status[lang] = len(files)
        else:
            status[lang] = 0
            
    results.append(status)

print(f"{'Book':<30} | {'English Sections':<16} | {'Urdu Sections':<13}")
print("-" * 65)
for res in results:
    print(f"{res['book']:<30} | {res['en']:<16} | {res['ur']:<13}")
