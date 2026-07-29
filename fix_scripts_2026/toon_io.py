#!/usr/bin/env python3
"""
Shared .toon read/write helpers for the DATASET_FIX_PLAN_2026.md implementation.

Format recap (per README.md):
  line 1: header, either bare `hadiths[N]{col1,col2,...}:` or wrapped in an
          extra pair of double quotes `"hadiths[N]{col1,col2,...}:"`
  lines 2..: standard RFC4180-ish CSV rows (quote-aware, multi-line fields
             allowed inside quotes), positional columns matching the header.

We NEVER interpret backslash as an escape character (matches README's own
correct JS/Python samples, not USAGE.md's buggy JS sample) — csv.reader
already does the right thing by default (only `""` is a real escape).

SURGICAL EDITING STRATEGY (critical for minimal diffs):
Full-file rewrite via csv.writer re-quotes EVERY row (changes `1,"text"` to
`"1","text"` etc even for untouched rows), producing enormous noisy diffs.
Instead we track exact raw-text spans per logical row (respecting multi-line
quoted fields) and only regenerate the span for rows we actually changed,
copying every other row's span byte-for-byte from the original file.
"""
import csv
import io
import re

HEADER_RE = re.compile(r'^"?([A-Za-z_]+)\[(?:count|\d+)\]\{([^}]*)\}\s*:"?\s*$')


def header_is_wrapped(header_line):
    s = header_line.strip()
    return s.startswith('"') and s.endswith(':"')


def make_header(block_name, columns, count, wrapped):
    inner = f'{block_name}[{count}]{{{",".join(columns)}}}:'
    if wrapped:
        return f'"{inner}"'
    return inner


def _split_logical_rows(rest_text):
    """Split the post-header text into logical row spans, respecting
    multi-line quoted fields. Returns list of (raw_span_text, parsed_fields).
    raw_span_text does NOT include the trailing newline that separates it
    from the next row (we re-add exactly one \n between rows on write)."""
    lines = rest_text.split('\n')
    spans = []
    buf_lines = []
    for line in lines:
        if not buf_lines and line == '':
            continue  # skip stray blank separator lines between rows
        buf_lines.append(line)
        combined = '\n'.join(buf_lines)
        # quote parity check: count unescaped quotes (ignore doubled "")
        temp = combined.replace('""', '')
        if temp.count('"') % 2 == 0:
            # balanced -> row complete
            parsed = next(csv.reader(io.StringIO(combined)), [])
            if parsed:
                spans.append((combined, parsed))
            buf_lines = []
    if buf_lines:
        # trailing unterminated content (shouldn't happen in well-formed files)
        combined = '\n'.join(buf_lines)
        parsed = next(csv.reader(io.StringIO(combined)), [])
        if parsed:
            spans.append((combined, parsed))
    return spans


def read_toon(path):
    """Returns dict with header_line, block_name, columns, and spans (list of
    (raw_text, fields) tuples) — the parseable, surgically-editable form."""
    with open(path, encoding='utf-8') as f:
        content = f.read()
    if not content:
        return {'header_line': '', 'block_name': None, 'columns': [], 'spans': []}
    parts = content.split('\n', 1)
    header_line = parts[0]
    rest = parts[1] if len(parts) > 1 else ''
    m = HEADER_RE.match(header_line.strip())
    if not m:
        raise ValueError(f'{path}: cannot parse header: {header_line!r}')
    block_name = m.group(1)
    columns = [c.strip() for c in m.group(2).split(',')]
    spans = _split_logical_rows(rest)
    return {
        'header_line': header_line,
        'block_name': block_name,
        'columns': columns,
        'spans': spans,
    }


def rows_dict(spans, key_col_idx=0):
    """hadithnumber -> fields (list), using LAST occurrence if HN repeats."""
    d = {}
    for _, fields in spans:
        if fields:
            d[fields[key_col_idx]] = fields
    return d


def serialize_row(fields):
    """Quote every field (QUOTE_ALL) — used only for rows we actively
    changed; untouched rows keep their original raw byte span."""
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator='')
    w.writerow(fields)
    return buf.getvalue()


def write_toon(path, header_line, block_name, columns, spans):
    """Writes back preserving original header wrap style and reusing
    untouched rows' exact raw span text; only rows explicitly marked as
    'changed' (span raw text starting with the sentinel produced by
    serialize_row, i.e. spans where we passed a freshly-serialized string)
    differ in on-disk quoting style. count in header = len(spans)."""
    wrapped = header_is_wrapped(header_line) if header_line else False
    header = make_header(block_name, columns, len(spans), wrapped)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(header + '\n')
        f.write('\n'.join(raw for raw, _ in spans))
        f.write('\n')


def apply_merge(spans, key_col_idx, updates, min_growth_ratio=1.3, min_abs_len=50):
    """
    spans: list of (raw_text, fields) from read_toon()['spans']
    updates: dict hadithnumber -> new_text_value (only the *last* column,
             i.e. the translation `text` field, is what we ever replace here)
    Returns (new_spans, log) where log is a list of dicts describing every
    row actually changed (old_len, new_len, hn) for audit purposes. Refuses
    to shrink: only replaces if new text is >= min_growth_ratio times longer
    OR old text is empty/near-empty, matching the plan's no-shrink guardrail.
    """
    log = []
    new_spans = []
    for raw, fields in spans:
        hn = fields[key_col_idx] if fields else None
        if hn in updates and len(fields) >= 1:
            old_text = fields[-1] if len(fields) > 1 else ''
            new_text = updates[hn]
            old_len = len(old_text)
            new_len = len(new_text)
            should_replace = (
                new_text
                and new_text != old_text
                and (
                    old_len == 0
                    or (new_len >= min_abs_len and new_len >= old_len * min_growth_ratio)
                )
            )
            if should_replace:
                new_fields = list(fields)
                new_fields[-1] = new_text
                new_raw = serialize_row(new_fields)
                new_spans.append((new_raw, new_fields))
                log.append({'hn': hn, 'old_len': old_len, 'new_len': new_len})
                continue
        new_spans.append((raw, fields))
    return new_spans, log
