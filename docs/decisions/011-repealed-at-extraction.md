# 011 — Aufhebungsdatum (`repealed_at`) aus `<standangabe>` per Anker-Regex

**Status:** accepted
**Date:** 2026-05-31

## Context

Der Zeit-Slider (Stufe 5) soll Gesetze nach Lebensspanne filtern — Geburt
(`ausfertigung-datum` → `created_at`) **und** Tod (`repealed_at`). `created_at`
war vorhanden; `repealed_at` war in `graph_builder.py` hartcodiert `None`, also
für alle 6124 Nodes leer. Ein Tod-Filter wäre damit wirkungslos gewesen.

Messung am echten Corpus (`build/laws_xml/`): nur **130 von 6124** Gesetzen (4 %)
führen ein Aufhebungsdatum, und zwar in
`<standangabe><standtyp>Aufh</standtyp><standkommentar>…</standkommentar></standangabe>`.
Der `standkommentar` ist **freier deutscher Prosatext**, z. B.:

- „… mit Ablauf d. 31.12.2026 außer Kraft"
- „V aufgeh. durch § 9a idF d. Art. 2 V **v. 8.7.2025** mWv **1.7.2026**"
- „… mWv 7.10.2025 mit Ausnahme des § 17 … mWv 18.8.2026 außer Kraft" (selektiv)

**Fallstrick:** Fast jeder Kommentar nennt das Datum des *aufhebenden Rechtsakts*
als `v. DD.MM.YYYY` — das ist **nicht** das Aufhebungsdatum. Eine naive
„erstes/letztes Datum"-Heuristik greift systematisch das falsche.

## Decision

**Ankerbasierte Regex mit Prioritätsreihenfolge** (`parse_repeal_date` in
`gii_parser.py`). Das Datum wird an seiner juristischen Bedeutung gebunden:

1. `bis zum (DATE) … verlängert` → bei mehreren das **späteste** (sequentielle Verlängerung)
2. `mit Ablauf [des] (DATE)`
3. `mWv (DATE)` (mit Wirkung vom)
4. `am (DATE) … außer Kraft`

Erste greifende Klasse gewinnt, innerhalb der Klasse das späteste Datum
(konservativ korrekt bei selektiver Teilaufhebung). `v.` ist **kein** Anker und
wird daher nie versehentlich gegriffen. Kein Anker / kein Datum trotz `Aufh` →
`None` + `parse_warnings`-Eintrag.

Ergebnis am echten Corpus: **108 von 130** Aufh-Gesetzen liefern ein Datum, **22**
bleiben bewusst `None` (bedingte/offene Aufhebung „an dem Tag, an dem das Abkommen
außer Kraft tritt"; partielle Aufhebung „teilweise aufgeh."; reine
`aufgeh. durch … v. DATE`-Fälle ohne `mWv`).

Das Feld fließt durch `law_serializer` → `classifier` → `graph_builder` (statt
`None` jetzt `meta.get("repealed_at")`) und via `{**node}`-Spread durch Stage
12/13 bis `nodes.json`.

## Alternatives considered

- **Erstes/letztes Datum global** — greift das `v.`-Akt-Datum statt des
  Wirkdatums; systematisch falsch, sobald `mWv` vorhanden ist. Verworfen.
- **`v. DATE`-Fallback** für `aufgeh.`-Fälle ohne `mWv` — würde ein paar
  zusätzliche Daten liefern, aber „teilweise aufgeh."-Fälle (Gesetz lebt weiter)
  fälschlich als tot markieren. Das False-Positive-Risiko überwiegt den geringen
  Gewinn; verworfen.
- **Textmonate** (`am 31. Juli 2013`) — 1 Einzelfall, bewusst out-of-scope
  (`None`).

## Consequences

- Tod-Filter im Frontend (Intervall-Overlap in `applyHighlight`, siehe `timefilter.ts`)
  ist nun real, betrifft aber nur ~108 Gesetze — sichtbar v. a. bei Zukunfts- oder
  eng-historischen Slider-Fenstern (befristete Verordnungen).
- Die 22 datumslosen Aufh-Fälle bleiben sichtbar (open-ended). Akzeptiert.
- Re-Run-Falle: Stage 04 (`directory()`-Output) gilt für Snakemake als aktuell,
  obwohl Code geändert wurde — nur der `code`-Rerun-Trigger (Snakemake 8) bzw. ein
  Force erzwingt das Neu-Parsen. Beim Tunen der Regex muss `parse_laws` ge-forced
  werden, sonst schlägt nichts durch.
- Sollte später eine bessere Quelle (buzer, FNA-Anreicherung) genauere
  Aufhebungsdaten liefern, kann `parse_repeal_date` ergänzt oder ersetzt werden,
  ohne den Durchreich-Pfad anzufassen.
