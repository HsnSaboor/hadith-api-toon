#!/usr/bin/env python3
import os
import re
import csv
import json
import gzip
import brotli
import subprocess
from pathlib import Path

# Setup paths inside workspace
BASE_DIR = Path("/home/saboor/code/hadith-api-toon")
BOOK_DIR = BASE_DIR / "editions" / "shamail-tirmazi"
TMP_DIR = BASE_DIR / "tmp_experiment"

# 1. Create temp directory
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Helper: Parse a CSV line handling quotes
def parse_toon_line(line):
    result = []
    current = ''
    in_quotes = False
    i = 0
    while i < len(line):
        char = line[i]
        if in_quotes:
            if char == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    current += '"'
                    i += 2
                else:
                    in_quotes = False
                    i += 1
            elif char == '\\' and i + 1 < len(line):
                next_char = line[i + 1]
                if next_char == 'n': current += '\n'
                elif next_char == 't': current += '\t'
                elif next_char == '"': current += '"'
                elif next_char == '\\': current += '\\'
                else: current += next_char
                i += 2
            else:
                current += char
                i += 1
        else:
            if char == '"':
                in_quotes = True
                i += 1
            elif char == ',':
                result.append(current)
                current = ''
                i += 1
            else:
                current += char
                i += 1
    result.append(current)
    return result

