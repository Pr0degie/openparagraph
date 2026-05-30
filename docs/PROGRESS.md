# PROGRESS

> The single source of truth for "where are we?" Claude updates this at the end
> of every working session. Read it at the start of every new session.
>
> If you find yourself with stale or contradictory information, trust `git log`
> and the actual state of `/data` and `/pipeline` over what this file claims.

---

## Current stage
**Stufe 1 — Pipeline backbone** (Stage 01 + 02 implemented)

## Last session
2026-05-30. Implemented **Stage 01 (download_toc) + Stage 02 (download_laws)** as real Snakemake rules.
New files:
- `pipeline/src/toc_parser.py` — `parse_toc_xml()` (pure, tested)
- `pipeline/src/downloader.py` — `fetch_law_xml()` (thin HTTP wrapper)
- `pipeline/rules/01_download_toc.smk` — fetches gii-toc.xml → `build/toc.json`
- `pipeline/rules/02_download_laws.smk` — parallel download of ~6000 xml.zips →
  `build/laws_xml/{slug}.xml` + `build/slug_table.json`; resumable (skips existing XMLs)
- `pipeline/tests/test_toc_parser.py` — 5 new tests, all green (28 total)
- Snakefile stubs replaced with `include:` — DAG dry-run verified
- `resolve_refs` stub updated to declare `slug_table.json` as input

## Next concrete step
**Stage 07 (extract_refs) + Stage 08 (resolve_refs).**

Stage 07: run `refex` over each law's norm text (from `laws_parsed/{slug}.json`),
apply the false-positive block-list, write `build/refs_raw.json` —
list of `{source_slug, book, section}` raw citations.

Stage 08: load `slug_table.json`, build `jurabk_index` (normalized_jurabk → slug),
normalize each raw citation's book field, look up slug, emit
`build/edges_structural.json` + `data/_global/reference-resolver.json`.

Both stages build directly on Spike C's prototype code.

## Open questions / parked thoughts
- Stage 05 work for later: lift FNA PDF coverage past 53.5% via fuzzy/token title
  matching + FNA-abbr↔jurabk join; pull code→Sachgebiet-name taxonomy tree from
  PDF front matter; add buzer enrichment behind a slow cached crawler.
- ZIP files can contain non-XML entries (images). Spike scripts filter `.xml` only.
- buzer may keep blocking this IP; the buzer prototype is expected to hit the 403
  gateway block from a cold IP (documented, not a bug).
- "einführungsgesetz" (66 citations from BGB): need a context-aware disambiguation
  table (BGB→BGBEG, StGB→EGStGB, etc.) for Stage 08.
- `data/spike_c/resolver_proto.json` (14 427 entries) is a useful starting point
  for the Stage 02 slug_table; slug-to-slug identity layer is already correct.

## Stage checklist
- [x] Stufe 0 — Foundation & de-risking spikes
  - [x] Monorepo scaffold (dirs, pyproject, package.json, Snakefile skeleton, CI)
  - [x] Spike A — data shape
  - [x] Spike B — FNA acquisition
  - [x] Spike C — reference extraction
- [ ] Stufe 1 — Pipeline backbone
  - [x] Stage 01 download_toc (build/toc.json)
  - [x] Stage 02 download_laws (build/laws_xml/ + build/slug_table.json)
  - [x] Stage 04 parse_laws (build/laws_parsed/ — JSON + HTML per law)
  - [x] Stage 05 scrape_fna (build/fna_map.json — PDF primary, resumable)
  - [x] Stage 06 classify (build/laws_classified.json — fna_code + main_group + opening_text)
- [ ] Stufe 2 — Layout & color
- [ ] Stufe 3 — Frontend graph shell
- [ ] Stufe 4 — Interaction & detail view
- [ ] Stufe 5 — Time axis & versions
- [ ] Stufe 6 — Polish & v1 launch
