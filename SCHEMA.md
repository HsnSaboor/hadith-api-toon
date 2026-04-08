# Hadith API Toon - Schema Documentation

## Current Schema

### info.toon
```
books[count]{id,name,total_hadiths,max_file_mb,minority_langs}:
```

### editions.toon
```
editions[count]{id,name,author,language,has_sections,dir,comments,path}:
```

### Section Files (editions/{book}/sections/{section}.toon)
```
hadiths[count]{hadithnumber,arabic,bengali,english,french,indonesian,russian,urdu,grades,reference,international_number,narrator_chain,chapter_intro}:
```

## Planned Enhanced Schema (Research-Grade)

### 1. Core Hadith Metadata
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| hadithnumber | ✓ | ✓ | int | Global hadith number |
| international_number | ✓ | ✓ | int | Fuad Abd al-Baqi numbering |
| book_id | ✗ | ✓ | int | Numeric book ID (Bukhari=1, Muslim=2, etc.) |
| book_name_original | ✗ | ✓ | string | Arabic book name |
| book_name_english | ✓ (in editions) | ✓ | string | English book name |
| chapter_id | ✓ (section) | ✓ | int | Chapter/section number |
| chapter_name_original | ✗ | ✓ | string | Arabic chapter name |
| hadith_status_standardized | ✗ | ✓ | enum | Sahih/Hasan/Da'if/Mawdu' |
| hadith_type | ✗ | ✓ | enum | Marfu'/Mawquf/Maqtu' |

### 2. Isnad (Narrator Chain) Structure
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| narrator_chain | ✓ | ✓ | string | Full chain text |
| narrators | ✗ | ✓ | array | Structured narrator objects |
| narrators[].id | ✗ | ✓ | int | Narrator ID |
| narrators[].name_ar | ✗ | ✓ | string | Arabic name |
| narrators[].name_en | ✗ | ✓ | string | English name |
| narrators[].reliability | ✗ | ✓ | string | thiqa/da'if/etc |
| narrators[].birth_year | ✗ | ✓ | int | Birth year AH |
| narrators[].death_year | ✗ | ✓ | int | Death year AH |
| isnad_strength_score | ✗ | ✓ | float | 0.0-1.0 score |

### 3. Matn (Text) Enhancements
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| arabic | ✓ | ✓ | string | Arabic text with tashkeel |
| matn_cleaned | ✗ | ✓ | string | Normalized Arabic (no tashkeel) |
| matn_keywords | ✗ | ✓ | array | Extracted keywords |
| matn_topics | ✗ | ✓ | array | Topic tags |
| matn_entities | ✗ | ✓ | array | Named entities |

### 4. Cross-Reference System
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| reference | ✓ | ✓ | string | Current reference text |
| reference.book | ✗ | ✓ | int | Book number |
| reference.chapter | ✗ | ✓ | int | Chapter number |
| reference.hadith_local | ✗ | ✓ | int | In-book hadith number |
| reference.volume | ✗ | ✓ | int | Volume number |
| reference.page | ✗ | ✓ | int | Page number |
| related_hadiths | ✗ | ✓ | array | Related hadith IDs |
| similar_hadiths | ✗ | ✓ | array | Similar hadith IDs |
| quran_references | ✗ | ✓ | array | Quran ayah references |

### 5. Multi-Language Structure
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| english, urdu, bengali, etc. | ✓ (flat) | ✓ (nested) | object | Per-language translations |
| translations.{lang}.text | ✗ | ✓ | string | Translation text |
| translations.{lang}.translator | ✗ | ✓ | string | Translator name |
| transliteration | ✗ | ✓ | string | Roman transliteration |
| search_normalized | ✗ | ✓ | string | Normalized for search |

### 6. Search & AI Features
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| embedding_vector | ✗ | ✓ | array[float] | Semantic embedding |
| search_tokens | ✗ | ✓ | array | Tokenized text |
| phonetic_keys | ✗ | ✓ | array | Phonetic variations |
| popularity_score | ✗ | ✓ | float | Usage popularity |
| search_rank_weight | ✗ | ✓ | float | Search ranking boost |

### 7. Grading Structure
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| grades | ✓ (string) | ✓ (array) | array | Grade objects |
| grades[].scholar | ✗ | ✓ | string | Scholar name |
| grades[].grade | ✓ | ✓ | string | Grade value |
| grades[].source | ✗ | ✓ | string | Source work |
| grading_consensus | ✗ | ✓ | string | Agreed grade |
| grading_conflicts | ✗ | ✓ | boolean | Has conflicts |

### 8. UI/UX Fields
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| chapter_intro | ✓ | ✓ | string | Chapter introduction |
| short_summary | ✗ | ✓ | string | Brief summary |
| explanation | ✗ | ✓ | string | Full explanation |
| context_background | ✗ | ✓ | string | Historical context |
| keywords_highlighted | ✗ | ✓ | array | UI highlights |
| difficulty_level | ✗ | ✓ | enum | basic/intermediate/advanced |

### 9. Integrity Fields
| Field | Current | Planned | Type | Description |
|-------|---------|---------|------|-------------|
| source_dataset | ✗ | ✓ | string | Data source |
| last_verified_at | ✗ | ✓ | date | Verification date |
| version | ✗ | ✓ | int | Schema version |
| data_quality_score | ✗ | ✓ | float | Quality rating |

## Book ID Mapping
```
1  = bukhari (Sahih al-Bukhari)
2  = muslim (Sahih Muslim)
3  = abudawud (Sunan Abi Dawud)
4  = tirmidhi (Jami' at-Tirmidhi)
5  = nasai (Sunan an-Nasa'i)
6  = ibnmajah (Sunan Ibn Majah)
7  = malik (Al-Muwatta)
8  = musnad-ahmed (Musnad Ahmad)
9  = mishkat (Mishkat al-Masabih)
10 = aladab-almufrad (Al-Adab al-Mufrad)
11 = bulugh-al-maram (Bulugh al-Maram)
12 = shamail-tirmazi (Shama'il al-Tirmidhi)
13 = sunan-darmi (Sunan ad-Darimi)
14 = nawawi (Al-Arba'in al-Nawawiyyah)
15 = qudsi (Al-Ahadith al-Qudsiyyah)
```

## Standardized Hadith Status
```
SAHIH    - Authentic
HASAN    - Good
DAIF     - Weak
MAWDU    - Fabricated
SAHIH_LIGHAIRIHI - Authentic due to supporting chains
HASAN_LIGHAIRIHI - Good due to supporting chains
```

## Hadith Types
```
MARFU   - Attributed to Prophet ﷺ
MAWQUF  - Attributed to Companion
MAQTU   - Attributed to Tabi'i
```
