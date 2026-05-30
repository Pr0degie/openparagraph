# Spike B — FNA Acquisition

**Date:** 2026-05-30
**Status:** Done
**Decision:** ADR `docs/decisions/002-fna-acquisition.md`
**Prototypes:** `pipeline/spikes/spike_b_fna.py` (PDF, primary),
`pipeline/spikes/spike_b_buzer.py` (buzer, secondary)
**Output:** `data/spike_b/{fna_map.json,results.json,summary.txt}` (gitignored)

## The question

GII per-law XML carries **no** FNA Sachgebiet code (the "fna" hits in BGB.xml are
false positives — "Au**fna**hme"; the only real codes are in-text citations like
"GG (100-1)"). So the code→law mapping must come from outside. Decide between
buzer.de scrape, BMJ PDF parse, or hybrid — and measure coverage of the 6 123-law
corpus.

## What we found

### buzer.de — clean data, hostile to crawlers
- The FNA tree at `buzer.de/fna/index.htm` is well structured: 9 main groups,
  recursive `/fna/<code>-<name>.htm` nodes, and leaf pages with a law table that
  gives the **exact** code per law:
  `<td class="fnal">400-2</td> … <a class="ltg" href="/BGB.htm">…</a>`.
- robots.txt **permits** `/fna/` (only `/s2.htm`, some `.js`, `/outb/`,
  newsletter, and `?m=`/`?line=` are disallowed).
- **But** a normal crawl (~7 req/s) trips an aggressive behavioural anti-bot:
  first a firewall-level block (`ConnectionError`, connection refused), then a
  persistent HTTP **403 "use gateway to start"**. It did not clear within ~45 min
  and was *renewed* by every further probe. → Not safe as an unattended-CI
  dependency.

### BMJ FNA PDF — robust acquisition, painful parsing
- `recht.bund.de/.../FNA_2023.pdf` — one 4.85 MB authoritative download, no
  rate-limit risk. URL pattern `FNA_<year>.pdf` is stable; PDFs exist since 2005.
- 1 126 pages, **two-column** layout. Extraction lessons:
  - **`pypdf` drops a whole column**; **`pdfplumber` interleaves** them. Fix:
    crop each half (`page.crop`) and read left-then-right. Inter-word spaces are
    sometimes lost — harmless for a normalized join key.
  - The front matter is the **Sachgebiet taxonomy tree** (code → name) — free.
  - Body entries: `400-2 Bürgerliches Gesetzbuch (BGB)\nvom 18. 8. 1896 …`, i.e.
    `<code> <title> (<abbr>)  vom <DD.MM.YYYY> <Fundstelle>`, plus "– Geändert …"
    amendment lines to skip.
  - **Code regex must allow 1–4 digit prefixes.** An early `\d{3,4}-\d+` silently
    dropped every 2-digit-prefix code — e.g. *all* of main group 5 (Verteidigung:
    `51-1` Soldatengesetz). Fixing it took entries from 1 710 → 3 789.
  - Anchor the title's end on a **numeric** `vom DD.MM.YYYY`; a spelled-out month
    ("vom 23. November 1964") is part of a treaty title, not the citation.
  - A single aggressive normalization (drop `(abbr)`, accents, all non-alphanum)
    absorbs hyphenation, lost spaces, and the recurring "V ertrag"/"V orschriften"
    glyph artifact at once.

## Coverage (full 6 123-law corpus, exact join)

| Metric | Value |
|---|---|
| PDF FNA-coded entries extracted | 3 789 |
| Coverage ceiling (1:1 join) | 61.9 % |
| Matched by exact title | 3 109 |
| Matched by abbr fallback | 170 |
| **Total coverage** | **3 279 / 6 124 = 53.5 %** |

Diagnostic on the 3 015 unmatched laws: **1 808 (60 %) appear somewhere in the
PDF text** (recoverable with fuzzy/token matching + better segmentation); 1 206
are genuine wording/scope/recency gaps (series laws the FNA lists under proper
names, e.g. "Erste Verordnung zur Durchführung des BImSchG" → "1. BImSchV", and
post-2023 laws). So **53.5 % is a join-key floor, not a content ceiling** — the
realistic target after Stage-05 fuzzy joining is ~75–80 %.

Main-group spread of matched laws (the 9 base hues), confirming all groups
populate: `1:309 2:820 3:173 4:235 5:74 6:304 7:615 8:408 9:341`.

## Decision

**BMJ PDF primary, buzer best-effort enrichment, embedding-gravitation for the
tail.** Full rationale and consequences in ADR 002. This *reverses* the earlier
ARCHITECTURE.md assumption (buzer primary), which has been updated accordingly.

## Notes / gotchas for Stage 05

- GII TOC `<link>` is already the `…/<slug>/xml.zip` URL — not an `index.html`.
- The robust join key is **FNA abbr ↔ GII `jurabk`** + fuzzy title, *not* the GII
  slug and *not* exact title alone.
- Re-run the spike each year by bumping `FNA_YEAR`; the parser is otherwise stable.
