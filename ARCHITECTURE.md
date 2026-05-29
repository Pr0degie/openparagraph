# Architecture

> Technical reference for **openparagraph** — a visual git for German law.
> This document is the single source of truth for design decisions. If you change
> a decision, change it here first.

---

## 1. What this is

openparagraph renders the entire corpus of German federal law as an interactive
force-directed graph. Each law is a node; each statutory cross-reference
(`§ 433 BGB → § 90 BGB`) is an edge. Nodes are colored by legal domain and
positioned so that densely cross-referencing laws cluster together organically —
the "fungal-spore" look of a ForceAtlas2 layout. Clicking a node opens the full
text with clickable references and a version timeline.

The "git" framing is literal: the underlying data is versioned, the time slider
walks the corpus through history, and a later milestone introduces draft stages
(Referentenentwurf → Regierungsentwurf → … → Verkündung) as branches.

---

## 2. Hard constraints discovered during research

These are facts about the data world that shape everything downstream. Read them
before proposing changes.

### 2.1 Version history only reaches back to ~April 2021
The git-tracked law repositories (`kmein/gesetze`, daily auto-updates;
`bundestag/gesetze`, partly manual) only started recording per-change history
around **April 2021**. There is **no** machine-readable archive of consolidated
intermediate versions before that.

Consequence — the time dimension splits into two layers:

| Layer | Source | Coverage |
|---|---|---|
| **Macro** — laws appearing / being repealed over decades | `ausfertigung-datum` in GII XML metadata (BGB = 1896-08-18) | Full history |
| **Micro** — fine-grained version diffs per law | git history of `kmein/gesetze` | ~April 2021 → today |

So: the global time slider that "grows the legal system over the decades" works
(node birth/death). The per-law diff timeline is rich only for the last ~5 years.
This is documented honestly in the UI; do not promise pre-2021 diffs.

### 2.2 The corpus is ~6,000+ laws, not 5,000
`gii-toc.xml` lists **>6,000** acts (laws + regulations). Plan node counts and
storage accordingly.

### 2.3 FNA classification is not in the per-law XML
The Fundstellennachweis A (FNA) — the official legal-domain taxonomy — is
published by the BMJ as **annual PDF only** (since 2005). The per-law GII XML
contains `fundstelle` but not a reliable FNA Sachgebiet code. The FNA has
**nine** main divisions (Hauptgliederungspunkte), not eight.

Acquisition options (resolved by Spike B in Stufe 0):
- **buzer.de** mirrors the FNA tree in browsable HTML (`buzer.de/fna/<code>.htm`) — scrape-friendly.
- BMJ annual PDF (`recht.bund.de/.../FNA_<year>.pdf`) — authoritative but PDF-parsing pain.
- Cross-reference both to maximize coverage; fall back to "unclassified → embedding gravitation" for the remainder.

---

## 3. System overview

```
                      ┌─────────────────────────────────────────┐
                      │  GitHub Actions (scheduled, e.g. daily)   │
                      └──────────────────┬────────────────────────┘
                                         │ runs
                      ┌──────────────────▼────────────────────────┐
                      │  Snakemake pipeline (Python)                │
                      │                                             │
   gii-toc.xml  ─────▶│  download → parse → classify(FNA)           │
   kmein/gesetze ────▶│  → extract-refs → embed → neighbors         │
   buzer.de (FNA) ───▶│  → build-graph → layout(FA2) → color        │
                      │  → diff-cache → search-index → bundle        │
                      └──────────────────┬────────────────────────┘
                                         │ writes /data/**.json + commits
                      ┌──────────────────▼────────────────────────┐
                      │  Static frontend (Vite + TS + sigma.js)     │
                      │  served from Vercel / Netlify / GH Pages    │
                      └─────────────────────────────────────────────┘
```

No server. No database. No Docker in production. The pipeline produces static
artifacts; the frontend is a static bundle that fetches them.

---

## 4. Tech stack & rationale

