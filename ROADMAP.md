# Roadmap

Staged plan to take openparagraph from empty repo to a launched v1, then beyond.
Estimates assume ~10–15 h/week (the "6 months, no pressure" track). Each stage
ends with a concrete, demoable deliverable. Don't start a stage before the
previous one's "Done when" is true.

Legend: 🔬 spike/research · 🐍 pipeline · 🎨 frontend · 🚀 ops

---

## Model & Effort Guide

Claude Code lets you switch model (`/model sonnet` / `/model opus`) and reasoning
effort (`/effort low|medium|high|xhigh|max`) mid-session. Use them deliberately —
each step up costs noticeably more quota.

**Rules of thumb for this project:**

- **Sonnet 4.6 + `medium`** — the daily driver. Routine code, scaffolding,
  refactoring, tests, straightforward UI work. Burns quota slowly.
- **Sonnet 4.6 + `high`** — anything where missing an edge case would hurt:
  parsers, validators, interaction logic, anything touching the dirty GII XML.
- **Opus 4.7 + `high`** — architectural decisions with real trade-offs, subtle
  algorithms (color blending, diff edge cases), debugging when Sonnet got stuck.
- **Opus 4.7 + `xhigh`** — the few "really think about this" moments: Spike B
  (FNA strategy), layout tuning for the spore look, the layout-stability
  problem in Stufe 5. Opus 4.7 defaults to `xhigh`; that's the recommended
  level for serious coding sessions.
- **`max`** — almost never. Reserve for one-shot decisions you'll commit to for
  months (e.g. final color-logic algorithm). Burns quota fast.
- **`low`** — file renames, "what does this do?", running a build. Don't use
  for anything you'd be annoyed about if it missed something.

**Trigger word shortcut:** typing `ultrathink` anywhere in a prompt
temporarily boosts that single response to high effort without changing the
session default. Useful when you want one careful response inside an otherwise
fast session.

Each stage below ends with a one-line recommendation: `→ Sonnet/medium` etc.
Treat it as a starting point, not a rule — escalate when you hit something
gnarly, downshift when you're doing boilerplate.

---

## Stufe 0 — Foundation & de-risking spikes
**~1–2 weeks. Goal: kill the three biggest unknowns before committing to the build.**

- 🚀 Monorepo scaffold (`/pipeline`, `/web`, `/data`, `/docs`), MIT license, `.gitignore`
- 🚀 `pyproject.toml` (uv) + `package.json` (pnpm) + `Snakefile` skeleton
- 🚀 `.devcontainer/devcontainer.json` for contributors; native WSL for daily dev
- 🚀 CI skeleton: lint + test on PR (no data build yet)
- 🔬 **Spike A — data shape:** download 10 laws via `gii-toc.xml`, parse XML, confirm
  metadata fields (`jurabk`, `ausfertigung-datum`, `langue`, norms structure).
- 🔬 **Spike B — FNA acquisition:** prototype FNA→law mapping for ~50 laws. Decide:
  buzer.de scrape vs BMJ PDF parse vs hybrid. **This is the riskiest unknown.**
- 🔬 **Spike C — references:** run `legal-reference-extraction` on 5 laws, measure
  recall by hand, prototype the `normalized ref → node id` resolver.

**Done when:** all three spikes produce a working prototype output file and you've
written a one-paragraph decision note per spike in `/docs`.

→ **Scaffolding work:** Sonnet/medium. **Spikes A & C:** Sonnet/high (XML reality
and parser recall are detail-heavy). **Spike B (FNA):** Opus/xhigh — this is the
single most strategic decision in the project; let it think.

---

## Stufe 1 — Pipeline backbone
**~3–4 weeks. Goal: every law as a node, every reference as an edge — no styling yet.**

- 🐍 Snakemake stages 01–08 (download → parse → classify → extract → resolve refs)
- 🐍 Emit `nodes.json` (~6000) + `edges.json` with raw structural references
- 🐍 Stage 17 validation: counts, dangling-resolver check, schema assertions
- 🐍 Graph sanity report: node/edge counts, degree distribution, orphan count

**Done when:** `snakemake bundle` produces valid node/edge JSON for the full
corpus and the validation stage passes.

→ **Most stages:** Sonnet/medium (each stage follows the same Snakemake pattern,
mostly straightforward). **The XML parser and reference resolver (stages 04, 08):**
Sonnet/high — defensive parsing of dirty input is where bugs hide. **If a stage
gets stuck after 2-3 tries:** escalate to Opus/high.

---

## Stufe 2 — Layout & color
**~2–3 weeks. Goal: the data has positions and meaning, verifiable as a static PNG.**

- 🐍 Stage 09–10: distiluse embeddings + orphan top-K neighbors → soft edges
- 🐍 Stage 12: `fa2_modified` layout on the union graph (tune for the spore look)
- 🐍 Stage 13: three-rule color logic (9 FNA groups + bridging + orphan blend)
- 🐍 Debug render: matplotlib/datashader PNG of the colored layout to eyeball clusters

**Done when:** the debug PNG visibly shows distinct, sensibly-colored clusters
(you can recognize a civil-law clump, a tax clump, etc.).

→ **Embeddings + orphan neighbors:** Sonnet/medium (mostly library glue).
**Layout tuning (the spore aesthetic):** Opus/xhigh — FA2 parameters are subtle
and interact; you want a model that reasons about visual outcomes from numeric
inputs. **Color logic (three-rule blending):** Opus/high — HSL blending with
proportional weights has edge cases (what if all neighbors are the same color?
what if a law has zero references?) you want thought through up front.

