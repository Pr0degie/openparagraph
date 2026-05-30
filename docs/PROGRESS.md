# PROGRESS

> The single source of truth for "where are we?" Claude updates this at the end
> of every working session. Read it at the start of every new session.
>
> If you find yourself with stale or contradictory information, trust `git log`
> and the actual state of `/data` and `/pipeline` over what this file claims.

---

## Current stage
**Stufe 0 — Foundation & de-risking spikes** (Spikes A + B + C done — all three complete)

## Last session
2026-05-30. Completed **Spike C — reference extraction**.
Key findings:
- `legal-reference-extraction` installs as **`refex`** (module), works out of the
  box — no git install needed.
- `CitationExtractor` extracts `§`/Art. citations well from plain text. Ran across
  5 laws (3 450 norms): **488 citations** extracted.
- **~49% false positive rate**: "vorschriften" (197×), "verordnung" (14×), etc.
  are generic German words, not law names. A block-list filter is needed in Stage 07.
- All genuine citations use **long-form law names** (e.g. `aufenthaltsgesetz`),
  never short GII-slug-style abbreviations.
- Resolver prototype: title-based lookup reaches 23% overall; root cause is that
  the authoritative cross-reference key is the **`jurabk`** field from each law's
  XML, not the TOC title. Stage 02 must output `slug_table.json` ({slug → jurabk/langue}).
- Expected resolver coverage in Stage 08: **~55–65%** of raw citations after
  false-positive filter + genitive normalization + jurabk lookup.
- ADR 003 written; ARCHITECTURE.md §9 updated (Stage 02 + 07 + 08).

## Next concrete step
**Transition to Stufe 1 — Pipeline backbone.**

Start with Stage 01 (download_toc) + Stage 02 (download_laws) as real Snakemake
rules. Stage 02 must emit `slug_table.json` (jurabk + langue per slug) as a
by-product of the XML parse, since Stage 08 needs it for the resolver.

Suggested order:
1. Write `pipeline/rules/01_download_toc.smk` — simple: fetch gii-toc.xml,
   write `data/download_toc/toc.json` (slug → zip_url, title).
2. Write `pipeline/rules/02_download_laws.smk` — parallel fetch; for each slug
   unzip + call `gii_parser.parse_law`; emit per-law `{jurabk, langue, ausfertigung_datum}`
   and accumulate into `slug_table.json`.
3. Hook both into the root `Snakefile` with a `rule all` target.

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
- [ ] Stufe 2 — Layout & color
- [ ] Stufe 3 — Frontend graph shell
- [ ] Stufe 4 — Interaction & detail view
- [ ] Stufe 5 — Time axis & versions
- [ ] Stufe 6 — Polish & v1 launch
