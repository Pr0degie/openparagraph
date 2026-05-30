# 001 — GII data shape: `jurabk` as primary key, `amtabk` unreliable

**Status:** accepted  
**Date:** 2026-05-30  
**Spike:** `docs/spike_a.md`, `data/spike_a/results.json`

## Context

Spike A downloaded and parsed 10 representative laws from the 6 123-law GII
corpus to confirm that the metadata fields assumed in ARCHITECTURE.md §5 are
actually present in the raw data.

## Decision

**Use `jurabk` as the sole law identifier.** Never depend on `amtabk`.

Node ids take the form `de-bund/<jurabk>` (as specified in ARCHITECTURE.md),
and this is confirmed sound: `jurabk` was present in 100 % of sampled laws.

## Findings

| Field | Present | Decision |
|---|---|---|
| `jurabk` | 10/10 (100%) | Primary key, always use |
| `ausfertigung-datum` | 10/10 (100%) | Safe to rely on for `created_at` |
| `langue` | 10/10 (100%) | Safe to use as display title |
| `amtabk` | 3/10 (30%) | Store if present, never require |

Additional observations:
- XML element for the date is `<ausfertigung-datum>` (hyphenated); attribute
  `manuell="ja"` is sometimes present but ignorable.
- Content norm `<titel>` (§ heading) is absent in proclamation-type laws —
  the parser must treat it as nullable.
- ZIP archives occasionally contain non-XML files (e.g. embedded coin images
  for Münzbekanntmachungen). Parse only `.xml` entries from the ZIP.
- Norm counts span 1–351; no special-casing needed for either extreme.

## Alternatives considered

Using `amtabk` as the key was rejected because only 30 % of laws have it.
Using `doknr` (the `builddate`/`doknr` attributes on `<norm>`) was rejected
because it is an internal GII system id, not a stable human-readable key.

## Consequences

- `pipeline/src/gii_parser.py`: `Law.amtabk` is `Optional[str]`, never a key.
- Stage 04 (`parse_laws`) and Stage 08 (`resolve_refs`) must build all
  identifiers from `jurabk` only.
- `reference-resolver.json` maps normalized ref strings to `de-bund/<jurabk>`.
