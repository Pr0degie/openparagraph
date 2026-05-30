# 002 — FNA acquisition: BMJ PDF primary, buzer secondary

**Status:** accepted
**Date:** 2026-05-30
**Spike:** `docs/spike_b.md`, `pipeline/spikes/spike_b_fna.py`, `pipeline/spikes/spike_b_buzer.py`

## Context

The FNA Sachgebiet code (→ one of 9 main groups → base hue) is not in the
per-law GII XML (confirmed: the "fna" strings in BGB.xml are false positives
like "Au**fna**hme"; FNA codes only appear as in-text citations). It must come
from an external source. ARCHITECTURE.md had *assumed* buzer.de scrape primary
with the BMJ PDF as fallback. Spike B tested both against the live 6 123-law
corpus to resolve this — the single most strategic decision in the project.

## Decision

**Reverse the assumption: the BMJ annual FNA PDF is the PRIMARY source; buzer.de
is best-effort enrichment only.**

- Stage 05 parses `recht.bund.de/.../FNA_<year>.pdf` (column-aware extraction).
- buzer is used opportunistically for laws the PDF misses and for laws newer than
  the latest annual edition — but never as a hard dependency.
- Laws with no FNA code from either source fall through to the existing
  embedding-gravitation rule (ARCHITECTURE §6).

## Alternatives considered

- **buzer.de scrape as primary** — rejected. The data is *cleaner* (each leaf
  page gives the exact code per law in `<td class="fnal">`), and robots.txt
  permits `/fna/`. But it runs an aggressive behavioural anti-bot: a normal
  crawl trips a firewall block (connection refused → persistent HTTP 403
  "use gateway to start") that does not clear within ~45 min and is *renewed* by
  further probing. Unacceptable for an unattended weekly CI build.
- **PDF only, no buzer** — viable but leaves coverage on the table for recent
  laws (the PDF is annual/stale) and for the parser's misses. Keep buzer as a
  gentle top-up.
- **Skip FNA, use embeddings as the primary colour signal** (the ROADMAP
  fallback) — not needed. The PDF gives a usable ~54 % baseline today and is
  authoritative, so FNA stays the primary signal as designed.

## Consequences

- New dependency **`pdfplumber`** (pulls `pdfminer.six`) — justified here and
  added to `pyproject.toml`. `pypdf` was rejected: it drops one of the two
  columns. `beautifulsoup4` stays, now for the secondary buzer path.
- Coverage is **join-key limited, not content-limited.** A spike-level parser
  with exact title + abbr join reaches **53.5 % (3 279 / 6 124)**. The PDF holds
  3 789 coded entries (ceiling 61.9 % for 1:1 join), but ~60 % of the unmatched
  laws' titles *do* appear in the PDF text — recoverable in Stage 05/06 with
  fuzzy/token matching and better entry segmentation (target ~75–80 %).
- The real join key in the pipeline is **FNA abbreviation ↔ GII `jurabk`** plus
  **fuzzy title** — not the GII slug and not exact title alone (GII and FNA word
  titles differently, e.g. GII "Erste Verordnung zur Durchführung des BImSchG"
  vs FNA's proper name "1. BImSchV").
- The PDF front matter also yields the **code → Sachgebiet-name taxonomy tree**
  for free — useful for labelling the 9 groups and sub-clusters later.
- ARCHITECTURE.md §2.3, stage 05, and the risk table updated to match.
- Spike artifacts (`data/spike_b/*`) are gitignored like Spike A's; the scripts
  and these docs are the committed record.
