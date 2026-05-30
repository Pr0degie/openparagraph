"""Extract cross-law citations from parsed GII law norms.

Stage 07 runs `refex` (legal-reference-extraction) over every norm in
build/laws_parsed/ and emits build/refs_raw.json — a list of filtered
citation records used by Stage 08 (resolve_refs) to build graph edges
and the frontend reference resolver.

Design notes
------------
* refex is CPU-bound, so Stage 07 uses ProcessPoolExecutor.  Worker
  functions MUST be module-level (pickleable); closures defined inside a
  Snakemake run: block are not.  The CitationExtractor is created once per
  worker process via the `initializer` argument.

* The false-positive filter (ADR 003) is applied here, before writing to
  disk, so Stage 08 never sees generic German words ("vorschriften" etc.)
  that refex mis-classifies as law names.

* `span_text` is stored in refs_raw.json so Stage 08 can build
  reference-resolver.json entries that map literal citation text to slugs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# ── false-positive filter (ADR 003) ──────────────────────────────────────────

FALSE_POSITIVES: frozenset[str] = frozenset({
    # Generic German legal vocabulary that refex mistakes for law names
    "vorschriften", "vorschrift",
    "verordnung", "rechtsverordnung",
    "anordnung",
    "haftung",
    "bundes",
    "überwachung",
    "ordnungswidrigkeiten",
    "bestimmungen", "bestimmung",
    "regelung", "regelungen",
    "gesetz",           # too generic on its own; caught only when book == "gesetz"
})


def is_false_positive(book: str) -> bool:
    """Return True if the refex book value is a known false-positive token."""
    return (book or "").lower() in FALSE_POSITIVES


# ── text normalisation ────────────────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(text_xml: str) -> str:
    """Replace XML/HTML tags with spaces and collapse whitespace."""
    text = _TAG_RE.sub(" ", text_xml)
    return re.sub(r"\s+", " ", text).strip()


# ── per-process CitationExtractor (initialised once per worker) ───────────────

_extractor = None   # set by init_extractor() in each worker process


def init_extractor() -> None:
    """ProcessPoolExecutor initializer: create one CitationExtractor per worker."""
    global _extractor
    from refex.orchestrator import CitationExtractor  # noqa: PLC0415
    _extractor = CitationExtractor()


# ── core worker (must be module-level to be pickleable) ──────────────────────

def process_law_file(json_path_str: str) -> list[dict]:
    """Read {slug}.json, run refex on all norms, return filtered citation records.

    Called inside a worker process where _extractor is already initialised.
    Per-norm exceptions are caught and skipped so one bad norm doesn't abort
    the whole law.
    """
    json_path = Path(json_path_str)
    slug = json_path.stem

    try:
        law_dict = json.loads(json_path.read_text())
    except Exception:
        return []

    records: list[dict] = []
    for norm in law_dict.get("norms", []):
        text_xml = norm.get("text_xml")
        if not text_xml:
            continue
        plain = strip_tags(text_xml)
        if not plain:
            continue

        norm_id_val = norm.get("norm_id", "")
        try:
            result = _extractor.extract(plain)
        except Exception:
            continue  # refex crash on this norm — skip, not fatal

        for c in result.citations:
            book = (c.book or "").lower()
            if not book or is_false_positive(book):
                continue
            records.append({
                "source_slug": slug,
                "source_norm_id": norm_id_val,
                "book": book,
                "number": c.number,
                "unit": c.unit,
                "span_text": c.span.text if c.span else None,
                "confidence": c.confidence,
            })

    return records
