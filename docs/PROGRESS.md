# PROGRESS

> The single source of truth for "where are we?" Claude updates this at the end
> of every working session. Read it at the start of every new session.
>
> If you find yourself with stale or contradictory information, trust `git log`
> and the actual state of `/data` and `/pipeline` over what this file claims.

---

## Current stage
**Stufe 0 — Foundation & de-risking spikes** (Spikes A + B done, C remains)

## Last session
2026-05-30. Completed **Spike B — FNA acquisition** (the riskiest unknown).
Tested both sources against the live 6 123-law corpus and **reversed the earlier
"buzer primary" assumption**:
- **buzer.de**: clean HTML (exact code per law) BUT an aggressive anti-bot blocks
  unattended crawling — a fast crawl trips a firewall block → persistent HTTP 403
  "use gateway to start" that doesn't clear in ~45 min and is renewed by probing.
- **BMJ FNA PDF** (`recht.bund.de/.../FNA_2023.pdf`): one authoritative download,
  no rate-limit risk → now the PRIMARY source. Two-column parsing is painful
  (must crop columns with pdfplumber; code regex must allow 1–4 digit prefixes —
  the early `\d{3,4}` dropped all of group 5). Spike-level parser: **53.5 %
  coverage (3 279/6 124)**; ceiling 61.9 %; ~60 % of misses are recoverable with
  fuzzy joining → realistic ~75–80 % target for Stage 05.

Wrote `spike_b_fna.py` (PDF, primary) + `spike_b_buzer.py` (buzer, secondary),
`docs/spike_b.md`, ADR 002, added `pdfplumber` to pyproject, and updated
ARCHITECTURE.md §2.3 / stage 05 / risk table to match.

## Next concrete step
**Spike C — reference extraction.**

Goal: run `legal-reference-extraction` on ~5 laws, measure recall by hand, and
prototype the `normalized ref → node id` resolver. Steps:
1. **First check `legal-reference-extraction` is installable** — it's in
   `pyproject.toml` but may not be on PyPI under that exact name (see below);
   may need a git install. Resolve this before building on it.
2. Run it over 5 varied laws (BGB, StGB, a regulation, a treaty, a short one).
3. Hand-measure recall of `§`/Art. citations; note miss patterns.
4. Prototype `reference-resolver.json` (normalized ref → `de-bund/<jurabk>`),
   degrading gracefully on unresolvable refs.
→ Sonnet/high (parser recall is detail-heavy), per ROADMAP guidance.

## Open questions / parked thoughts
- `legal-reference-extraction` is listed in `pyproject.toml` but may not be
  on PyPI under that exact name. **Resolve at the start of Spike C** (step 1).
- Stage 05 work for later: lift PDF coverage past 53.5% via fuzzy/token title
  matching + FNA-abbr↔jurabk join (1 808 unmatched laws' titles already appear in
  the PDF text); pull the code→Sachgebiet-name taxonomy tree from the PDF front
  matter for group labelling; add buzer enrichment behind a slow cached crawler.
- ZIP files can contain non-XML entries (images). Spike scripts filter `.xml` only.
- buzer may keep blocking this IP for a while; the buzer prototype is expected to
  hit the 403 gateway block from a cold IP (documented, not a bug).

## Stage checklist
- [ ] Stufe 0 — Foundation & de-risking spikes
  - [x] Monorepo scaffold (dirs, pyproject, package.json, Snakefile skeleton, CI)
  - [x] Spike A — data shape
  - [x] Spike B — FNA acquisition
  - [ ] Spike C — reference extraction
- [ ] Stufe 1 — Pipeline backbone
- [ ] Stufe 2 — Layout & color
- [ ] Stufe 3 — Frontend graph shell
- [ ] Stufe 4 — Interaction & detail view
- [ ] Stufe 5 — Time axis & versions
- [ ] Stufe 6 — Polish & v1 launch
