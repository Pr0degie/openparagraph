# 006 — Stage 07: ProcessPoolExecutor for refex, filter before disk

**Status:** accepted  
**Date:** 2026-05-30

## Context

Stage 07 runs `refex` (CitationExtractor) over every norm in ~6 000 laws.
Two decisions with real trade-offs arose:

**1. Thread model:** refex is pure-Python NLP (regex + state machine) and
does not release the GIL.  ThreadPoolExecutor gives no parallelism benefit
for CPU-bound work.  ProcessPoolExecutor spawns real OS processes and bypasses
the GIL, but requires all submitted functions to be pickleable — closures
defined inside a Snakemake `run:` block are not.

**2. Filter placement:** The false-positive filter (ADR 003 block-list) could
run in Stage 07 (before `refs_raw.json`) or in Stage 08 (after loading).
Filtering early reduces file size and keeps Stage 08 focused on resolution
logic.  Filtering late keeps Stage 07 simpler and preserves raw data for
debugging.

## Decision

**ProcessPoolExecutor** with `initializer=init_extractor`: creates one
`CitationExtractor` per worker process (expensive to construct, so done
once per process).  Worker function `process_law_file` lives in
`src/ref_extractor.py` (module-level → pickleable).

**Filter in Stage 07**, before writing to disk.  `refs_raw.json` contains
only post-filter citations.  Stage 08 receives clean input.

## Alternatives considered

- **ThreadPoolExecutor** — rejected: refex holds the GIL; threads give no
  speedup on CPU-bound extraction.  Would serialize all CPU work anyway.
- **Sequential processing** — viable for small corpora but unacceptable at
  6 000 laws × tens of norms each (estimated 10–30 min single-threaded).
- **Filter in Stage 08** — rejected: would bloat `refs_raw.json` by ~49 %
  (ADR 003 measured false-positive rate), and repeat the block-list logic
  every time Stage 08 re-runs.  Filtering once at the source is cleaner.

## Consequences

- Worker functions (`process_law_file`, `init_extractor`) must remain
  module-level in `src/ref_extractor.py`.  Do not move them into the
  Snakemake rule or any closure — they will silently fail to pickle.
- `refs_raw.json` is a flat list (not grouped by law).  Stage 08 groups
  by source in memory; at ~20 000–40 000 expected citations this is trivial.
- Per-norm refex exceptions are caught and skipped (not fatal); law-level
  JSON errors return an empty list.  Silent skips are acceptable because
  unresolvable norms contribute no edges anyway.
- Adding new false-positive words requires only a change to `FALSE_POSITIVES`
  in `ref_extractor.py` and a Stage 07 re-run (Stage 08 re-runs automatically
  as its input changed).
