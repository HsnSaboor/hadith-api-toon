# References Extraction Report

Source: `takhreej_downloads/hadith/*.jsonl`  
Output: `references.toon` (38,565 entries)

---

## Coverage Summary

| Edition | Extracted | Added to refs.toon | Skipped (not in edition) | Already in grades.toon? |
|---------|-----------|-------------------|--------------------------|------------------------|
| abudawud | 5,264 | 5,264 | 0 | ✅ Yes |
| alzawaid | 12,216 | 12,216 | 0 | — |
| bayhaqi | 20,494 | 123 | 20,371 | — |
| bukhari | 1,453 | 1,453 | 0 | — |
| ibnmajah | 4,324 | 4,324 | 0 | ✅ Yes |
| malik | 1,851 | 1,851 | 0 | ✅ Yes |
| mishkat | 6,294 | 1 | 6,293 | — |
| musannaf-ibn-abi-shaybah | 0 | 0 | 0 | — |
| muslim | 0 | 0 | 0 | — |
| musnad-ahmed | 0 | 0 | 0 | — |
| mustadrak | 0 | 0 | 0 | — |
| nasai | 5,761 | 5,758 | 3 | ✅ Yes |
| sahih-ibn-khuzaymah | 3,053 | 26 | 3,027 | — |
| silsila-sahih | 3,703 | 50 | 3,653 | — |
| sunan-darmi | 3,545 | 3,545 | 0 | — |
| tirmidhi | 3,954 | 3,954 | 0 | ✅ Yes |

---

## What Is a Takhreej?

**Takhreej** (تخریج) is a cross-reference field in Islamic hadith scholarship.
It lists where the same hadith appears in other major collections, along with
the grade/authenticity ruling at the end (e.g., `(حسن صحیح)` = Hasan Sahih).

Example:
```
تخریج دارالدعوہ: سنن الترمذی/الطھارة ۱۶ (۲۰)، سنن النسائی/الطھارة ۱۶ (۱۷)،
سنن ابن ماجہ/الطھارة ۲۲ (۳۳۱)، (تحفة الأشراف: ۱۱۵۴۰)،
وقد أخرجہ: مسند احمد (۴/۲۴۴)، سنن الدارمی/الطھارة ۴ (۶۸۶) (حسن صحیح)
```

## File Format — references.toon

```
references[N]{book,hadithnumber,source,takhreej}:
abudawud,1,takhreej,تخریج دارالدعوہ: ...
abudawud,2,takhreej,تخریج دارالدعوہ: ...
```

## Relationship to grades.toon

| File | Content | Books covered |
|------|---------|---------------|
| `grades.toon` | Structured `grader: grade` pairs (Al-Albani, Shuaib Al Arnaut, etc.) | abudawud, ibnmajah, malik, nasai, tirmidhi |
| `references.toon` | Free-text Urdu Takhreej (cross-references + embedded grade) | All books with non-zero Takhreej in takhreej |

These are **complementary** — `grades.toon` has machine-readable English grades,
`references.toon` has rich Urdu scholarly cross-reference text.

## Books With Zero Takhreej (takhreej gaps)

| Book | Reason |
|------|--------|
| muslim | Only 5/7564 hadiths have Takhreej in takhreej |
| musnad | No Takhreej available |
| mustadrak | No Takhreej available |
| shaybah | No Takhreej available |