---

## Stufe 3 — Frontend graph shell
**~3–4 weeks. Goal: the graph is live in a browser and deployed.**

- 🎨 Vite + TS + sigma.js + graphology project
- 🎨 Load nodes/edges, render with FA2 positions and FNA colors
- 🎨 Camera, zoom, pan; BGB start-zoom + dismissible hint
- 🎨 Dark aesthetic: node glow, ~0.1 edge opacity
- 🚀 Deploy to Vercel; wire the data-refresh GitHub Action (weekly)

**Done when:** the live URL shows the interactive, navigable, colored graph.

→ **Vite setup + sigma.js scaffolding:** Sonnet/medium. **Camera + zoom +
interaction primitives:** Sonnet/high (small bugs here ruin the UX). **Deploy
config + GH Action wiring:** Sonnet/medium.

---

## Stufe 4 — Interaction & detail view
**~3–4 weeks. Goal: the graph becomes a tool, not just a picture.**

- 🎨 Click node → sidebar with rendered full text + table of contents
- 🎨 Clickable `§` references → camera flies to target node + opens it
- 🎨 FlexSearch + highlight UX (brighten matches, dim the rest via node reducer)
- 🐍 Stage 15: ship the serialized search index

**Done when:** you can search "Mietrecht", click a result, read the law, click a
referenced `§`, and land on the right node.

→ **Sidebar layout + text rendering:** Sonnet/medium. **Reference resolver +
fly-to-node logic:** Sonnet/high (where unresolved refs get handled gracefully,
where camera animation lives — classic edge-case territory). **FlexSearch +
node-reducer highlight pattern:** Sonnet/high — node reducers in sigma.js have
subtle perf traps you want a thoughtful pass on.

---

## Stufe 5 — Time axis & versions
**~3–4 weeks. Goal: the "git" promise becomes visible.**

- 🐍 Stage 14: per-law base.html + forward patches from `kmein/gesetze` git history (2021+)
- 🎨 Global time slider (filter visibility by `created_at`/`repealed_at`)
- 🎨 Per-law version timeline + paragraph-level diff viewer (diff-match-patch)
- 🎨 Honest UI note: fine-grained diffs start ~2021

**Done when:** dragging the slider grows/shrinks the corpus over the decades, and
a law with post-2021 changes shows a working paragraph-level diff.

→ **Diff cache stage:** Sonnet/high — diff-match-patch chain correctness matters
(a broken patch breaks reconstruction for that law forever). **Time slider
filtering logic:** Sonnet/medium. **Layout-stability problem** (decoupling
weekly data refresh from layout recompute, seeding new positions from previous
ones — see ARCHITECTURE.md risk A): Opus/xhigh — this is the trickiest design
problem in the project after Spike B; give it the room. Use `ultrathink` for
the moment you actually design the seeding mechanism.

---

## Stufe 6 — Polish & v1 launch
**~2–3 weeks. Goal: portfolio-grade, launch-ready.**

- 🎨 Loading/empty/error states, legend, about page, onboarding hint
- 🎨 Performance pass (reducer throttling, lazy text fetch if needed)
- 🚀 README polish: screenshots, demo GIF, quick-start, contributing guide
- 🚀 Launch: Show HN, r/de / r/recht, Mastodon, link from the Malt profile

**Done when:** a stranger can land on the URL, understand it in 10 seconds, and
explore without instructions.

→ **All of it:** Sonnet/medium. Polish work is high-volume, low-stakes-per-task —
exactly the regime where Sonnet shines. **One exception:** the performance pass.
If you hit an actual perf problem, escalate that single investigation to
Opus/high — perf debugging rewards careful reasoning about what's actually
expensive.

---

## Post-v1

### v1.1 — accessibility of reach (~2–3 weeks)
- Mobile-responsive layout (S-Bahn-friendly)
- Multi-language UI (DE/EN toggle)

### v2 — breadth (~2–3 months)
- DE Bundesverordnungen + Landesrecht (16 states; per-state classification mapping)
- DIP integration (`api.dip.bundestag.de`) → draft stages as **branches**
- Incremental pipeline (beat the GH Actions 6h limit)
- Chunked storage + lazy loading

### v3 — Europe (~open-ended)
- EU law via EUR-Lex (CELEX ids; EuroVoc → meta-taxonomy mapping)
- Renderer port to cosmos.gl if sigma.js stalls past ~100k nodes
- GPU layout (cuGraph / Datashader)

### v4 — the full corpus
- Court decisions, administrative regulations (500k+ nodes)

---

## Critical path (the spine you can't parallelize)

```
Stufe 0 spikes  →  Stufe 1 backbone  →  Stufe 2 layout/color  →  Stufe 3 shell
                                                                      │
                          Stufe 4 interaction  ←──────────────────────┘
                                   │
                          Stufe 5 time/versions  →  Stufe 6 launch
```

Everything hinges on Stufe 0 Spike B (FNA). If FNA acquisition turns out to be
genuinely hard, fall back to: ship v1 with embedding-derived clusters as the
*primary* color signal and FNA as a later enhancement. The architecture already
supports orphan→embedding gravitation, so this is a graceful degradation, not a
redesign.
