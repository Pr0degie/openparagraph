# PROGRESS

> The single source of truth for "where are we?" Claude updates this at the end
> of every working session. Read it at the start of every new session.
>
> If you find yourself with stale or contradictory information, trust `git log`
> and the actual state of `/data` and `/pipeline` over what this file claims.

---

## Current stage
**Stufe 3 — Frontend graph shell** — DONE, plus a major mid-stream pivot:
the renderer moved from sigma.js (2D-only) to a **single Three.js renderer
(3d-force-graph)** serving **2D / 2.5D / 3D** views, and the pipeline grew a
**semantic z-axis**. Next up is Stufe 4 (interaction) on the new renderer.
Branch: `spike/3d-view` (no longer a throwaway — our feature branch; not yet
merged to main).

## Last session
2026-05-31 (later). **3D renderer migration + pipeline z-axis (ADR 009).**

Decided one renderer for all three views (see `docs/decisions/009-single-renderer-3d.md`).
Three commits on `spike/3d-view`:
- `76076ee` pipeline(layout): retune FA2 (scaling_ratio 2→8, gravity 1→0.3,
  adjust_sizes) to stop the core clumping — regenerated layout/nodes.
- `ceb0354` web(render): replace sigma.js + graphology with 3d-force-graph
  (Three.js). Spike → `web/src/main.ts`; old sigma trio archived under
  `web/archive/sigma-2d/` (not deleted). Flat MeshBasic + dark BackSide outline
  reproduces the sigma 2D look; 2D mode is camera-locked top-down, no rotation.
  View toggle via `#mode=2d|2.5d|3d`. Bundle ~1 MB (three.js).
- `11b5e4f` pipeline(layout): semantic z from PCA of stage-09 embeddings
  (`pca_z`, deterministic SVD). Stage 12 injects z when `layout.dimensions=3`;
  `merge_layout` copies it; all 6124 nodes now have z (std 6000 ≈ x/y). 43 tests.

Docs: ADR 009 created; ARCHITECTURE §3/4/5/7/8/9/11 + ROADMAP updated.

App now at `/` (not `/spike.html`); dev server bound to 0.0.0.0 + Vite polling
(WSL `/mnt/c` HMR fix). Verified renders headless via the bundled Chromium at
`~/.cache/ms-playwright/chromium-1223/`.

## Last session (Stufe 3 scaffold)
2026-05-31. **Erste End-to-End-Ausführung der Pipeline + Stage-07-Bugfix.**

**Frontend scaffold (Stufe 3):**
- `web/tsconfig.json`, `web/vite.config.ts`, `web/index.html`
- `web/src/types.ts`, `data.ts`, `graph.ts`, `main.ts`, `style.css`
- `web/pnpm-workspace.yaml` — pnpm 11 esbuild approval
- `web/public/data/` — 20-Node/20-Edge Fixtures für Dev ohne Pipeline
- Vite dev middleware: `../data/*` → `/data/*` (echte Daten haben Vorrang vor Fixtures)
- `pnpm build` sauber: 28 Module, 162 KB JS, TypeScript strict

**Pipeline-Ausführung Stages 01–13:**
- Stage 01–06, 08–13 liefen problemlos durch
- Stage 07 (extract_refs) hing zwei Mal mit hängenden Worker-Prozessen
- Fix: `pebble.ProcessPool` mit `timeout=60` (tötet Worker-Prozess tatsächlich; `concurrent.futures`-Timeout tut das nicht) — siehe ADR 008

**Endergebnis:**
- `data/de-bund/nodes.json` — 6 124 Gesetze mit x/y/color/size
- `data/_global/edges.json` — 20 091 Kanten
- `data/_global/layout.json`, `meta-taxonomy.json`, `reference-resolver.json`

## Last session (prior)
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
1. Eyeball the three views in a real browser (`cd web && pnpm dev`, open
   `http://<wsl-ip>:5173/#mode=2d|2.5d|3d`); tune `z_scale` / `NODE_R` if needed.
2. Decide on merging `spike/3d-view` → `main` (squash or keep the 3 commits).
3. Then **Stufe 4 — Interaction & detail view** on the Three.js renderer:
   hover tooltip (jurabk + title) + click → detail panel; search highlight via
   node-color/opacity accessors; ref fly-to via `cameraPosition`.

## Open questions / parked thoughts
- `rule search_index` (Stage 15) is still a `run: pass` STUB → it fails on
  `output: search-index.json`, so a full `snakemake` (default target → bundle)
  can't complete. Pre-existing, not a regression. Build the FlexSearch serialize
  in Stufe 4, or mark the rule's output `touch()`-only until then.
- z visual tuning: `z_scale=6000` ≈ x/y std; frontend `POS_SCALE=20` divides both.
  Might want the 2D→3D "lift" animation (single-renderer benefit) in Stufe 4/6.
- Real production view-switcher UI (the current banner is a minimal spike toggle);
  pick the default landing view (currently 2.5d).
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
- [x] Stufe 3 — Frontend graph shell (scaffold + real pipeline data: 6124 nodes, 20091 edges)
- [ ] Stufe 4 — Interaction & detail view
- [ ] Stufe 5 — Time axis & versions
- [ ] Stufe 6 — Polish & v1 launch
