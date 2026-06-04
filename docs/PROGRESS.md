# PROGRESS

> The single source of truth for "where are we?" Claude updates this at the end
> of every working session. Read it at the start of every new session.
>
> If you find yourself with stale or contradictory information, trust `git log`
> and the actual state of `/data` and `/pipeline` over what this file claims.

---

## Current stage
**Stufe 5 — Time axis & versions** — macro time slider shipped with full
**birth *and* death** semantics, plus a round of **visual/UX tuning** on top.
Dual-range year slider (delivered via Ultraplan on branch `stufe5-time-slider`)
dims nodes outside the window; extended so the filter uses real lifespan
interval-overlap (`created_at` .. `repealed_at`). Pipeline now extracts
`repealed_at` from the source XML (was hardcoded `None`). Then, from live user
feedback: 2.5D back to discrete FNA layers, opaque spheres + depth-tested labels,
large-only permanent labels (others on hover), a live tuning panel, and 3D
centre-gravity + softened repulsion. Then (2026-06-03): fixed a 3D black-screen
race and added the **Saturn ring** — the ~46% unclassified laws are pinned to a
thin tilted annulus around the force cloud so the central clusters read (ADR 015).
Branch `stufe5-time-slider`; **committed, not merged**. Live visual eyeball ongoing
with the user (build/tests green).

## Last session
2026-06-03. **3D black-screen fix + Saturn ring for unclassified laws.**

Branch `stufe5-time-slider`. Two web-only changes (`web/src/main.ts`), each
verified in a headless Chromium probe (no `pageerror` in 3D/2.5D/2D):

- **3D black-screen race fix (commit `9ff51cc`).** The 3D force tuning from
  `6fdd772` called `Graph.d3ReheatSimulation()` synchronously right after
  `graphData()`. That flips `engineRunning=true` and starts the tick loop, but
  3d-force-graph only assigns `state.layout` at the end of the *deferred* graphData
  digest (next frame). The race fired `layoutTick` before `state.layout` existed →
  `Cannot read properties of undefined (reading 'tick')` → dead render loop → black
  screen. Fix: keep registering the custom charge/gravity forces but **drop the
  init-time reheat**; the engine starts itself after the digest and picks them up.
- **Saturn ring (ADR 015).** The 2806 unclassified laws (`main_group === null`,
  46%) drowned the clusters. Now pinned via `fx/fy/fz` to a thin tilted annulus
  (`ringPos(i)`: golden-angle + decorrelated radius/z, default radius 400 / width 60
  / tilt 0.35); classified nodes stay force-driven in the centre. Ring nodes are
  **de-emphasised** (shrunk by `tuneRingDim`, recoloured muted slate `#3a3a44` in
  `applyHighlight`, still opaque) unless search-matched. **Camera fits the clusters
  only** — 3D `zoomToFit` passes a node filter to `getGraphBbox` excluding the ring.
  Five new live sliders (radius/width/thickness/tilt/dim) via a new `applyRing()`.
- TS strict / `pnpm typecheck` green; geometry verified (annulus radius 370–430, no
  NaN). 2D/2.5D untouched. Default cloud↔ring gap is tight — left to live tuning.

## Last session (Stufe 5 birth/death + visual tuning, commit `6fdd772`)
2026-05-31. **Stufe 5 — birth/death time filter + `repealed_at` extraction, then
a visual/UX tuning round from live user feedback.**

Branch `stufe5-time-slider` (Ultraplan delivered the base dual-range slider as
`46541b2`; this session added the death dimension end-to-end, then visual fixes).

**Visual / UX (web/src/main.ts, ui.ts, style.css) — from user feedback:**
- **2.5D = discrete FNA layers** again (not the continuous PCA `z`, which read as
  "Kuddelmuddel"). `applyHighlight`'s 2.5D z uses `zFromMainGroup`. See ADR 012.
- **Spheres never transparent** — dimmed nodes go solid dark (`#23232b`,
  opacity 1) instead of see-through. See ADR 013.
- **Label occlusion** — label sprites `depthTest:true` (front sphere hides rear
  label); labels float above the *scaled* sphere so a node never hides its own.
- **Label visibility** — only "large" nodes (size ≥ `tuneLabelThreshold`, def 7.5)
  show a permanent label; the rest reveal theirs on hover. See ADR 013.
