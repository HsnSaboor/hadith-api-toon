import os

editions_dir = 'editions'
books = os.listdir(editions_dir)

for book in sorted(books):
    info_path = os.path.join(editions_dir, book, 'info.toon')
    if os.path.exists(info_path):
        with open(info_path, 'r') as f:
            content = f.read()
            # Basic parsing of info.toon which seems to have "languages: [en, ur, ...]"
            print(f"Book: {book}")
            for line in content.splitlines():
                if 'languages' in line:
                    print(f"  {line.strip()}")
