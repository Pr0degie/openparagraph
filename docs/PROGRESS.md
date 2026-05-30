# PROGRESS

> The single source of truth for "where are we?" Claude updates this at the end
> of every working session. Read it at the start of every new session.
>
> If you find yourself with stale or contradictory information, trust `git log`
> and the actual state of `/data` and `/pipeline` over what this file claims.

---

## Current stage
**Stufe 2 — Layout & color** (Stages 09–13 complete — Stufe 2 done)

## Last session
2026-05-30. Implemented **Stages 09, 10, 11 (updated), 12** in one block.
New files:
- `pipeline/src/embedder.py` — `texts_for_embedding()` + `embed()` (sentence-transformers)
- `pipeline/src/orphan_neighbors.py` — `orphan_indices()` + `compute_soft_edges()` (cosine KNN)
- `pipeline/src/layout_builder.py` — `build_nx_graph()` + `run_layout()` (fa2_modified)
- `pipeline/rules/09_embed.smk` — laws_classified → build/embeddings.npy
- `pipeline/rules/10_orphan_neighbors.smk` — embeddings + classified → build/edges_soft.json
- `pipeline/rules/12_layout.smk` — graph_nodes + edges → data/_global/layout.json
- Stage 11 updated: now takes edges_structural + edges_soft as union input
- 160 tests green; DAG dry-run: full 11-rule chain 01→02→04→05→06→07→08→09→10→11→12 verified

Key decisions:
- Row order in embeddings.npy = sorted(laws_classified.keys()) — no companion slug file needed
- FA2 initial positions generated via np.random.default_rng(seed) on sorted node IDs for
  full reproducibility (fa2_modified uses networkx's internal RNG when pos=None, ignoring
  np.random.seed — fixed by passing explicit pos=)

## Last session (Stage 13)
2026-05-30. Implemented **Stage 13 (color)**.
New files:
- `pipeline/src/color_builder.py` — `hsl_to_hex`, `blend_hsl` (circular hue mean), `assign_colors`
  (two-pass: classified first, orphans second), `merge_layout`, `build_meta_taxonomy`
- `pipeline/rules/13_color.smk` — graph_nodes + layout + edges → data/de-bund/nodes.json
  + data/_global/meta-taxonomy.json
- `pipeline/tests/test_color_builder.py` — 27 tests, all green (187 total)
- Snakefile stub replaced with `include: "rules/13_color.smk"`
- DAG dry-run: full 12-rule chain through Stage 13 verified

Key decisions:
- Palette (9 HSL base hues) hard-coded in color_builder.py as module constants — will be
  superseded when FNA taxonomy PDF is fully parsed (Stage 05 enrichment, parked).
- meta-taxonomy.json is also output of Stage 13 (frontend needs group→color mapping).
- Bridging blend: only hard out-edge target groups count; own group has no self-weight.
- Orphan color: equal-weight blend of soft-edge neighbours' HSL (weight from edge dict).
  Orphans with no resolvable neighbours get neutral slate (#ORPHAN_HSL).

## Next concrete step
**Stufe 3 — Frontend graph shell.**
Start with `web/` scaffold: Vite + TypeScript + sigma.js v3 + graphology.
First milestone: load `data/de-bund/nodes.json` + `data/_global/edges.json` + `data/_global/layout.json`
and render the graph with correct colors and sizes — no interaction yet.

Steps:
1. `web/src/data.ts` — typed loader for nodes.json + edges.json + layout.json
2. `web/src/graph.ts` — build graphology MultiGraph from loaded data
3. `web/src/main.ts` — mount sigma.js renderer with node reducers for color/size
4. Verify: `pnpm dev` renders ~6000 nodes on dark background

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
  - [x] Stage 07 extract_refs (build/refs_raw.json — ProcessPool refex + FP filter)
  - [x] Stage 08 resolve_refs (build/edges_structural.json + data/_global/reference-resolver.json)
  - [x] Stage 11 build_graph (build/graph_nodes.json + data/_global/edges.json)
- [ ] Stufe 2 — Layout & color
  - [x] Stage 09 embed (build/embeddings.npy)
  - [x] Stage 10 orphan_neighbors (build/edges_soft.json)
  - [x] Stage 11 updated (hard + soft edge union)
  - [x] Stage 12 layout (data/_global/layout.json)
  - [x] Stage 13 color (data/de-bund/nodes.json + data/_global/meta-taxonomy.json)
- [ ] Stufe 3 — Frontend graph shell
- [ ] Stufe 4 — Interaction & detail view
- [ ] Stufe 5 — Time axis & versions
- [ ] Stufe 6 — Polish & v1 launch
