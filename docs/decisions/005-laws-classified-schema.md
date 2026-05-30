# 005 — laws_classified.json: compact metadata, main_group as int, meta_cluster deferred

**Status:** accepted  
**Date:** 2026-05-30

## Context

Stage 06 (`classify`) produces `build/laws_classified.json`, which is the
central lookup table used by Stages 09 (embed), 10 (orphan neighbors),
11 (build_graph), and 13 (color).  Three design questions arose:

1. **Include full norm lists?** Each `laws_parsed/{slug}.json` can be 50–200 KB
   (BGB ≈ 2385 norms × ~1 KB text).  Duplicating all 6 000 norm lists into a
   single file would produce a multi-GB monolith that no stage needs as a whole.

2. **`main_group` as integer or string?** The FNA code's first digit (1–9)
   identifies the Sachgebiet main group.  The final node schema uses a string
   `meta_cluster` (e.g. `"civil-law"`), but the mapping from digit to name is
   external taxonomy data not yet pinned.

3. **Emit `meta_cluster` string now or later?** The nine human-readable cluster
   names will eventually live in `data/_global/meta-taxonomy.json` (Stage 13).
   Hardcoding them in Stage 06 would couple classification to color logic.

## Decision

1. **No full norm lists** in `laws_classified.json`.  Stages that need
   norm-level detail (07 extract_refs, 08 resolve_refs) read
   `laws_parsed/{slug}.json` directly.  Stage 06 only copies top-level metadata
   (`jurabk`, `amtabk`, `langue`, `ausfertigung_datum`, `norm_count`) plus
   `fna_code`, `main_group`, and `opening_text`.

2. **`main_group` is an integer 1–9** (or `null` for unclassified laws).
   Derived as `int(fna_code[0])`.  Simple and unambiguous.

3. **`meta_cluster` string is deferred to Stage 13.**  Stage 06 does not emit
   it.  Stage 13 (color) will join `main_group` → `meta_cluster` via the
   taxonomy file, keeping taxonomy changes confined to Stage 13.

`opening_text` (first non-empty norm text, XML tags stripped, ≤ 500 chars) is
included because Stage 09 (embed) needs it and it is cheap to extract here
once rather than re-reading 6 000 JSON files in Stage 09.

## Alternatives considered

- **Include full norm lists** — rejected: ~1 GB monolith that no single stage
  needs whole; better to keep norm data in per-law files.
- **`meta_cluster` string now** — rejected: the nine names aren't finalized;
  hardcoding them creates a maintenance burden and couples classification to
  color logic.
- **Separate `opening_text` extraction into Stage 09** — viable, but Stage 09
  would then re-read all 6 000 large JSON files just to get the first norm text.
  Cheaper to extract it once in Stage 06 while the file is already open.

## Consequences

- Stages 07 and 08 must read `build/laws_parsed/` directly for norm text.
  This is already reflected in their stub inputs.
- Adding a `meta_cluster` field later requires only a Stage 13 change (and a
  re-run of Stage 13 onward), not a full re-classify.
- The `opening_text` field is a heuristic (first usable norm text).  Laws with
  only structural norms (tables, annexes) may get `null`; Stage 09 must handle
  this gracefully (skip embedding or use title only).
