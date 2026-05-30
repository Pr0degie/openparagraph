# 000 — Use this ADR template

**Status:** accepted (this is just a template / example)
**Date:** 2026-05-30

## Context
We need a lightweight way to record the *why* behind decisions so that future
sessions (and contributors, and our own future selves after a few weeks away)
don't have to reverse-engineer reasoning from code. Long planning docs go stale;
chat history disappears when context is cleared.

## Decision
Use lightweight, numbered ADRs in `docs/decisions/`, one per real decision,
following the template in this folder's README. Each ADR is immutable once
accepted — if we change our minds, we write a new ADR that supersedes the old
one.

## Alternatives considered
- **Inline comments only** — rejected because they explain local code but not
  cross-cutting choices (e.g. why we picked sigma.js over cosmos.gl).
- **One big DECISIONS.md** — rejected because it grows into a chronological
  blob that's hard to reference and risky to edit.
- **Confluence / Notion** — rejected because it lives outside the repo and
  contributors can't see it.

## Consequences
- Decisions live in the repo, versioned alongside the code they shaped.
- New sessions can be primed by "read the latest ADR" in addition to
  `PROGRESS.md`.
- Slight friction at decision time — but writing one is a forcing function for
  thinking the choice through clearly.
