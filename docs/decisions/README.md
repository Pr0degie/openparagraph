# Decisions

Architecture Decision Records (ADRs). One file per non-trivial decision that
shapes the project, numbered sequentially: `001-…`, `002-…`. Past Tobi and
future Tobi (and any contributor) should be able to read these and understand
*why* something is the way it is — including what was rejected and on what
grounds.

## When to write one

- Stufe 0 spikes always produce one (Spike A → 001, Spike B → 002, Spike C → 003).
- Any time a session reaches a decision with real trade-offs (e.g. "we chose
  forward patches over reverse patches because …").
- Any time you flip an earlier decision — write a *new* ADR that supersedes the
  old one. Never edit history.

## Format

Keep it short. Aim for one screen of text, not a thesis.

```markdown
# NNN — Short imperative title

**Status:** accepted | superseded by NNN | rejected
**Date:** YYYY-MM-DD

## Context
A few sentences on the situation that forced a decision.

## Decision
What we're going to do.

## Alternatives considered
- Option B — rejected because …
- Option C — rejected because …

## Consequences
Things that follow from this — both intended and ones to watch out for.
```

That's it. Don't gold-plate the format.
