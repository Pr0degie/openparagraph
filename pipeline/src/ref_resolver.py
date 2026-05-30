"""Resolve raw refex citations to graph edges and the frontend resolver.

Stage 08 loads build/refs_raw.json (Stage 07) and build/slug_table.json
(Stage 02) + build/toc.json (Stage 01) and emits:

  build/edges_structural.json        — deduplicated {source, target} pairs
  data/_global/reference-resolver.json — span_text → node_id for the frontend

Resolution strategy (ADR 003):
  1. normalize_book(refex book) → look up in jurabk_index
  2. jurabk_index is built from three key sources per slug:
       a. jurabk abbreviation (e.g. "bgb" → BGB)
       b. TOC common title (e.g. "aufenthaltsgesetz")
       c. Parenthetical short name from langue
         ("... (Aufenthaltsgesetz)" → "aufenthaltsgesetz")

Expected coverage after Stage 07 filtering: ~55–65 % of raw citations.
Unresolved citations are silently dropped (no edge, no resolver entry).
"""
from __future__ import annotations

import re
import unicodedata


# ── normalisation ─────────────────────────────────────────────────────────────

def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def normalize_book(book: str) -> str:
    """Normalize a refex book string for index lookup.

    Steps:
    1. Strip accents, lowercase, ß → ss
    2. Remove all non-alphanumeric characters (spaces, punctuation)
    3. Strip German genitive suffix -es from long words only
       ("aufenthaltsgesetzes" → "aufenthaltsgesetz",
        "burgerlichengesetzbuches" → "burgerlichengesetzbuch")
    """
    if not book:
        return ""
    s = _strip_accents(book).lower().replace("ß", "ss")
    s = re.sub(r"[^a-z0-9]", "", s)
    if len(s) > 10 and s.endswith("es"):
        s = s[:-2]
    elif len(s) > 8 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    return s


def _short_name_from_langue(langue: str) -> str | None:
    """Extract parenthetical short name from a formal law title.

    'Gesetz über den Aufenthalt ... (Aufenthaltsgesetz)' → 'Aufenthaltsgesetz'
    Returns None if no suitable parenthetical is found.
    """
    m = re.search(r"\(([^()]{4,})\)\s*$", langue)
    return m.group(1).strip() if m else None


# ── index building ────────────────────────────────────────────────────────────

def build_jurabk_index(
    slug_table: dict[str, dict],
    toc: dict[str, dict],
) -> dict[str, str]:
    """Build {normalized_key → slug} for citation resolution.

    Key sources per slug (in priority order, first write wins):
      1. jurabk abbreviation — "BGB" → "bgb" → {bgb: <slug>}
      2. TOC common title   — "Aufenthaltsgesetz" → {aufenthaltsgesetz: <slug>}
      3. Short name from langue parenthetical

    Keys shorter than 3 chars after normalization are excluded to prevent
    false-positive matches on very short abbreviations.
    """
    index: dict[str, str] = {}

    def _add(raw: str, slug: str) -> None:
        key = normalize_book(raw)
        if len(key) >= 3:
            index.setdefault(key, slug)

    # Pass 1: jurabk abbreviations (highest priority — most precise)
    for slug, meta in slug_table.items():
        if meta.get("jurabk"):
            _add(meta["jurabk"], slug)

    # Pass 2: TOC common titles
    for slug, info in toc.items():
        if info.get("title"):
            _add(info["title"], slug)

    # Pass 3: short names from langue parentheticals
    for slug, meta in slug_table.items():
        if meta.get("langue"):
            short = _short_name_from_langue(meta["langue"])
            if short:
                _add(short, slug)

    return index


# ── resolution ────────────────────────────────────────────────────────────────

def resolve_book(book: str, index: dict[str, str]) -> str | None:
    """Return the slug for a refex book value, or None if unresolved."""
    return index.get(normalize_book(book))


# ── output building ───────────────────────────────────────────────────────────

def build_edges_and_resolver(
    refs_raw: list[dict],
    index: dict[str, str],
    slug_table: dict[str, dict],
    jurisdiction: str,
) -> tuple[list[dict], dict[str, str]]:
    """Resolve all raw citations; return (edges_list, resolver_dict).

    edges_list: deduplicated {source, target, type, weight, valid_from, valid_to}
      One entry per unique (source_id, target_id) pair.
      valid_from/valid_to are null here — Stage 14 (diff_cache) adds dates.

    resolver_dict: {normalized_span_text → target_node_id}
      Used by the frontend to make citation text clickable.
      First span_text that resolves a given target wins.
    """
    def _node_id(slug: str) -> str:
        meta = slug_table.get(slug, {})
        jurabk = meta.get("jurabk") or slug
        return f"{jurisdiction}/{jurabk}"

    edge_set: set[tuple[str, str]] = set()
    edges: list[dict] = []
    resolver: dict[str, str] = {}
    resolved = unresolved = 0

    for ref in refs_raw:
        source_slug = ref.get("source_slug", "")
        book = ref.get("book", "")
        span_text = ref.get("span_text")

        target_slug = resolve_book(book, index)
        if not target_slug:
            unresolved += 1
            continue
        resolved += 1

        source_id = _node_id(source_slug)
        target_id = _node_id(target_slug)

        pair = (source_id, target_id)
        if pair not in edge_set:
            edge_set.add(pair)
            edges.append({
                "source": source_id,
                "target": target_id,
                "type": "explicit",
                "weight": 1.0,
                "valid_from": None,
                "valid_to": None,
            })

        if span_text:
            resolver.setdefault(span_text.lower().strip(), target_id)

    total = resolved + unresolved
    return edges, resolver, {
        "resolved": resolved,
        "unresolved": unresolved,
        "coverage_pct": round(100 * resolved / total, 1) if total else 0.0,
        "unique_edges": len(edges),
        "resolver_entries": len(resolver),
    }