| Layer | Choice | Why this over alternatives |
|---|---|---|
| Pipeline language | **Python 3.12** | Best ecosystem for XML, graphs, embeddings, ML |
| Orchestration | **Snakemake** | Incremental re-runs (skip unchanged stages); standard in data/research OSS |
| Reference parsing | **`legal-reference-extraction`** (openlegaldata) | Maintained, normalizes `§ 211 Absatz 1 des Strafgesetzbuches` → `§ 211 Abs. 1 StGB`; used in production. Beats hand-rolled regex. |
| Embeddings | **`sentence-transformers` / `distiluse-base-multilingual-cased-v2`** | CPU-runnable on ~6k docs in minutes; multilingual = no model swap when EU law arrives |
| Layout | **`fa2_modified`** (pure-Python ForceAtlas2, Barnes-Hut + Cython) | Eliminates the Java/Gephi-Toolkit dependency entirely. Reproducible, Snakemake-native. |
| Graph data structure | **graphology** | Required companion to sigma.js |
| Renderer | **sigma.js v3** (WebGL) | Battle-tested since 2014, node-reducer API fits the highlight UX, handles 6k nodes trivially |
| Diff engine | **diff-match-patch** | Tiny client-side lib; reconstructs versions from base + forward patches |
| Search | **FlexSearch** | Fastest client-side full-text index; title + short description |
| Build tool | **Vite** + TypeScript | Fast HMR, static output |
| Hosting | **Vercel** (or Netlify / GH Pages) | Free static hosting, auto-rebuild on data commit |
| CI / cron | **GitHub Actions** | Free for public repos; scheduled data refresh + PR checks |

### Deferred / scale-out choices (do NOT adopt in v1)
- **GPU layout** (`cuGraph` ForceAtlas2 or Datashader `forceatlas2_layout`) — only when node count crosses ~100k (v3, EU law). Note: a local RTX 4070 can run cuGraph for one-off layout precompute if CPU FA2 ever feels slow.
- **`cosmos.gl`** renderer — only if sigma.js stalls past ~100k nodes. API is close enough that it's a port, not a rewrite.
- **Incremental pipeline** (process only changed laws) — required once a full rebuild can't finish inside the GitHub Actions 6h job limit (v2, Landesrecht).

---

## 5. Data model

Jurisdiction-aware from day one, even though v1 only emits `DE-BUND`. This avoids
a painful schema migration when Landesrecht and EU law arrive.

### Node (`/data/<jurisdiction>/nodes.json`, one entry per law)
```jsonc
{
  "id": "de-bund/BGB",
  "jurisdiction": "DE-BUND",
  "jurabk": "BGB",
  "title": "Bürgerliches Gesetzbuch",
  "classification": { "scheme": "FNA", "code": "400-2", "main_group": 4 },
  "meta_cluster": "civil-law",        // mapped from classification.scheme→meta taxonomy
  "created_at": "1896-08-18",         // ausfertigung-datum
  "repealed_at": null,                 // null = currently in force
  "x": 142.7, "y": -88.3,              // ForceAtlas2 output (union-graph coords)
  "color": "#4F8DFB",                  // resolved per §6 color logic
  "size": 24,                          // f(degree)
  "degree": 311                        // number of cross-references touching this node
}
```

### Edge (`/data/_global/edges.json`)
```jsonc
{
  "source": "de-bund/BGB",
  "target": "de-bund/HGB",
  "type": "explicit",                  // explicit | soft (embedding)
  "weight": 1.0,                       // explicit refs = 1.0, soft/orphan edges ≈ 0.1
  "valid_from": "2021-04-01",          // best-effort; macro layer only knows existence
  "valid_to": null
}
```
Edges may be cross-jurisdiction from day one (a DE law can reference
`eu/CELEX:32016R0679`); the target simply won't resolve to a node until EU data exists.

### Per-law detail (`/data/<jurisdiction>/laws/<id>/`)
```
base.html              # oldest captured version, rendered with data-ref-id spans
patches/2021-06-12.diff # forward diff-match-patch patch per change
patches/2022-01-03.diff
meta.json              # toc, version index with timestamps
```

### Global indexes (`/data/_global/`)
```
layout.json            # node id → {x, y}
search-index.json      # serialized FlexSearch
meta-taxonomy.json     # classification scheme code → meta_cluster + color
reference-resolver.json# "§ 433 BGB" → "de-bund/BGB" (for clickable refs)
```

---

## 6. Color logic (three rules)

The nine FNA main groups define nine base hues. Everything else derives from them.

1. **FNA-unambiguous** → pure main-group hue.
2. **FNA-bridging** (a law whose references span multiple main groups) →
   weighted HSL blend, proportional to reference counts per group.
3. **FNA-unclassified / orphan** → no FNA code. Compute text embedding, take
   top-K (K=5) nearest neighbors by cosine similarity, blend their colors (HSL,
   weighted by similarity). The same neighbors become **soft edges** (weight ≈ 0.1)
   in the layout so the orphan gravitates into its semantic neighborhood.

This marries two signals: the **structural** graph (explicit §-references, hard
edges) and the **semantic** graph (text similarity, soft edges, orphans only).

---

## 7. Layout

- Build the graph on the **union of all laws ever** (including repealed ones), so
  rewinding the time slider doesn't leave historical nodes position-less.
- Hard edges: explicit references, weight 1.0.
- Soft edges: orphan→neighbor embedding links, weight ≈ 0.1 (enough to pull, not
  enough to dominate).
