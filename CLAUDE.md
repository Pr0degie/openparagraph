# CLAUDE.md

Instructions for Claude Code working in this repository. Read this first, every
session.

## What this project is

openparagraph: a static, two-part system. A **Python/Snakemake pipeline**
(`/pipeline`) turns official German law data into static JSON; a **TypeScript +
sigma.js frontend** (`/web`) renders it. No server, no DB, no Docker in
production. Full design in `ARCHITECTURE.md`; plan in `ROADMAP.md`. **If a design
decision is unclear, ARCHITECTURE.md wins — and if you change a decision, update
ARCHITECTURE.md in the same change.**

## Golden rules

1. **Read before write.** `grep`/read the relevant module before editing. This
   repo favors a grep-first workflow to keep context lean.
2. **Respect the stage boundaries.** The pipeline is a Snakemake DAG. A change to
   one stage should not silently couple to another. Stages communicate only
   through files in `/data` (or stage-local temp dirs).
3. **Jurisdiction-aware always.** Every node/edge carries a `jurisdiction` field
   even though v1 only emits `DE-BUND`. Never hardcode `DE-BUND` assumptions into
   shared code — go through the meta-taxonomy layer.
4. **Don't promise pre-2021 diffs.** Fine-grained version history starts ~April
   2021. The macro time slider (node birth/death) uses `ausfertigung-datum` and
   does cover full history; keep these two layers distinct.
5. **No new heavy dependencies without a note.** If you add one, justify it in the
   PR description and in ARCHITECTURE.md §4.

## Repo layout

```
/pipeline   Python + Snakemake. Stages 01–17 (see ARCHITECTURE.md §9).
/web        Vite + TS + sigma.js frontend.
/data       Generated artifacts. NOT hand-edited. Output of the pipeline.
/docs       Spike decision notes, ADRs.
```

## Pipeline conventions (`/pipeline`)

- Python 3.12, managed with **uv**. Don't use `pip` directly; use `uv add`.
- Each Snakemake rule = one stage, named `NN_verb` (e.g. `12_layout`).
- Stages must be **idempotent** and **deterministic** (fixed random seeds; the
  layout seed lives in config so re-runs reproduce coordinates).
- Use **lxml** for XML. The GII source XML is dirty (style markup, not pure
  semantics) — handle malformed input gracefully, log, continue.
- References: always go through `legal-reference-extraction`; do not hand-roll
  regex parsing of `§` citations.
- Heavy stages (download, embed, layout) must cache so editing a downstream stage
  doesn't re-run them. Trust Snakemake's input/output declarations to do this.

## Frontend conventions (`/web`)

- TypeScript, **pnpm**, Vite. Strict mode on.
- sigma.js v3 + graphology. Use **node reducers** for the search-highlight and
  hover states — do not mutate the graph for transient visual state.
- **No `localStorage`/`sessionStorage`** assumptions for core data; the data is
  fetched static JSON. (Browser storage is fine for user prefs like theme.)
- Keep all colors and sizing driven by the data (`color`, `size` on nodes) — the
  frontend does not recompute the color logic; that's the pipeline's job.
- Clickable references resolve through `reference-resolver.json`. If a ref doesn't
  resolve (e.g. a future EU target), degrade gracefully — no crash, no dead link.

## Testing

- Pipeline: pytest. Every parser/normalizer stage gets unit tests with real (small)
  fixture XML snippets committed under `pipeline/tests/fixtures/`.
- The `17_validate` stage is the integration gate: node/edge counts in range, no
  dangling resolver entries, schema valid. CI runs it on a small sample corpus.
- Frontend: keep it light for now — type-check + a smoke test that the bundle
  loads sample data and renders without throwing.

## CI / data

- PRs run lint + type-check + tests on a **sample** corpus (not all 6000 laws).
- The full data build runs on a **scheduled** action (weekly), commits `/data`,
  and triggers the frontend redeploy. Don't run the full build in PR CI.

## When stuck on data reality

The source data lies about its own cleanliness. Before assuming a field exists,
check a real example:
- `gii-toc.xml` lists every law's `xml.zip`.
- A law's metadata block has `jurabk`, `amtabk`, `ausfertigung-datum`, `langue`.
- FNA codes are **not** reliably in that XML — they come from the FNA source
  (see Spike B note in `/docs`).

## Style

- Commit messages: imperative, scoped (`pipeline(layout): tune FA2 gravity`).
- Keep functions small; prefer pure functions in the pipeline so stages stay testable.
- Comments explain *why*, not *what*.
