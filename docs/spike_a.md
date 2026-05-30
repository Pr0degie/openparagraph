# Spike A — GII Data Shape

**Date:** 2026-05-30  
**Status:** Done  
**Output:** `data/spike_a/results.json`, `data/spike_a/summary.txt`

## What we tested

Downloaded 10 representative laws spread across the 6 123-law `gii-toc.xml` corpus.
Parsed their XML with lxml and measured field presence.

## Confirmed structure

- TOC root element is `<items>` (not `<laws>` or `<gesetze>`).  
- Each law is one ZIP at `/<slug>/xml.zip` containing one or more `.xml` files
  (some ZIPs also include images — iterate over `.xml` entries only).
- Within the XML, a `<dokument>` root holds `<norm>` elements.
  The **first** `<norm>` is the law header (Stammnorm); subsequent norms are individual §§.
- Header `<metadaten>` always contains `<jurabk>`, `<ausfertigung-datum>`, `<langue>`.
- Content norms have `<enbez>` (§-number) and `<textdaten><text>` reliably; `<titel>` is
  sometimes absent for proclamation- and order-type laws.

## Field presence (10-law sample)

| Field | Present | Notes |
|---|---|---|
| `jurabk` | 10/10 | Always present — **use as primary law key** |
| `ausfertigung-datum` | 10/10 | Always present; ISO date in element text |
| `langue` | 10/10 | Always present — full German title |
| `amtabk` | 3/10 | **Unreliable (30%)** — do not use as identifier |

## Norm count spread

Ranges from 1 (short proclamations) to 351 (BauGB). The parser must handle
both extremes without special-casing.

## Decision

**`jurabk` is the law identifier.** Do not depend on `amtabk`; it is absent
in ~70 % of laws. The `Law` dataclass in `src/gii_parser.py` treats `amtabk`
as nullable and never uses it as a key. The node id format is `de-bund/<jurabk>`.

No structural surprises in the XML. The lxml recovery parser handles the
occasional broken markup gracefully (confirmed by malformed-fixture unit test).
The parser (`src/gii_parser.py`) and 23 unit tests are committed alongside this note.