- **Tuning panel** (`initTunePanel`) — collapsible live sliders w/ numeric readout:
  sphere sizes, label threshold/offset, node/layer spacing (2D/2.5D), centre-gravity
  + repulsion (3D). Mode-aware spec. See ADR 014.
- **3D forces** — custom `centerGravityForce` (hand-rolled d3 force pulling nodes
  to origin, default 0.18) + softened `charge` repulsion (12 vs ~30). Live-tunable.
  Position changes apply via `d3ReheatSimulation()` (the lib only rewrites object
  positions inside `layoutTick`, which stops after cooldown). See ADR 014.
- All TS strict, `pnpm typecheck`/`build` green; 11 vitest still green.

**Pipeline + frontend `repealed_at` (the Stufe-5 core):**

- **Pipeline `repealed_at`** (was `graph_builder.py:59` hardcoded `None`):
  new `parse_repeal_date` + `extract_repealed_at` in `gii_parser.py` read the
  `<standangabe><standtyp>Aufh</standtyp><standkommentar>` block via an
  **anchor-based regex** (`mit Ablauf` / `mWv` / `am … außer Kraft` /
  `bis zum … verlängert`), deliberately ignoring the amending-act `v. DATE`
  citation. New `Law.repealed_at` field threaded through `law_serializer.py:45`
  → `classifier.py:65` → `graph_builder.py:59`; stages 12/13 pass it through via
  `{**node}` spread. See **ADR 011**.
- **Coverage**: 130/6124 laws carry an Aufh block; **108** yield a parseable
  date, 22 stay `None` (conditional/partial repeals). Verified in
  `data/de-bund/nodes.json` (108 non-null). Spot-checks: BattG → 2026-08-18
  (latest mWv of a selective repeal), AugOptMstrV → 2026-07-01 (trap avoided).
- **Frontend**: extracted pure `web/src/timefilter.ts` (`parseYear`,
  `isInTimeWindow`); `applyHighlight` in `main.ts` now uses interval-overlap
  `[born, death] ∩ [from, to]` (null death = open-ended). **Behaviour change
  (intended):** laws born before `from` but still alive are now shown, not dimmed.
- **Tests**: pipeline 218 pytest green (new `parse_repeal_date` parametrisation +
  pass-through asserts + `sample_repealed_law.xml` fixture); frontend 11 new
  vitest in `timefilter.test.ts` (first frontend tests — `pnpm test` now passes
  instead of "no test files"). `pnpm typecheck` + `pnpm build` green.
- **Re-run note**: `--forcerun parse_laws build/laws_classified.json` is variadic
  and swallowed the file as a second force-item → no explicit target → Snakemake
  rebuilt the default `bundle` (full pipeline). Harmless (deterministic layout,
  same coords) but re-embedded needlessly. To target just classify, pass the
  file as a positional **before** `--forcerun`, or use `--until`.

## Last session (Stufe 4 — Interaction & detail view, commit `67ea97e`)
2026-05-31. **Stufe 4 — Interaction & detail view (commit `67ea97e`).**

New files: `web/src/ui.ts` (tooltip, detail panel, search box, banner).
Refactored `web/src/main.ts` + `style.css`. Key changes:

- **Hover tooltip**: custom HTML div tracking mouse via `onNodeHover`;
  suppresses 3d-force-graph's native title-attr tooltip.
- **Detail panel**: slide-in right sidebar (300 px, CSS transform transition).
  Shows jurabk (coloured left-border), full title, FNA code, cluster,
  dates, degree, outgoing + incoming ref chips (≤25, +N overflow).
  Ref chips are clickable → fly camera to that node.
- **Search / highlight**: pill input (center-top), `/` keyboard shortcut
  focuses it, `Esc` clears. Simple substring match over jurabk+title
  (~3 ms for 6124 nodes). Hit nodes keep colour; rest dims to #1a1a22 @
  22% opacity by imperatively updating `nodeFillMats` Map (MeshBasicMaterial).
- **Fly-to**: 2D mode rotates camera 90° left (side-on from −x) with
  `noRotate` unlocked and an "↑ Übersicht" button to reset top-down.
  2.5D/3D flies to dist-120 offset sphere around the node.