def main():
    print("Starting data parsing for shamail-tirmazi...", flush=True)
    
    # 2. Write hadith.proto file
    proto_content = """syntax = "proto3";

message Book {
  string id = 1;
  string name = 2;
  int32 total_hadiths = 3;
  string intro = 4;
  string intro_ar = 5;
  string intro_en = 6;
  string intro_ur = 7;
  
  repeated Chapter chapters = 8;
  repeated Hadith hadiths = 9;
}

message Chapter {
  string id = 1;
  string name = 2;
  string name_ar = 3;
  string name_bn = 4;
  string name_en = 5;
  string name_fr = 6;
  string name_id = 7;
  string name_ru = 8;
  string name_tr = 9;
  string name_ur = 10;
  string first_hadith = 11;
  string last_hadith = 12;
}

message Hadith {
  string number = 1;
  string arabic = 2;
  string grades = 3;
  string reference = 4;
  map<string, string> translations = 5;
}
"""
    proto_path = TMP_DIR / "hadith.proto"
    proto_path.write_text(proto_content, encoding="utf-8")
    
    # Compile proto using protoc
    print("Compiling protobuf schema...", flush=True)
    subprocess.run([
        "protoc", 
        f"--python_out={TMP_DIR}", 
        f"--proto_path={TMP_DIR}", 
        str(proto_path)
    ], check=True)
    
    # Strip version checks to prevent version mismatch exceptions
    pb2_path = TMP_DIR / "hadith_pb2.py"
    pb2_content = pb2_path.read_text(encoding="utf-8")
    pb2_content = re.sub(
        r'_runtime_version\.ValidateProtobufRuntimeVersion\(.*?\)',
        r'pass',
        pb2_content,
        flags=re.DOTALL
    )
    pb2_path.write_text(pb2_content, encoding="utf-8")
    
    # Import the generated module
    import sys
    sys.path.append(str(TMP_DIR))
    import hadith_pb2
    
    # 3. Parse Toon data
    # Parse info.toon
    info_path = BOOK_DIR / "info.toon"
    info_content = info_path.read_text(encoding="utf-8")
    
    # Parse Metadata
    meta = {}
    in_meta = False
    for line in info_content.splitlines():
        trimmed = line.strip()
        if trimmed == "metadata:":
            in_meta = True
            continue
        if in_meta:
            if trimmed.startswith("translations[") or trimmed.startswith("sections["):
                in_meta = False
                break
            match = re.match(r"^(\w+):\s*\"(.*)\"$", trimmed)
            if not match:
                # might not have quotes if it is multiline or simple
                match = re.match(r"^(\w+):\s*\"?(.*?)\"?$", trimmed)
            if match:
                meta[match.group(1)] = match.group(2)
                
    # Parse Chapters/Sections
    chapters = []
    lines = info_content.splitlines()
    sec_header = next(l for l in lines if l.strip().startswith("sections["))
    fields_match = re.search(r"\{([^}]+)\}", sec_header)
    fields = [f.strip() for f in fields_match.group(1).split(",")]
    
    sec_start = lines.index(sec_header) + 1
    count = int(re.search(r"\[(\d+)\]", sec_header).group(1))
    
    for i in range(sec_start, sec_start + count):
        line = lines[i].strip()
        if not line: continue
        parts = parse_toon_line(line)
        if len(parts) >= len(fields):
            ch = {}
            for idx, field in enumerate(fields):
                ch[field] = parts[idx]
            chapters.append(ch)
            
    # Gather all Hadiths
    hadiths_dict = {} # hadithnumber -> hadith object
    
    # Read Arabic sections
    sections_dir = BOOK_DIR / "sections"
    for f in os.listdir(sections_dir):
        if not f.endswith(".toon"): continue
        sec_path = sections_dir / f
        content = sec_path.read_text(encoding="utf-8")
        h_lines = content.splitlines()
        h_header = next(l for l in h_lines if l.strip().startswith("hadiths["))
        h_idx = h_lines.index(h_header) + 1
        for line in h_lines[h_idx:]:
            if not line.strip(): continue
            parts = parse_toon_line(line)
            if len(parts) >= 4:
                hn = parts[0]
                hadiths_dict[hn] = {
                    "number": hn,
                    "arabic": parts[1],
                    "grades": parts[2],
                    "reference": parts[3],
                    "translations": {}
                }
                
    # Read English and Urdu translations
    langs = ["en", "ur"]
    for lang in langs:
        trans_sec_dir = BOOK_DIR / "translations" / lang / "sections"
        if not trans_sec_dir.exists(): continue
        for f in os.listdir(trans_sec_dir):
            if not f.endswith(".toon"): continue
            t_path = trans_sec_dir / f
            content = t_path.read_text(encoding="utf-8")
            t_lines = content.splitlines()
            t_header = next(l for l in t_lines if l.strip().startswith("hadiths["))
            t_idx = t_lines.index(t_header) + 1
            for line in t_lines[t_idx:]:
                if not line.strip(): continue
                parts = parse_toon_line(line)
                if len(parts) >= 2:
                    hn = parts[0]
                    if hn in hadiths_dict:
                        hadiths_dict[hn]["translations"][lang] = parts[1]
                        
    # Convert dict to sorted list of Hadiths
    hadiths_list = [hadiths_dict[k] for k in sorted(hadiths_dict.keys(), key=lambda x: int(re.sub(r"\D", "", x)))]
    
    # 4. Serialize to Target Formats
    book_data = {
        "id": meta.get("book_id", ""),
        "name": meta.get("book_name", ""),
        "total_hadiths": int(meta.get("total_hadiths", "0")),
        "intro": meta.get("intro", ""),
        "intro_ar": meta.get("intro_ar", ""),
        "intro_en": meta.get("intro_en", ""),
        "intro_ur": meta.get("intro_ur", ""),
        "chapters": chapters,
        "hadiths": hadiths_list
    }
    
    # Write Pretty JSON
    json_path = TMP_DIR / "shamail-tirmazi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)
        
    # Write Minified JSON
    min_json_path = TMP_DIR / "shamail-tirmazi.min.json"
    with open(min_json_path, "w", encoding="utf-8") as f:
        json.dump(book_data, f, separators=(",", ":"), ensure_ascii=False)
        
    # Write Merged Toon
    toon_merged_path = TMP_DIR / "shamail-tirmazi.toon"
    # To construct a single merged toon representing all data:
    with open(toon_merged_path, "w", encoding="utf-8") as f:
        # metadata section
        f.write("metadata:\n")
        for k, v in meta.items():
            f.write(f'  {k}: "{v}"\n')
        f.write("\n")
        # chapters section
        f.write(sec_header + "\n")
        for ch in chapters:
            row = [ch.get(field, "") for field in fields]
            f.write(','.join(f'"{x}"' if ',' in x or '"' in x or '\n' in x else x for x in row) + "\n")
        f.write("\n")
        # hadiths section
        f.write("hadiths[417]{hadithnumber,arabic,grades,reference,translation_en,translation_ur}:\n")
        for h in hadiths_list:
            row = [
                h["number"],
                h["arabic"],
                h["grades"],
                h["reference"],
                h["translations"].get("en", ""),
                h["translations"].get("ur", "")
            ]
            row_formatted = []
            for val in row:
                if ',' in val or '"' in val or '\n' in val:
                    row_formatted.append('"' + val.replace('"', '""') + '"')
                else:
                    row_formatted.append(val)
            f.write(','.join(row_formatted) + "\n")

    # Write Protobuf Binary
    pb_book = hadith_pb2.Book()
    pb_book.id = book_data["id"]
    pb_book.name = book_data["name"]
    pb_book.total_hadiths = book_data["total_hadiths"]
    pb_book.intro = book_data["intro"]
    pb_book.intro_ar = book_data["intro_ar"]
    pb_book.intro_en = book_data["intro_en"]
    pb_book.intro_ur = book_data["intro_ur"]
    
    for ch in chapters:
        pb_ch = pb_book.chapters.add()
        pb_ch.id = ch.get("id", "")
        pb_ch.name = ch.get("name", "")
        pb_ch.name_ar = ch.get("name_ar", "")
        pb_ch.name_bn = ch.get("name_bn", "")
        pb_ch.name_en = ch.get("name_en", "")
        pb_ch.name_fr = ch.get("name_fr", "")
        pb_ch.name_id = ch.get("name_id", "")
        pb_ch.name_ru = ch.get("name_ru", "")
        pb_ch.name_tr = ch.get("name_tr", "")
        pb_ch.name_ur = ch.get("name_ur", "")
        pb_ch.first_hadith = ch.get("hadith_first", "")
        pb_ch.last_hadith = ch.get("hadith_last", "")
        
    for h in hadiths_list:
        pb_h = pb_book.hadiths.add()
        pb_h.number = h["number"]
        pb_h.arabic = h["arabic"]
        pb_h.grades = h["grades"]
        pb_h.reference = h["reference"]
        for l, text in h["translations"].items():
            pb_h.translations[l] = text
            
    pb_path = TMP_DIR / "shamail-tirmazi.pb"
    pb_path.write_bytes(pb_book.SerializeToString())
    
    # 5. Measure Sizes and Compressions
    # Gather size of original individual toon files
    original_toon_size = info_path.stat().st_size
    for f in os.listdir(sections_dir):
        original_toon_size += (sections_dir / f).stat().st_size
    for lang in langs:
        trans_dir = BOOK_DIR / "translations" / lang / "sections"
        if trans_dir.exists():
            for f in os.listdir(trans_dir):
                original_toon_size += (trans_dir / f).stat().st_size
                
    files = {
        "Toon (Multi-file)": (None, original_toon_size),
        "Toon (Merged)": (toon_merged_path, toon_merged_path.stat().st_size),
        "JSON (Pretty)": (json_path, json_path.stat().st_size),
        "JSON (Minified)": (min_json_path, min_json_path.stat().st_size),
        "Protobuf (Binary)": (pb_path, pb_path.stat().st_size)
    }
    
    results = []
    
    for label, (path, raw_size) in files.items():
        if path is None:
            # Multi-file toon size, can't compress simply as one file, but we can approximate by compressing all and summing
            gz_size = 0
            br_size = 0
            # Compress info
            gz_size += len(gzip.compress(info_path.read_bytes()))
            br_size += len(brotli.compress(info_path.read_bytes()))
            # Compress sections
            for f in os.listdir(sections_dir):
                data = (sections_dir / f).read_bytes()
                gz_size += len(gzip.compress(data))
                br_size += len(brotli.compress(data))
            # Compress translations
            for lang in langs:
                trans_dir = BOOK_DIR / "translations" / lang / "sections"
                if trans_dir.exists():
                    for f in os.listdir(trans_dir):
                        data = (trans_dir / f).read_bytes()
                        gz_size += len(gzip.compress(data))
                        br_size += len(brotli.compress(data))
        else:
            raw_bytes = path.read_bytes()
            gz_bytes = gzip.compress(raw_bytes)
            br_bytes = brotli.compress(raw_bytes)
            
            # Write compressed files for inspection
            (path.parent / (path.name + ".gz")).write_bytes(gz_bytes)
            (path.parent / (path.name + ".br")).write_bytes(br_bytes)
            
            gz_size = len(gz_bytes)
            br_size = len(br_bytes)
            
        results.append({
            "Format": label,
            "Raw Size (B)": raw_size,
            "Gzip Size (B)": gz_size,
            "Brotli Size (B)": br_size
        })
        
    # 6. Save results to report json
    with open(TMP_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("Experiment completed! Writing results...", flush=True)

if __name__ == "__main__":
    main()
