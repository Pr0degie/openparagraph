import pytest

from src.ref_resolver import (
    _short_name_from_langue,
    build_edges_and_resolver,
    build_jurabk_index,
    normalize_book,
    resolve_book,
)


# ── normalize_book ────────────────────────────────────────────────────────────

def test_normalize_book_abbreviation():
    assert normalize_book("BGB") == "bgb"

def test_normalize_book_lowercase_passthrough():
    assert normalize_book("bgb") == "bgb"

def test_normalize_book_strips_spaces():
    assert normalize_book("Bürgerliches Gesetzbuch") == normalize_book("BürgerlichesGesetzbuch")

def test_normalize_book_strips_accents():
    # ü → u, ö → o etc.
    result = normalize_book("Bürgerliches Gesetzbuch")
    assert "u" in result   # ü became u
    assert "ü" not in result

def test_normalize_book_eszett():
    assert normalize_book("Straßenverkehrsgesetz") == normalize_book("Strassenverkehrsgesetz")

def test_normalize_book_genitive_es_long():
    # "aufenthaltsgesetzes" → strip -es → "aufenthaltsgesetz"
    base = normalize_book("Aufenthaltsgesetz")
    gen  = normalize_book("Aufenthaltsgesetzes")
    assert base == gen

def test_normalize_book_genitive_not_stripped_short():
    # Short words must not have -es stripped ("des" must not become "d")
    assert normalize_book("des") == "des"   # too short to strip

def test_normalize_book_empty():
    assert normalize_book("") == ""


# ── _short_name_from_langue ───────────────────────────────────────────────────

def test_short_name_extracts_parenthetical():
    langue = "Gesetz über den Aufenthalt, die Erwerbstätigkeit … (Aufenthaltsgesetz)"
    assert _short_name_from_langue(langue) == "Aufenthaltsgesetz"

def test_short_name_none_when_no_parens():
    assert _short_name_from_langue("Bürgerliches Gesetzbuch") is None

def test_short_name_ignores_short_parenthetical():
    # Parens must contain ≥ 4 chars
    assert _short_name_from_langue("Gesetz (BGB)") is None  # "BGB" = 3 chars

def test_short_name_uses_last_parenthetical():
    langue = "Gesetz (Alte Abk.) über X (NeuesGesetz)"
    assert _short_name_from_langue(langue) == "NeuesGesetz"


# ── build_jurabk_index ────────────────────────────────────────────────────────

def _make_slug_table():
    return {
        "bgb": {"jurabk": "BGB", "langue": "Bürgerliches Gesetzbuch"},
        "aufenthg_2004": {
            "jurabk": "AufenthG",
            "langue": "Gesetz über den Aufenthalt … (Aufenthaltsgesetz)",
        },
        "stgb": {"jurabk": "StGB", "langue": "Strafgesetzbuch"},
    }

def _make_toc():
    return {
        "bgb":           {"title": "Bürgerliches Gesetzbuch", "zip_url": ""},
        "aufenthg_2004": {"title": "Aufenthaltsgesetz", "zip_url": ""},
        "stgb":          {"title": "Strafgesetzbuch", "zip_url": ""},
    }


def test_index_jurabk_lookup():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    assert idx.get(normalize_book("BGB")) == "bgb"
    assert idx.get(normalize_book("StGB")) == "stgb"

def test_index_toc_title_lookup():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    # TOC title "Aufenthaltsgesetz" must index the slug
    assert idx.get(normalize_book("Aufenthaltsgesetz")) == "aufenthg_2004"

def test_index_langue_parenthetical_lookup():
    idx = build_jurabk_index(_make_slug_table(), {})
    # Short name from langue: "(Aufenthaltsgesetz)" → key added
    assert idx.get(normalize_book("Aufenthaltsgesetz")) == "aufenthg_2004"

def test_index_excludes_very_short_keys():
    slug_table = {"xy": {"jurabk": "XY", "langue": "Xy"}}
    toc = {}
    idx = build_jurabk_index(slug_table, toc)
    # "xy" normalizes to "xy" (2 chars) → excluded
    assert "xy" not in idx


# ── resolve_book ─────────────────────────────────────────────────────────────

def test_resolve_book_abbreviation():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    assert resolve_book("bgb", idx) == "bgb"
    assert resolve_book("BGB", idx) == "bgb"

def test_resolve_book_long_form():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    assert resolve_book("Aufenthaltsgesetz", idx) == "aufenthg_2004"

def test_resolve_book_genitive():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    # "aufenthaltsgesetzes" → strip -es → same key as "aufenthaltsgesetz"
    assert resolve_book("Aufenthaltsgesetzes", idx) == "aufenthg_2004"

def test_resolve_book_unknown_returns_none():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    assert resolve_book("unbekanntes gesetz xyz", idx) is None


# ── build_edges_and_resolver ─────────────────────────────────────────────────

def _sample_refs():
    return [
        {"source_slug": "stgb", "book": "bgb",   "span_text": "§ 242 BGB",
         "number": "242", "unit": "paragraph", "confidence": 0.9,
         "source_norm_id": "242"},
        {"source_slug": "stgb", "book": "bgb",   "span_text": "§ 433 BGB",
         "number": "433", "unit": "paragraph", "confidence": 0.9,
         "source_norm_id": "242"},  # same source→target pair, diff span
        {"source_slug": "bgb",  "book": "stgb",  "span_text": "§ 1 StGB",
         "number": "1",   "unit": "paragraph", "confidence": 0.8,
         "source_norm_id": "1"},
        {"source_slug": "bgb",  "book": "unbekannt", "span_text": None,
         "number": "1",   "unit": "paragraph", "confidence": 0.5,
         "source_norm_id": "1"},   # unresolvable
    ]


def test_edges_deduplicated():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    edges, _, stats = build_edges_and_resolver(_sample_refs(), idx, _make_slug_table(), "de-bund")
    # stgb→bgb appears twice in refs but must produce only ONE edge
    stgb_bgb = [e for e in edges if "StGB" in e["source"] and "BGB" in e["target"]]
    assert len(stgb_bgb) == 1

def test_edges_shape():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    edges, _, _ = build_edges_and_resolver(_sample_refs(), idx, _make_slug_table(), "de-bund")
    for e in edges:
        assert e["type"] == "explicit"
        assert e["weight"] == 1.0
        assert "source" in e and "target" in e

def test_edges_node_id_format():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    edges, _, _ = build_edges_and_resolver(_sample_refs(), idx, _make_slug_table(), "de-bund")
    for e in edges:
        assert e["source"].startswith("de-bund/")
        assert e["target"].startswith("de-bund/")

def test_resolver_populated():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    _, resolver, _ = build_edges_and_resolver(_sample_refs(), idx, _make_slug_table(), "de-bund")
    assert "§ 242 bgb" in resolver
    assert resolver["§ 242 bgb"] == "de-bund/BGB"

def test_stats_coverage():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    _, _, stats = build_edges_and_resolver(_sample_refs(), idx, _make_slug_table(), "de-bund")
    # 3 refs resolve, 1 doesn't
    assert stats["resolved"] == 3
    assert stats["unresolved"] == 1
    assert 0 < stats["coverage_pct"] < 100

def test_unresolvable_citation_dropped():
    idx = build_jurabk_index(_make_slug_table(), _make_toc())
    edges, resolver, _ = build_edges_and_resolver(_sample_refs(), idx, _make_slug_table(), "de-bund")
    all_targets = {e["target"] for e in edges}
    # "unbekannt" must not appear as a target
    assert not any("unbekannt" in t for t in all_targets)
