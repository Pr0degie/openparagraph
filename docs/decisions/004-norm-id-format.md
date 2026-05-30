# 004 — norm_id: enbez-derived, URL-safe stable identifiers

**Status:** accepted  
**Date:** 2026-05-30

## Context

Stage 04 renders each norm as a `<section>` in `base.html`.  Stage 14 (diff
cache) needs a stable anchor per norm so forward patches can target individual
paragraphs across versions.  The frontend needs the same anchor to scroll to a
specific § when a citation is clicked.

The candidate identifier sources are:

- **enbez** (`§ 1`, `Art. 2`, `Anlage 3`) — human-readable, present in the
  official XML, stable across minor law amendments.
- **Sequential index** (`norm-0`, `norm-1`, …) — trivial to generate, but
  shifts whenever a norm is inserted or deleted, breaking all forward patches.
- **UUID / hash** — stable but opaque and impossible to infer from the law
  text itself.

## Decision

Derive `norm_id` from `enbez` with a small normalization:

- Strip leading `§ ` → the number remains (`§ 1` → `"1"`)
- Replace leading `Art. ` → prefix with `art-` (`Art. 2` → `"art-2"`)
- Collapse remaining whitespace to `-`, remove non-word characters, lowercase
- Fall back to `norm-{idx}` only when `enbez` is absent

Implemented in `src/law_serializer.py::norm_id()`.

## Alternatives considered

- **Sequential index** — rejected: index-based IDs shift on insertions,
  corrupting every forward patch that references a later norm.
- **Hash of enbez + content** — rejected: content changes on every amendment,
  which is exactly when we need the anchor to stay stable for diffing.
- **Raw enbez as-is** (`§ 1`) — rejected: not URL-safe; breaks HTML `id`
  attribute parsing and fragment links.

## Consequences

- The id space is law-local, not globally unique.  Cross-law links are formed
  as `{slug}#{norm_id}` (e.g. `bgb#242`) by the frontend reference resolver.
- Rare norms with no `enbez` (introductory clauses, tables of contents) get
  `norm-{idx}` — index-stable within a single parse, but will shift if the
  header norm count changes.  Acceptable: these norms are rarely citation targets.
- Laws that rename a § (e.g. renumber after a reform) will invalidate the
  corresponding patch anchor.  This is inherent to any enbez-based scheme and
  matches how legal citations work in practice.
