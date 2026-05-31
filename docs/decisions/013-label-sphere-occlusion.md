# 013 — Label & sphere occlusion: opaque spheres, depth-tested labels, large-only labels

**Status:** accepted
**Date:** 2026-05-31

## Context

Three coupled visual complaints surfaced in live use:
1. Spheres looked see-through when dimmed (search/time filter dimmed nodes to
   `opacity 0.22, transparent`).
2. Reading the text label of a node *behind* a front sphere (label sprites had
   `depthTest: false` → always drawn on top).
3. After fixing (2) with `depthTest: true`, a node's own sphere could clip its own
   label at close/oblique angles.

Requirement, in the user's words: spheres must never be transparent; a front
sphere must hide a rear node's label; but a node must never hide its *own* label.
With a single depth buffer and no per-frame work, "occluded by others but never by
self" has no exact solution — so the resolution is a deliberate compromise.

## Decision

Three rules in `web/src/main.ts`:

1. **Spheres are always opaque.** The dim state (search/time filter) uses a solid
   dark colour (`#23232b`, `opacity 1`, `transparent false`), not reduced opacity.
   Only label sprites and links (`linkOpacity`) may be transparent.
2. **Labels depth-test** (`depthTest: true`) so a closer opaque sphere occludes a
   rear node's label, and float above the *scaled* sphere
   (`label.position.y = baseR·1.3·sizeMul + labelGap`) so a node does not occlude
   its own label in normal viewing.
3. **Only "large" nodes carry a permanent label** (`size ≥ tuneLabelThreshold`,
   default 7.5 → ~top 10%); every other node reveals its label on hover. Far fewer
   visible labels makes the residual self-occlusion edge cases negligible and the
   scene calmer.

## Alternatives considered

- **`depthTest:false` (labels always on top)** — original; lets you read labels
  through front spheres. Rejected (complaint 2).
- **Per-frame camera-facing depth bias** so labels beat their own sphere but lose
  to others — would solve it exactly but needs per-frame JS, which the renderer
  deliberately avoids. Rejected as overkill.
- **All nodes labelled** — clutter + maximises self-occlusion. Rejected; on-hover
  for the long tail is enough.

## Consequences

- `labelGap` and `labelThreshold` are live-tunable (ADR 014); raising `labelGap`
  further reduces any self-occlusion.
- Dimmed nodes are still clearly de-emphasised (dark, recede into the background)
  without transparency — consistent with ADR 010's material-mutation mechanism,
  just opacity-free.
- User preference captured in auto-memory (`feedback-25d-discrete-layers`,
  "Kugeln nie transparent").
