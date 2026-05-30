# 007 — Stage 08: three-key jurabk index, laws_classified dropped as input

**Status:** accepted  
**Date:** 2026-05-30

## Context

Stage 08 must map the `book` field from refex citations (e.g. `"bgb"`,
`"aufenthaltsgesetz"`, `"bürgerlichen gesetzbuches"`) to a GII slug so it
can emit graph edges and the frontend resolver.  Two design questions arose:

**1. What keys should the lookup index contain?**  
`slug_table.json` has `jurabk` (official abbreviation) and `langue` (full
formal title).  `toc.json` has the common name as listed by GII.  Refex
returns a mix: abbreviations ("bgb"), common names ("aufenthaltsgesetz"),
and genitive-inflected long forms ("bürgerlichen gesetzbuches").

**2. Does Stage 08 need `laws_classified.json` as input?**  
The stub declared it.  In practice Stage 08 only needs jurabk (for node ID
construction) and langue (for parenthetical short-name extraction), both
present in `slug_table.json`.

## Decision

**Three-key index** (priority order, first-write-wins):
1. `jurabk` abbreviation → slug  (e.g. "bgb" → bgb, "stgb" → stgb)
2. TOC common title → slug  (e.g. "aufenthaltsgesetz" → aufenthg_2004)
3. Parenthetical short name from `langue` → slug
   (e.g. `"... (Aufenthaltsgesetz)"` → aufenthg_2004)

`normalize_book()` strips accents, maps ß→ss, removes non-alphanumeric, and
strips German genitive `-es` from words longer than 10 chars.

**`laws_classified.json` removed from inputs.**  Slug_table + toc are sufficient.

## Alternatives considered

- **jurabk only** — rejected: refex often returns long-form names
  ("aufenthaltsgesetz") that don't match abbreviations ("AufenthG"); TOC titles
  close the gap for the majority of unabbreviated citations.
- **Full langue title lookup** — rejected: formal titles like "Gesetz über den
  Aufenthalt, die Erwerbstätigkeit und die Integration von Ausländern im
  Bundesgebiet" do not match refex short names at all; only the parenthetical
  short name at the end is useful.
- **Keeping `laws_classified.json` as input** — rejected: it adds a Stage 06
  dependency (→ slower DAG fan-out) and provides nothing that slug_table
  doesn't already have.

## Consequences

- Genitive-inflected adjective forms (`"bürgerlichen gesetzbuches"` for BGB)
  still don't match the index after normalization because the adjective
  "bürgerlichen" differs from "bürgerliches".  This is an accepted residual
  miss; fuzzy/token matching is a noted future improvement (PROGRESS.md).
- Expected coverage stays at ADR 003's ~55–65 % after Stage 07 filtering.
- Changing the index strategy requires only a Stage 08 re-run
  (edges + resolver rebuilt from the same refs_raw.json).
- `data/_global/reference-resolver.json` is the first file Stage 08 writes
  directly into the final data tree (`data/`); all other Stage 08 outputs are
  in `build/`.
