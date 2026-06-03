# 015 — Saturn ring for unclassified laws (3D)

**Status:** accepted
**Date:** 2026-06-03

## Context

In the 3D force view, ~46 % of nodes (2806 of 6124) are **unclassified**
(`classification.main_group === null`, ≡ `meta_cluster === "unclassified"`) — laws
with no FNA code. They carry no meaningful map position, so the FA2 x/y is noise for
them. Free-floating in the force cloud they scattered everywhere and drowned the
colour clusters of the ~3318 classified laws: "man kann nicht wirklich Cluster
erkennen". The user asked for them to form "einen dünnen Ring um das ganze … wie bei
Saturn".

## Decision

**Pin the unclassified nodes to a thin, tilted annulus; leave classified nodes
force-driven.** d3-force-3d honours `fx/fy/fz` per node (same mechanism 2D/2.5D
already use), so a *subset* can be pinned while the rest stay simulated in the same
graph.

- `ringPos(i)` places ring node `i` deterministically: **golden-angle** for the
  angle, decorrelated fractional sequences (`i/φ`, plastic constant) for a thin
  radial band and z-jitter, then a tilt about the x-axis. Default ring radius 400,
  width 60, z-jitter 20, tilt 0.35 rad. Stable per-node index built once in node
  array order (`ringIndex`).
- **De-emphasise ring nodes** (they are noise): shrink by `tuneRingDim` (def 0.5)
  in `applyNodeSize`, and recolour to muted slate `#3a3a44` in `applyHighlight`
  (still opaque — ADR 013) unless an active search matches them.
- **Camera fits the clusters, not the ring:** the 3D `zoomToFit` passes a node
  filter to `getGraphBbox` excluding ring nodes, so the central clusters fill the
  view and the ring frames them.
- All five ring parameters are **live sliders** in the existing tuning panel
  (ADR 014). Radius/width/jitter/tilt recompute pinned coords via a new `applyRing()`
  (sibling of `applyPositions`) + `d3ReheatSimulation()`; dim re-runs sizes + highlight.

## Alternatives considered

- **Leave them in the cloud** — rejected: this is the exact problem being fixed.
- **Drop unclassified nodes from 3D entirely** — rejected: they are real laws and
  searchable; hiding them loses information.
- **A second, separate d3 radial force** (forceRadial from d3-force-3d) — rejected:
  a new dependency, and forces only *pull toward* a radius without giving the clean,
  static, evenly-spread ring pinning gives for free. Pinning is simpler and exact.

## Consequences

- The `charge` (many-body) force still runs over all 6124 nodes (pinning stops
  position updates, not force participation) — no perf regression vs. before, but
  the ring does not reduce cost. The ring's repulsion on the cloud is negligible at
  radius 400 and roughly self-cancelling by symmetry, so no per-node charge surgery.
- Every ring-slider drag reheats the engine, so the free cloud visibly "breathes"
  for ~80 ticks before re-settling. Acceptable.
- Default separation (cloud ~250 vs ring inner edge ~370) is tight; clusters pop
  more if the user raises ring radius or centre-gravity. Left to live tuning.
- 2D/2.5D are untouched — `ringIndex` exists in all modes but pinning + the camera
  filter only apply when `mode === '3d'`.
