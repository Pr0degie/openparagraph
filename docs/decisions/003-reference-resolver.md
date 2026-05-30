# 003 — Reference resolver: jurabk-based lookup with false-positive filter

**Status:** accepted  
**Date:** 2026-05-30  
**Spike:** `docs/spike_c.md`, `pipeline/spikes/spike_c_references.py`

## Context

Spike C tested `refex` (package: `legal-reference-extraction`) on 5 laws
(3 450 norms) and prototyped a reference resolver. The key design question:
how should `refex` output be converted into graph edges `(source_norm → target_law)`?

Findings:
- refex returns `book='aufenthaltsgesetz'` (long-form, lowercase) for a citation
  to the Aufenthaltsgesetz, not the GII slug `aufenthg_2004` or abbreviation `AufenthG`.
- ~49% of raw refex citations are false positives (generic words like "vorschriften",
  "verordnung") — these must be filtered before building edges.
- The GII TOC title is unreliable as a lookup key: slugs encode year variants
  (`tkg_2021`, `aufenthg_2004`), formal titles diverge from common law names.
- The authoritative lookup key is the `jurabk` field (inside each law's XML),
  which represents the official abbreviation and maps naturally to the slug.

## Decision

Build the resolver in Stage 01 (as part of the law metadata extraction pass),
not in Stage 06. Stage 01 outputs a `slug_table.json`:

```json
{
  "aufenthg": {"jurabk": "AufenthG", "langue": "Gesetz über den Aufenthalt…"},
  "tkg_2021": {"jurabk": "TKG", "langue": "Telekommunikationsgesetz"},
  …
}
```

Stage 06 builds `reference-resolver.json` from `slug_table.json` using a
three-step lookup:

1. **Normalize** refex book → strip genitive suffix, ß↔ss, collapse spaces
2. **jurabk match**: normalized book → `jurabk.lower()` in slug_table → slug
3. **langue fuzzy** (Stage 06 enhancement): token overlap with `langue` field

Pre-filter drops generic non-law words before any lookup attempt:
`vorschriften`, `verordnung`, `rechtsverordnung`, `anordnung`, `haftung`,
`bundes`, `überwachung`, `ordnungswidrigkeiten`.

Ambiguous `einführungsgesetz` citations are resolved by injecting the current
law's own jurabk as context: `BGB` → `BGBEG`, `StGB` → `EGStGB`, etc.

## Alternatives considered

- **Title-based resolver only** — rejected. Spike C showed 23% overall coverage
  with title matching; many laws use year-versioned slugs or formal titles that
  don't match the common law name. jurabk is the natural shared key between
  refex output and GII data.
- **Build full resolver in Stage 06** — rejected. The slug_table is a
  natural by-product of Stage 01's XML parse of all 6 124 laws. Building it
  separately in Stage 06 would mean a second pass over all XMLs.
- **Use refex's built-in `resolves_to` field** — inspected; the field is None
  for all citations in the spike (the package ships without a resolver). We
  build our own.

## Consequences

- Stage 01 must output `slug_table.json` in addition to its per-law metadata.
  This is a small addition to the existing XML parse loop.
- Stage 06 (reference extraction stage) is now:
  1. Load `slug_table.json`
  2. Build `jurabk_index`: `{normalized_jurabk → slug}`
  3. For each law in corpus: extract text → run refex → filter noise →
     normalize book → lookup → emit edge `(source_slug, target_slug)` or skip
  4. Write `edges.json` (for Stage 07 graph build) and
     `reference-resolver.json` (for frontend `clickable-refs`)
- Expected edge coverage: ~55–65% of raw refex citations resolve to a GII node.
  The remaining ~35–45% are either noise (already filtered), very new laws,
  EU/state-law references (out of scope for v1), or ambiguous fragments.
- The false-positive filter block-list is hard-coded in Stage 06 and versioned
  with the codebase (not in config), since it's a linguistic constant.
- ARCHITECTURE.md §9 stage map updated: Stage 01 gains `slug_table.json` output;
  Stage 06 gains `reference-resolver.json` + `edges.json` outputs.