- **Smooth controls**: `enableDamping=true`, `dampingFactor=0.07`,
  `zoomSpeed=0.35`, `rotateSpeed=0.45` — three-forcegraph calls
  `controls.update()` each frame so damping works without a second loop.
- **Node labels**: OffscreenCanvas sprites floating above spheres; rely on
  Three.js `sizeAttenuation` for zoom-threshold effect (tiny when zoomed
  out, readable when zoomed in — no per-frame JS).
- Added `@types/three 0.184.1`; removed `declare module 'three'` override
  that was blocking proper type resolution.

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
Stufe-5 work is **committed** on `stufe5-time-slider` (`6fdd772` core, `9ff51cc`
3D fix, plus today's ring commit). Not merged. There may still be a stray untracked
`stufe5timeslider.patch` (teleport artifact) that can be deleted.

1. **Finish the visual eyeball / tuning** on the dev server
   (`http://<wsl-ip>:5174`, branch `stufe5-time-slider`): the user was dialling in
   the tuning-panel sliders (sphere sizes, label threshold/offset, 2.5D layer +
   node spacing, 3D centre-gravity + repulsion, **and now the 5 Saturn-ring
   sliders**). Default cloud↔ring separation is tight — likely wants a larger ring
   radius or stronger centre-gravity. **Once they settle on values they like, bake
   them in as the new defaults** (the `tune*` consts in `main.ts`) and decide
   whether to keep the tuning panel as dev-only or hide it for v1.
2. Time slider: consider a label like "existierte zwischen" to convey the
   lifespan-overlap semantics. Verify future range (2027–2030) dims repealed laws.
3. **Commit + merge** `stufe5-time-slider` → `main`. Note: local `main` already
   carries an equivalent teleported commit `1a4c292` (base slider only, no
   `repealed_at`) — reconcile when merging.
4. Then **Stufe 6 — Polish & v1 launch** (perf, a11y, deploy, CI smoke test), and
   the still-open Stufe-5 tail: Stage 14 version history + per-law diff viewer.

## Open questions / parked thoughts
- **Ring still covers the clusters too much (user, 2026-06-04).** The Saturn ring
  of unclassified laws (ADR 015) is better than scattering, but the user is **not
  yet satisfied** — the unclassified nodes still obscure the central clusters too
  much. Wants to change something here in a future session. Not yet decided what;
  candidate levers: larger default ring radius / stronger centre-gravity so the
  cloud is more compact, a tighter cluster-only camera fit, smaller/dimmer ring
  nodes (`tuneRingDim`), or moving the ring further out of the cluster's view cone.
- **⚠️ Layout (Stage 12 / FA2) is NOT reproducible across runs.** Discovered this
  session: a full rebuild moved all 6124 x/y coords (max ~39k units) even though
  node set, edges, embeddings and the seed were unchanged. The z-axis (PCA from
  embeddings) IS deterministic — only the 2D FA2 step drifts. This contradicts
  CLAUDE.md golden rule ("layout seed reproduces coordinates") and the prior
  session's note about passing explicit `pos=`. Likely a residual nondeterminism
  in `fa2_modified` (BLAS thread order / dict iteration) the seed doesn't pin.
  Worked around for now by **not** committing the re-layout: `nodes.json` was
  patched to add only the 108 `repealed_at` values onto the committed coords;
  `layout.json` left at HEAD. Needs a real fix before any future full rebuild
  (pin BLAS threads = 1, or persist+reuse layout.json as the seed of record).
- DONE: Stage 15 `search_index` already emits `search-index.json`; frontend
  search now works via simple substring match (fast enough, ~3 ms). FlexSearch
  import is in deps but not used — could swap in later for fuzzy/prefix search.
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
- [x] Stufe 4 — Interaction & detail view (tooltip, panel, search, fly-to, smooth controls, labels)
- [~] Stufe 5 — Time axis & versions
  - [x] Dual-range time slider, birth/death interval-overlap
  - [x] `repealed_at` extraction (Stage 04/06/11) — ADR 011
  - [x] Visual tuning: discrete 2.5D layers, opaque spheres, labels, tuning panel, 3D gravity — ADRs 012–014
  - [ ] Stage 14 version history (kmein/gesetze patches) + per-law paragraph diff viewer
- [ ] Stufe 6 — Polish & v1 launch
