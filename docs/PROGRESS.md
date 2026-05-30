# PROGRESS

> The single source of truth for "where are we?" Claude updates this at the end
> of every working session. Read it at the start of every new session.
>
> If you find yourself with stale or contradictory information, trust `git log`
> and the actual state of `/data` and `/pipeline` over what this file claims.

---

## Current stage
**Stufe 0 — Foundation & de-risking spikes** (Spike A done, B and C remain)

## Last session
2026-05-30. Set up proper directory structure (moved scaffold files from root
into `pipeline/`, `web/`, `.github/workflows/`, `.devcontainer/`). Completed
**Spike A — data shape**: wrote `pipeline/src/gii_parser.py`, 3 fixture XMLs,
23 passing unit tests, and `pipeline/spikes/spike_a_data_shape.py`. Ran the
spike against live GII data — sampled 10 laws from the 6 123-law corpus,
confirmed all key fields. Key finding: `amtabk` is only 30% present; `jurabk`
is the reliable primary key. Decision recorded in `docs/decisions/001-data-shape.md`.

## Next concrete step
**Spike B — FNA acquisition** (the riskiest unknown).

Goal: prototype FNA→law mapping for ~50 laws. Decide: buzer.de scrape vs BMJ
PDF parse vs hybrid. Steps:
1. Fetch the buzer.de FNA tree (`buzer.de/fna/`); check if it's scrape-friendly
   and how complete the code→jurabk mapping is.
2. Optionally cross-check against the BMJ annual PDF for the top FNA codes.
3. Measure coverage: what fraction of the 6 123 laws get an FNA code?
4. Write `pipeline/spikes/spike_b_fna.py` + decision note.
→ Use Opus/xhigh for this — it's the most strategic decision in the project.

## Open questions / parked thoughts
- `legal-reference-extraction` is listed in `pyproject.toml` but may not be
  on PyPI under that exact name. Will need to check at Stufe 1 / Spike C time.
- ZIP files can contain non-XML entries (images). The spike script handles this
  correctly (filters for `.xml` entries only).

## Stage checklist
- [ ] Stufe 0 — Foundation & de-risking spikes
  - [x] Monorepo scaffold (dirs, pyproject, package.json, Snakefile skeleton, CI)
  - [x] Spike A — data shape
  - [ ] Spike B — FNA acquisition
  - [ ] Spike C — reference extraction
- [ ] Stufe 1 — Pipeline backbone
- [ ] Stufe 2 — Layout & color
- [ ] Stufe 3 — Frontend graph shell
- [ ] Stufe 4 — Interaction & detail view
- [ ] Stufe 5 — Time axis & versions
- [ ] Stufe 6 — Polish & v1 launch
