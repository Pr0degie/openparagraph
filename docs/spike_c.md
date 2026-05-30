# Spike C — Reference Extraction

**Date:** 2026-05-30  
**Script:** `pipeline/spikes/spike_c_references.py`  
**Output:** `data/spike_c/` (gitignored)

## Goal

Test `legal-reference-extraction` (module: `refex`) against 5 diverse laws,
measure extraction recall and resolver coverage, and prototype the
`reference-resolver.json` architecture needed for Stage 06/07.

---

## Installation finding

The PyPI package name is `legal-reference-extraction` but the importable module
is **`refex`**. Use:

```python
from refex.orchestrator import CitationExtractor
```

The package is installed and importable. No git install needed.

---

## Laws tested

| Slug | jurabk | Norms | Citations | Resolved |
|------|--------|------:|----------:|---------:|
| bgb | BGB | 2543 | 329 | 30 (9.1%) |
| stgb | StGB | 563 | 74 | 40 (54.1%) |
| gg | GG | 205 | 2 | 0 (0%) |
| bimschg | BImSchG | 121 | 74 | 33 (44.6%) |
| burlg | BUrlG | 18 | 9 | 9 (100%) |
| **Total** | | **3450** | **488** | **112 (23.0%)** |

---

## Key findings

### 1. Extraction recall — qualitatively good

refex finds genuine `§`/Art. citations reliably. Every real cross-reference
to an external law in the sample text was captured. The regex source (not CRF
or transformer) has high confidence = 1.0 for all findings.

### 2. False positive rate — ~40% of extracted citations are noise

refex extracts sequences like "die §§ 476 und 477 über die Rechte bei Mängeln.
An die Stelle der … Vorschriften treten die Vorschriften" as a citation with
`book='vorschriften'`. The word "Vorschriften" (= "provisions") is not a law
name.

Top false-positive book codes (aggregate across all 5 laws):

| book | count | reason |
|------|------:|-------|
| vorschriften | 197 | "die Vorschriften" = generic "the provisions" |
| einführungsgesetz | 66 | ambiguous: BGBEG? StPOEG? needs context |
| verordnung | 14 | generic "statutory order" |
| haftung | 9 | "Haftung" = liability, not a law name |
| bundes | 7 | fragment of compound word |
| anordnung | 3 | generic "order" |
| rechtsverordnung | 3 | generic "statutory ordinance" |
| überwachung | 4 | generic word |

**~237 of 488 citations (49%) are noise.** Excluding these, the real citation
count is ~251 across 3450 norms = 0.07 citations/norm.

### 3. All genuine citations use long-form law names, not abbreviations

Legal texts write "des Bürgerlichen Gesetzbuches" and "das Wasserhaushaltsgesetz",
not "BGB" or "WHG". refex returns these as lowercase long-form book names:
`wasserhaushaltsgesetz`, `beurkundungsgesetz`, `telekommunikationsgesetz`.

No short GII-slug-style codes (`bgb`, `stgb`) appear in any of the 488 citations.

### 4. Resolver design: title-match is insufficient; jurabk-lookup is needed

Title-based resolver (3-layer: slug identity + exact title lowercase + parenthetical):
- Reaches 23% overall / 44.6% for non-BGB laws
- BGB bottleneck: BGB cites many modern laws (Telekommunikationsgesetz,
  Aufenthaltsgesetz) whose GII slugs encode a year suffix (`tkg_2021`,
  `aufenthg_2004`). The title lookup hits `tkg_2021` for "telekommunikationsgesetz"
  (exact match ✓), but "aufenthaltsgesetz" fails because the TOC stores it under
  "Gesetz über den Aufenthalt … (Aufenthaltsgesetz)" and the parenthetical
  collision logic chose a different entry.
- Genitive forms are not normalized: "wasserhaushaltsgesetzes" (genitive -es)
  doesn't match "Wasserhaushaltsgesetz" (nominative).
- Many law names use the colloquial Kurzname ("Kreislaufwirtschaftsgesetz") while
  the GII title is the formal long name — no overlap at the title level.

**Root cause:** the authoritative cross-reference key is the `jurabk` field in
each law's XML, not the TOC title. A full resolver needs the `jurabk` table
(slug → jurabk) from all 6 124 laws.

---

## Resolver architecture for Stage 06

Three-step lookup:

```
refex book (e.g. "aufenthaltsgesetz")
  ↓
Step 1: Normalize
  - Strip genitive suffixes: -es, -s at word end
  - Strip German ß→ss variant
  - Strip spaces (for multi-word book names)
  ↓
Step 2: Try lookup table (built in Stage 01 from all 6124 law XMLs)
  jurabk_normalized → {slug, jurabk, langue}
  Note: jurabk is already the natural key ("AufenthG" → "aufenthg" slug variant)
  ↓
Step 3: Fuzzy fallback (Stage 06 enhancement)
  - Token overlap between book name and langue
  - Threshold TBD
  ↓
Fallback: unresolvable → degrade gracefully (no edge, no crash)
```

Pre-filter (drop before lookup to avoid false edges):
```
GENERIC_WORDS = {
    "vorschriften", "verordnung", "rechtsverordnung", "anordnung",
    "haftung", "bundes", "überwachung", "verfassung", "ordnungswidrigkeiten",
}
```

---

## Revised "einführungsgesetz" handling

66 citations use `book='einführungsgesetz'` — these are real but ambiguous.
In BGB context: Einführungsgesetz zum Bürgerlichen Gesetzbuche (BGBEG, slug
`bgbeg`). In StGB context: Einführungsgesetz zum Strafgesetzbuch (EGStGB, slug
`egstgb`). Resolution: inject current law's jurabk as context into the resolver
and maintain an "Einführungsgesetz context table" (X → its EGXYZ).

---

## Realistic coverage estimate for Stage 06

After false-positive filtering + genitive normalization + jurabk-based lookup:

- False positive filter removes ~49% noise → ~251 real citations
- jurabk lookup expected to resolve ~70–80% of genuine citations
- Remaining ~20–30% unresolvable: very new laws, EU references, state laws

**Target: ~55–65% of raw refex citations resolve to a GII node.**
(This is the edge coverage, not law coverage — most well-connected nodes in the
 graph will have high cross-reference counts.)

---

## GG low citation count (only 2 citations across 205 norms)

The GG cites the Weimar Constitution directly ("Artikel 136 … der deutschen
Verfassung") and the Gemeindeverkehrsfinanzierungsgesetz — both unresolvable.
The low count is correct: the GG's norms are mostly structural ("Der Bundestag
besteht aus …") with few cross-statute citations. Not an extraction bug.
