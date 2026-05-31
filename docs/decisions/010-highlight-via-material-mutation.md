# 010 — Visuelle Zustände (Highlight, Dimmen) via imperative Material-Mutation

**Status:** accepted
**Date:** 2026-05-31

## Context

Der Renderer nutzt `nodeThreeObject` um pro Node eine eigene Three.js-Gruppe
(Outline-Kugel + Fill-Kugel + Label-Sprite) zu erzeugen. Für Stufe 4 brauchen
wir **reaktive visuelle Zustände**: beim Suchen sollen Treffer-Nodes ihre Farbe
behalten, alle anderen auf ein dunkles Grau dimmen. Gleiches Muster wird in
Stufe 5–6 für den Zeit-Filter (Nodes außerhalb des Fensters ausgrauen) und ein
Adjacency-Highlight (Nachbarn eines angeklickten Nodes hervorheben) gebraucht.

3d-force-graph bietet zwei Wege, Node-Farben zu steuern:

**Option A — `nodeColor`-Accessor:**
```ts
Graph.nodeColor((n) => highlighted.has(n.id) ? n.color : '#1a1a22')
```
Der Accessor wird von der Bibliothek intern ausgewertet. Jede Änderung am
Accessor-Argument (`Graph.nodeColor(newFn)`) löst einen Re-Build der gesamten
Szene aus (alle Geometrien/Materialien neu anlegen). Das ist korrekt für
Standard-Nodes die die Bibliothek selbst anlegt — aber wir ersetzen sie via
`nodeThreeObject` mit eigenen Meshes. Der Accessor hat dort keine Wirkung;
die Farbe steckt im `MeshBasicMaterial` des selbst erzeugten Meshes.

**Option B — Imperative Material-Mutation (gewählt):**
Beim Erzeugen jeder Node in `makeNodeObject` wird das Fill-Material in einer
Map `nodeFillMats: Map<string, THREE.MeshBasicMaterial>` registriert.
Wenn sich der Highlight-Zustand ändert, iteriert `applyHighlight()` über die
Map und setzt `mat.color.set(...)` + `mat.opacity` direkt:

```ts
function applyHighlight(nodeById: Map<string, GraphNode>): void {
  nodeFillMats.forEach((mat, id) => {
    if (!searchActive || highlightedIds.has(id)) {
      mat.color.set(nodeById.get(id)!.color)
      mat.opacity = 1
      mat.transparent = false
    } else {
      mat.color.set('#1a1a22')
      mat.opacity = 0.22
      mat.transparent = true
    }
  })
}
```

Three.js erkennt die Änderung automatisch (`needsUpdate` für Colors ist nicht
nötig, weil `MeshBasicMaterial.color` ein `Color`-Objekt ist das direkt vom
Renderer gelesen wird); das nächste Frame sieht die neue Farbe.

## Decision

**Option B: imperative Mutation über die `nodeFillMats`-Map.**

Der `nodeColor`-Accessor scheidet aus, weil wir `nodeThreeObject` nutzen —
die Bibliothek hat keine Kontrolle über unsere Materials. Option A wäre nur
nutzbar, wenn wir auf eigene Node-Objekte verzichten, was Outline und Labels
zunichte machen würde.

Die Map-Referenz ist einmalig beim Init aufgebaut; `applyHighlight()` läuft in
O(n) über alle 6124 Nodes in ~1 ms und ist damit framerate-unabhängig aufrufbar.

**Konsequenz für Stufe 5–6:** Alle weiteren visuellen Zustände (Zeit-Filter,
Adjacency-Highlight) müssen denselben Weg gehen — `nodeFillMats` erweitern oder
eine analoge Map für weitere Material-Properties (z. B. Skalierung via
`node.scale`) anlegen. Den `nodeColor`-Accessor nicht für transiente Zustände
verwenden.

## Alternatives considered

- **`nodeColor`-Accessor** — scheidet aus (s. o.): hat keine Wirkung auf
  `nodeThreeObject`-Meshes; außerdem würde jede Änderung den vollen Szenen-Build
  auslösen (~50–200 ms für 6124 Nodes), was Echtzeit-Interaktion spürbar lahmlegt.
- **`Graph.refresh()`** — aktualisiert die gesamte Szene neu; dieselben
  Performance-Probleme wie der Accessor-Weg, und kein klarer Gewinn.
- **Shader-Uniforms / Custom ShaderMaterial** — würde Opacity und Farbe ohne
  CPU-Iteration ändern, aber erfordert Custom-GLSL und bricht die einfache
  MeshBasicMaterial-Schicht. Overkill für 6124 Nodes.
- **Separate Overlay-Objekte (z. B. schwarze halbtransparente Kugeln über
  gedimmten Nodes)** — komplex, erhöht Draw-Calls, keine klare Vereinfachung.

## Consequences

- `nodeFillMats` ist ein Modul-Level-Singleton in `main.ts`; bei einem
  zukünftigen Hot-Reload oder Graph-Rebuild (Jurisdiction-Wechsel) muss die Map
  geleert und neu befüllt werden.
- Outline-Kugeln werden vom Highlight nicht berührt (Outline-Material ist
  geteilt und hat die Hintergrundfarbe). Das ist gewollt: die Outline dient nur
  als Rand und soll nicht mitdimmen.
- Label-Sprites sind ebenfalls nicht betroffen (SpriteMaterial mit Canvas-Textur);
  Labels bleiben beim Dimmen sichtbar. Falls das stört, kann ein zweites
  `labelMats`-Map analog angelegt werden.