- `fa2_modified` settings for the organic look:
  - `outboundAttractionDistribution=True` (dissuade hubs — keeps mega-laws like BGB from collapsing everything inward)
  - `barnesHutOptimize=True`, `barnesHutTheta≈1.2`
  - `scalingRatio≈2.0`, `gravity≈1.0`, `strongGravityMode=False` (lets outliers fan out as "spores")
  - `edgeWeightInfluence=1.0`
  - fixed `seed` for reproducible layouts across pipeline runs
- Node size = f(degree). Dense reference hubs become visually large centers.

Rendering aesthetic (frontend): dark background, low edge opacity (~0.1) so
references read as fine mist rather than spaghetti, subtle node glow.

---

## 8. Frontend interaction model

- **Entry:** camera starts zoomed onto the BGB neighborhood with a dismissible
  hint ("zoom out for the bird's-eye view"). Avoids the wall-of-nodes shock.
- **Click node:** sidebar with rendered full text + table of contents.
- **Clickable references:** each `<span data-ref-id="…">` resolves via
  `reference-resolver.json`; click → camera flies to the target node + opens it.
- **Search:** FlexSearch over title + short description, debounced ~50ms. Matches
  brighten (higher opacity/size/glow via sigma node reducer); non-matches dim to ~15%.
- **Time slider (global, bottom):** filters node/edge *visibility* by
  `created_at`/`repealed_at`. Positions never move.
- **Version timeline (per law):** in the sidebar; select a version, see a
  paragraph-level diff (status badge per § + inline diff-match-patch render).

---

## 9. Pipeline stages (Snakemake)

```
01 download_toc        gii-toc.xml → list of ~6000 law xml.zip URLs
02 download_laws       fetch + unzip each law's XML (parallel)
03 clone_history       shallow-clone kmein/gesetze for git version history
04 parse_laws          XML → structured Law objects (lxml); render base.html w/ ref spans
05 scrape_fna          buzer.de FNA tree (+ BMJ PDF fallback) → code→law mapping
06 classify            attach FNA code + meta_cluster to each law
07 extract_refs        legal-reference-extraction over each law → normalized refs
08 resolve_refs        normalized ref → node id; build reference-resolver.json
09 embed               distiluse embeddings for all laws
10 orphan_neighbors    top-K cosine neighbors for unclassified laws → soft edges
11 build_graph         assemble nodes + (hard + soft) edges, compute degree
12 layout              fa2_modified on union graph → x/y per node
13 color               apply three-rule color logic
14 diff_cache          per law: base.html + forward patches from git history
15 search_index        FlexSearch serialize (title + short desc)
16 bundle              write /data/**.json in final shapes
17 validate            assert node/edge counts, no dangling resolver entries, schema check
```

Snakemake caches per stage: editing stage 13 (color) re-runs only 13→17, not the
expensive download/parse/embed/layout work.

---

## 10. Deployment & data freshness

- **Frontend:** static bundle, deployed on push to `main` (Vercel auto-build).
- **Data refresh:** scheduled GitHub Action (start with weekly; daily is overkill
  since the upstream repos and gii-toc change infrequently). The action runs the
  pipeline, commits regenerated `/data`, which triggers a frontend redeploy.
- **Cost:** 0 €/month for a public repo.

---

## 11. Known risks & mitigations

| Risk | Bites at | Mitigation |
|---|---|---|
| Reference recall < target | v1 | Use `legal-reference-extraction`; track misses; NER upgrade in v2 |
| FNA only as PDF | v1 (Stufe 0) | buzer.de scrape primary, PDF fallback; orphans handled by embedding rule |
| No pre-2021 version diffs | v1 | Document honestly; macro time slider still works via `ausfertigung-datum` |
| GH Actions 6h job limit | v2 (Landesrecht) | Incremental pipeline (process only changed laws) |
| Initial payload size | v2/v3 | Chunked storage + lazy-load full text on click |
| sigma.js performance ceiling | v3 (>100k nodes) | Port renderer to cosmos.gl |
| CPU layout too slow | v3 | GPU layout (cuGraph / Datashader); local RTX 4070 viable |
| FNA is DE-Bund only | v2 | Pluggable meta-taxonomy + per-scheme mapping tables |

---

## 12. Reference implementations (study, don't fork wholesale)

- `bundestag/gesetze-tools` — XML download + markdown conversion scripts
- `maxsagt/de_laws_to_json` — gii-toc.xml → JSON, shows the XML metadata shape
- `kmein/gesetze` — daily-updated law repo with git history (history source)
- `jandinter/gesetze-im-internet` — weekly XML archive
- `openlegaldata/legal-reference-extraction` — the reference parser (dependency)
- `fa2_modified` / `pyforceatlas2` — layout engine (dependency)
