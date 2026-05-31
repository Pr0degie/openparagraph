import math

import pytest

from src.graph_builder import build_graph, compute_size

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LAWS = {
    "bgb": {
        "jurabk": "BGB",
        "langue": "Bürgerliches Gesetzbuch",
        "ausfertigung_datum": "1896-08-18",
        "norm_count": 2385,
        "fna_code": "400-2",
        "main_group": 4,
        "opening_text": "Wer geschäftsfähig ist…",
    },
    "stgb": {
        "jurabk": "StGB",
        "langue": "Strafgesetzbuch",
        "ausfertigung_datum": "1871-05-15",
        "repealed_at": "2026-08-18",
        "norm_count": 358,
        "fna_code": "450-2",
        "main_group": 4,
        "opening_text": "Eine Straftat begeht…",
    },
    "unclassified_1": {
        "jurabk": None,
        "langue": "Gesetz ohne Abkürzung",
        "ausfertigung_datum": None,
        "norm_count": 10,
        "fna_code": None,
        "main_group": None,
        "opening_text": None,
    },
}

EDGES = [
    {
        "source": "DE-BUND/BGB",
        "target": "DE-BUND/StGB",
        "type": "explicit",
        "weight": 1.0,
        "valid_from": None,
        "valid_to": None,
    },
    {
        "source": "DE-BUND/BGB",
        "target": "eu/CELEX:32016R0679",
        "type": "explicit",
        "weight": 1.0,
        "valid_from": None,
        "valid_to": None,
    },
]


# ---------------------------------------------------------------------------
# compute_size
# ---------------------------------------------------------------------------


def test_compute_size_zero_degree():
    assert compute_size(0) == 2.0


def test_compute_size_example_from_architecture():
    # ARCHITECTURE.md example: degree 311 → size 24
    result = compute_size(311)
    assert abs(result - 24.0) < 1.0


def test_compute_size_increases_monotonically():
    sizes = [compute_size(d) for d in [0, 1, 10, 100, 1000]]
    assert sizes == sorted(sizes)


def test_compute_size_negative_clamped_to_zero():
    assert compute_size(-5) == compute_size(0)


# ---------------------------------------------------------------------------
# build_graph — node count and structure
# ---------------------------------------------------------------------------


def test_build_graph_node_count():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    assert len(nodes) == len(LAWS)


def test_build_graph_node_id_uses_jurabk():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    nids = {n["id"] for n in nodes}
    assert "DE-BUND/BGB" in nids
    assert "DE-BUND/StGB" in nids


def test_build_graph_node_id_falls_back_to_slug_when_no_jurabk():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    nids = {n["id"] for n in nodes}
    assert "DE-BUND/unclassified_1" in nids


def test_build_graph_node_schema_fields():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    bgb = next(n for n in nodes if n["id"] == "DE-BUND/BGB")
    assert bgb["jurisdiction"] == "DE-BUND"
    assert bgb["jurabk"] == "BGB"
    assert bgb["title"] == "Bürgerliches Gesetzbuch"
    assert bgb["classification"] == {"scheme": "FNA", "code": "400-2", "main_group": 4}
    assert bgb["meta_cluster"] is None
    assert bgb["created_at"] == "1896-08-18"
    assert bgb["repealed_at"] is None  # no repealed_at in meta → None
    assert bgb["x"] is None
    assert bgb["y"] is None
    assert bgb["color"] is None


def test_build_graph_repealed_at_passed_through():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    stgb = next(n for n in nodes if n["id"] == "DE-BUND/StGB")
    assert stgb["repealed_at"] == "2026-08-18"


def test_build_graph_null_jurabk_law_fields():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    u = next(n for n in nodes if n["id"] == "DE-BUND/unclassified_1")
    assert u["jurabk"] is None
    assert u["classification"] == {"scheme": "FNA", "code": None, "main_group": None}


# ---------------------------------------------------------------------------
# build_graph — degree computation
# ---------------------------------------------------------------------------


def test_build_graph_bgb_out_degree():
    # BGB references StGB (1 edge to known node) + EU law (1 edge to unknown)
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    bgb = next(n for n in nodes if n["id"] == "DE-BUND/BGB")
    # out_degree = 2 (both edges count as out from BGB)
    # but only BGB and StGB are known; EU target is unknown → only 1 out counts?
    # Actually: out_deg counts ALL out-edges where source is a known node.
    # BGB is known, so both its out-edges count → out_deg["DE-BUND/BGB"] = 2
    assert bgb["degree"] >= 2


def test_build_graph_stgb_in_degree():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    stgb = next(n for n in nodes if n["id"] == "DE-BUND/StGB")
    # StGB receives 1 edge from BGB
    assert stgb["degree"] == 1


def test_build_graph_unclassified_degree_zero():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    u = next(n for n in nodes if n["id"] == "DE-BUND/unclassified_1")
    assert u["degree"] == 0


def test_build_graph_size_matches_degree():
    nodes, _ = build_graph(LAWS, EDGES, "DE-BUND")
    for n in nodes:
        expected = compute_size(n["degree"])
        assert n["size"] == expected


# ---------------------------------------------------------------------------
# build_graph — edges pass-through
# ---------------------------------------------------------------------------


def test_build_graph_edges_passed_through():
    _, edges = build_graph(LAWS, EDGES, "DE-BUND")
    assert edges is EDGES  # same object, no copy


def test_build_graph_empty_laws():
    nodes, edges = build_graph({}, [], "DE-BUND")
    assert nodes == []
    assert edges == []
