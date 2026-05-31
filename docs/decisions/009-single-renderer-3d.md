# 009 — Ein Renderer (Three.js / 3d-force-graph) für 2D + 2.5D + 3D, sigma.js wird abgelöst

**Status:** accepted
**Date:** 2026-05-31

## Context

ARCHITECTURE.md §4 hatte **sigma.js v3** als Renderer gewählt (2D, WebGL,
node-reducer-API). sigma kann jedoch **kein 3D**. Ein Spike (`web/src/spike3d.ts`,
Branch `spike/3d-view`) hat auf den echten 6124 Nodes gezeigt, dass **3d-force-graph**
(Three.js + d3-force-3d) dieselben Daten in drei Ansichten rendern kann, gesteuert
nur über z-Quelle + Kamera:

- **2D** — z=0, Kamera senkrecht von oben, Rotation gesperrt (die vertraute flache Karte)
- **2.5D** — getunte FA2-x/y als Karte + sinnvolle z-Achse
- **3D** — volles Force-Layout

Der Nutzer will alle drei Ansichten. Zwei Renderer parallel zu halten (sigma für 2D,
Three für 2.5D/3D) bedeutet: In-Canvas-Interaktionen (Such-Highlight, Fly-to,
Zeit-Filter aus Stufe 4–6) doppelt verdrahten, ein harter Schnitt beim View-Wechsel
und **kein** sanfter 2D→3D-Übergang. Der Spike hat zudem gezeigt, dass sich der
ursprüngliche Grund für sigma (flache, knackige 2D-Optik) in Three reproduzieren
lässt: `MeshBasicMaterial` (lichtunabhängig, keine matte Schattierung) + dünner
dunkler BackSide-Outline als Rand.

## Decision

**Ein Renderer: 3d-force-graph (Three.js).** sigma.js, graphology und der
Custom-Shader `node-border-program.ts` werden abgelöst. Die drei Ansichten sind ein
Umschalter über z-Quelle + Kamera, eine Codebasis, **Stufe 4–6 wird nur einmal gebaut**.

- Vorberechnete Koordinaten werden **fest** eingespeist (Force-Engine in 2D/2.5D aus),
  damit die Determinismus-Regel des Projekts erhalten bleibt.
- Die 2.5D-z-Achse kommt im echten Bau aus **PCA der vorhandenen `embeddings.npy`**
  (alle Nodes bekommen Tiefe; der Spike nutzte ersatzweise `main_group`, das nur 54 %
  abdeckt).
- Der alte sigma-Code wird **nicht gelöscht, sondern archiviert** unter
  `web/archive/sigma-2d/` (kann später entfernt werden), falls ein Rückgriff nötig wird.

## Alternatives considered

- **sigma für 2D behalten, Three für 2.5D/3D (zwei Renderer)** — abgelehnt: doppelte
  In-Canvas-Interaktions-Logik, harter Schnitt beim Umschalten, kein animierter
  2D→3D-Übergang. Die einzige Stärke (beste 2D-Optik) ist in Three nachbaubar.
- **Roher Three.js statt 3d-force-graph** — abgelehnt für den ersten Bau: Picking,
  Labels, Kamera/Orbit, Fly-to müssten von Hand gebaut werden (~7–12 statt ~2–3 Tage).
  Bleibt Rückfalloption, falls die Bibliothek limitiert (analog zur cosmos.gl-Notiz).
- **Bei reinem 2D-sigma bleiben** — abgelehnt: der Nutzer will 3D.

## Consequences

- Löst die Renderer-Wahl in **ARCHITECTURE.md §4** ab; §4/§5/§7/§8/§11 und ROADMAP
  werden im Implementations-Commit (gleiche Änderung wie der Code) nachgezogen.
- Neue Dependencies `three` + `3d-force-graph`; Bundle wächst von ~150 KB auf ~1 MB
  (three.js) — vertretbar für eine Desktop-Visualisierung.
- Der Custom-Border-Shader entfällt; Ersatz: flaches `MeshBasicMaterial` + Outline
  (2D) bzw. die natürliche Tiefenschattierung der Kugeln (3D).
- Pipeline bekommt eine optionale **z-Achse** (Stage 12/13, hinter Config; 2D bleibt
  Default lauffähig) — eigener Arbeitsschritt, siehe Implementations-Plan.
- `web/archive/sigma-2d/` ist toter Code (nicht im Build, nicht typgeprüft); bei einem
  späteren Cleanup ersatzlos löschbar.
- Determinismus bleibt gewahrt, weil die Force-Engine in 2D/2.5D aus ist und die
  Koordinaten aus der Pipeline kommen.
