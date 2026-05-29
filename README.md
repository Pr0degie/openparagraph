# openparagraph

**A visual git for German law.** Every federal law as a node, every statutory
cross-reference as an edge, laid out so that related laws cluster on their own —
colored by legal domain, navigable through time.

> Status: **early development (Stufe 0).** See [ROADMAP.md](./ROADMAP.md).

---

## Why

German federal law is freely available at gesetze-im-internet.de — but only as
~6,000 separate documents in their current form. You cannot *see* the structure:
which laws lean on which, where the dense clusters of civil or tax law are, how
the body of law has grown over the decades. openparagraph turns that invisible
structure into a map you can explore.

## What it does

- **Cluster map.** A WebGL force-directed graph of all federal laws. Laws that
  reference each other pull together; nine legal domains give nine colors.
- **Drill in.** Click a law to read its full text. Every `§`-reference is a link —
  click it to fly to the law it points at.
- **Time travel.** A slider walks the corpus through history; watch laws appear
  and disappear across the decades. Per-law version diffs for recent changes.
- **Search.** Instant full-text search that lights up matching laws in the graph.

## How it works

A Python [Snakemake](https://snakemake.github.io/) pipeline pulls the official
XML from gesetze-im-internet.de and the git history from community law mirrors,
extracts cross-references with
[`legal-reference-extraction`](https://github.com/openlegaldata/legal-reference-extraction),
classifies laws by their Fundstellennachweis A (FNA) domain, computes a
ForceAtlas2 layout, and emits static JSON. A Vite + TypeScript + sigma.js
frontend renders it. No server, no database — just static files refreshed by a
scheduled GitHub Action.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design.

## Tech stack

| | |
|---|---|
| Pipeline | Python 3.12, Snakemake, lxml, sentence-transformers, fa2_modified |
| References | openlegaldata/legal-reference-extraction |
| Frontend | TypeScript, Vite, sigma.js v3, graphology, FlexSearch, diff-match-patch |
| Hosting | Static (Vercel / Netlify / GH Pages) + GitHub Actions cron |

## Data sources

All inputs are official works free of copyright (`Gesetze sind amtliche Werke`):

- [gesetze-im-internet.de](https://www.gesetze-im-internet.de/gii-toc.xml) — current law XML
- [kmein/gesetze](https://github.com/kmein/gesetze) — daily-updated git history (versions from ~April 2021)
- [Fundstellennachweis A](https://www.recht.bund.de/) — legal-domain taxonomy

## Quick start

```bash
# Pipeline (Python, via uv)
cd pipeline
uv sync
snakemake --cores 4 bundle      # builds /data from scratch

# Frontend (via pnpm)
cd web
pnpm install
pnpm dev                         # http://localhost:5173
```

Or open the repo in the provided **dev container** for a one-click environment.

## Roadmap (short version)

- **v1** — federal laws: cluster map, detail view, search, time slider
- **v1.1** — mobile + DE/EN UI
- **v2** — regulations + Landesrecht + draft-stage *branches* (DIP)
- **v3** — EU law (EUR-Lex)

Full detail in [ROADMAP.md](./ROADMAP.md).

## Contributing

Contributions welcome. The data is public and the build is reproducible — clone,
run the pipeline, and you have the whole corpus locally. See ARCHITECTURE.md for
how the pieces fit, then open an issue before large changes.

## License

[MIT](./LICENSE). The underlying legal texts are official works not subject to
copyright.

---

*Built by [@Pr0degie](https://github.com/Pr0degie).*
