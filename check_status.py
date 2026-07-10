import json
with open("/home/saboor/code/hadith-api-toon/sunnah.com-download/adab/en.json", "r") as f:
    data = json.load(f)
narrators = sum(1 for d in data if d.get("narrator"))
statuses = sum(1 for d in data if d.get("status"))
print(f"Filled narrators: {narrators}")
print(f"Filled statuses: {statuses}")
