# Archived: sigma.js 2D renderer

This is the **superseded** sigma.js + graphology frontend, kept for reference
only. It is **not** part of the build (it lives outside `web/src/`, so it is
neither type-checked nor bundled) and the `sigma` / `graphology` /
`graphology-layout` dependencies have been removed from `web/package.json` —
these files will not compile as-is anymore.

**Why it was retired:** see `docs/decisions/009-single-renderer-3d.md`. The app
moved to a single Three.js renderer (`3d-force-graph`) that serves the 2D, 2.5D
and 3D views from one code path. The old flat-2D look (crisp circles + thin dark
border) is reproduced in the new renderer with `MeshBasicMaterial` + a BackSide
outline.

## Files

- `main.ts` — Sigma instantiation + options (camera ratios, edge arrows, label threshold)
- `graph.ts` — built a graphology `DirectedGraph` from `nodes.json` / `edges.json`
- `node-border-program.ts` — custom WebGL fragment shader: thin dark border ring on nodes

## To restore (if ever needed)

1. `pnpm add sigma graphology graphology-layout`
2. Move these three files back into `web/src/`
3. Point `web/index.html` at the restored `main.ts`
4. Remove the Three.js renderer or gate it behind a flag

This whole folder is safe to delete once you're confident the 3D renderer covers
everything.
