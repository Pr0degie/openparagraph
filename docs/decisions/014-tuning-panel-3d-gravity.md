# 014 — Live tuning panel + 3D centre-gravity force

**Status:** accepted
**Date:** 2026-05-31

## Context

Dialling the spore/cluster aesthetic by editing constants and rebuilding is slow.
The user asked for live sliders ("ein paar Slider … damit ich das ganze fine tunen
kann") and, specifically for 3D, that "alle Knoten zum Mittelpunkt hingezogen aber
auch schwächer abgestoßen werden".

## Decision

**Tuning panel** (`initTunePanel` in `ui.ts`): a collapsible box of range sliders,
each with a live numeric readout, firing `onChange(key, value)` on input. The spec
is **mode-aware** — sphere sizes + label threshold/offset always; node/layer
spacing in 2D/2.5D; centre-gravity + repulsion in 3D.

Apply strategy by cost:
- **Sizes / labels** mutate the existing meshes directly (`mesh.scale`,
  `label.visible`, `label.position`) — instant, no rebuild.
- **Positions** (2D/2.5D `spread`, 2.5D `layerGap`) recompute the fixed coords and
  then call `Graph.d3ReheatSimulation()`. **Why reheat:** three-forcegraph only
  writes object positions inside `layoutTick`, which runs only while the engine is
  running; with `cooldownTicks(0)` it cools after one tick, so a direct
  `group.position` set is never re-applied. Reheating runs one tick that rewrites
  positions from the new (still pinned) coords — nothing drifts.

**3D forces:** pull every node toward the origin with a hand-rolled d3 force
(`centerGravityForce`, adds `-pos · strength · alpha` to each node's velocity;
default strength 0.18) and soften the default repulsion
(`d3Force('charge').strength(-12)`, vs d3's ~−30). Both live-tunable; changes
reheat the simulation.

## Alternatives considered

- **`d3-force-3d`'s `forceRadial` for centre gravity** — would work, but pulls in a
  dependency just for one force. Hand-rolling the force is ~8 lines and keeps the
  no-new-heavy-deps rule (CLAUDE.md §5). Rejected.
- **Rebuild via `Graph.graphData(...)` for position changes** — re-runs
  `nodeThreeObject` for all 6124 nodes per slider tick; far too heavy. Rejected in
  favour of the reheat trick.
- **dat.GUI / leva** — external tuning-UI deps; overkill for a handful of sliders.

## Consequences

- The panel is currently always shown (dev convenience). Before v1, decide whether
  to hide it behind a flag/hash or keep it. Defaults the user settles on should be
  baked into the `tune*` consts in `main.ts`.
- 3D-only forces are no-ops in 2D/2.5D (nodes are statically pinned) — harmless.
- The `d3ReheatSimulation` position-update trick is also the reason a casual full
  pipeline rebuild reshuffles the 2D layout — see the FA2 non-reproducibility
  caveat in ARCHITECTURE §7 and PROGRESS.
