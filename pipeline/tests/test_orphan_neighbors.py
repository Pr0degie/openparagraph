import numpy as np
import pytest

from src.orphan_neighbors import compute_soft_edges, orphan_indices

# 4 laws: bgb + stgb classified (main_group=4), two orphans (main_group=None)
LAWS = {
    "bgb": {"jurabk": "BGB", "langue": "BGB", "main_group": 4, "fna_code": "400-2"},
    "stgb": {"jurabk": "StGB", "langue": "StGB", "main_group": 4, "fna_code": "450-2"},
    "orphan_a": {"jurabk": "OA", "langue": "Orphan A", "main_group": None, "fna_code": None},
    "orphan_b": {"jurabk": "OB", "langue": "Orphan B", "main_group": None, "fna_code": None},
}
SLUGS = sorted(LAWS.keys())   # ["bgb", "orphan_a", "orphan_b", "stgb"]

# Deterministic 3-dim embeddings (L2-normalised)
_raw = np.array([
    [1.0, 0.0, 0.0],   # bgb
    [0.9, 0.4, 0.0],   # orphan_a  (close to bgb)
    [0.0, 1.0, 0.0],   # orphan_b  (close to stgb)
    [0.0, 0.9, 0.4],   # stgb
], dtype=np.float32)
# L2-normalise each row
EMBEDDINGS = _raw / np.linalg.norm(_raw, axis=1, keepdims=True)


def test_orphan_indices_finds_orphans():
    idxs = orphan_indices(LAWS, SLUGS)
    orphan_slugs = {SLUGS[i] for i in idxs}
    assert orphan_slugs == {"orphan_a", "orphan_b"}


def test_orphan_indices_excludes_classified():
    idxs = orphan_indices(LAWS, SLUGS)
    classified = {SLUGS[i] for i in idxs}
    assert "bgb" not in classified
    assert "stgb" not in classified


def test_compute_soft_edges_count_k1():
    o_idxs = orphan_indices(LAWS, SLUGS)
    edges = compute_soft_edges(SLUGS, EMBEDDINGS, LAWS, o_idxs, k=1, weight=0.1, jurisdiction="de-bund")
    # 2 orphans × 1 neighbour = 2 edges
    assert len(edges) == 2


def test_compute_soft_edges_count_k2():
    o_idxs = orphan_indices(LAWS, SLUGS)
    edges = compute_soft_edges(SLUGS, EMBEDDINGS, LAWS, o_idxs, k=2, weight=0.1, jurisdiction="de-bund")
    # 2 orphans × 2 neighbours = 4 edges
    assert len(edges) == 4


def test_compute_soft_edges_schema():
    o_idxs = orphan_indices(LAWS, SLUGS)
    edges = compute_soft_edges(SLUGS, EMBEDDINGS, LAWS, o_idxs, k=1, weight=0.1, jurisdiction="de-bund")
    for e in edges:
        assert e["type"] == "soft"
        assert e["weight"] == 0.1
        assert e["valid_from"] is None
        assert e["valid_to"] is None
        assert e["source"].startswith("de-bund/")
        assert e["target"].startswith("de-bund/")


def test_compute_soft_edges_no_self_edges():
    o_idxs = orphan_indices(LAWS, SLUGS)
    edges = compute_soft_edges(SLUGS, EMBEDDINGS, LAWS, o_idxs, k=3, weight=0.1, jurisdiction="de-bund")
    for e in edges:
        assert e["source"] != e["target"]


def test_compute_soft_edges_orphan_a_nearest_is_bgb():
    # orphan_a embedding is [0.9, 0.4, 0.0] → closest to bgb [1.0, 0.0, 0.0]
    o_idxs = orphan_indices(LAWS, SLUGS)
    edges = compute_soft_edges(SLUGS, EMBEDDINGS, LAWS, o_idxs, k=1, weight=0.1, jurisdiction="de-bund")
    oa_edges = [e for e in edges if e["source"] == "de-bund/OA"]
    assert len(oa_edges) == 1
    assert oa_edges[0]["target"] == "de-bund/BGB"


def test_compute_soft_edges_empty_when_no_orphans():
    all_classified = {
        slug: {**meta, "main_group": 4} for slug, meta in LAWS.items()
    }
    slugs = sorted(all_classified.keys())
    o_idxs = orphan_indices(all_classified, slugs)
    edges = compute_soft_edges(slugs, EMBEDDINGS, all_classified, o_idxs, k=5, weight=0.1, jurisdiction="de-bund")
    assert edges == []


def test_compute_soft_edges_k_clamped_to_available():
    o_idxs = orphan_indices(LAWS, SLUGS)
    # k=100 but only 3 other laws available
    edges = compute_soft_edges(SLUGS, EMBEDDINGS, LAWS, o_idxs, k=100, weight=0.1, jurisdiction="de-bund")
    # Each orphan gets at most len(SLUGS)-1 = 3 neighbours
    per_orphan = {}
    for e in edges:
        per_orphan.setdefault(e["source"], []).append(e)
    for src, src_edges in per_orphan.items():
        assert len(src_edges) <= len(SLUGS) - 1
