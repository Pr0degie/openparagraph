import numpy as np
import pytest

from src.layout_builder import build_nx_graph, pca_z

# We test build_nx_graph (pure Python, no FA2) extensively.
# run_layout is tested with a smoke test using a tiny graph + few iterations.

NODES = [
    {"id": "de-bund/BGB"},
    {"id": "de-bund/StGB"},
    {"id": "de-bund/HGB"},
    {"id": "de-bund/AO"},
]

EDGES = [
    {"source": "de-bund/BGB", "target": "de-bund/HGB", "weight": 1.0},
    {"source": "de-bund/BGB", "target": "de-bund/StGB", "weight": 1.0},
    {"source": "de-bund/StGB", "target": "de-bund/AO", "weight": 0.1},
    # cross-jurisdiction edge — should be skipped
    {"source": "de-bund/BGB", "target": "eu/CELEX:32016R0679", "weight": 1.0},
]


# ---------------------------------------------------------------------------
# build_nx_graph
# ---------------------------------------------------------------------------


def test_build_nx_graph_node_count():
    G = build_nx_graph(NODES, EDGES)
    assert G.number_of_nodes() == len(NODES)


def test_build_nx_graph_skips_cross_jurisdiction_edges():
    G = build_nx_graph(NODES, EDGES)
    assert not G.has_node("eu/CELEX:32016R0679")


def test_build_nx_graph_edge_count():
    G = build_nx_graph(NODES, EDGES)
    # 3 within-jurisdiction edges
    assert G.number_of_edges() == 3


def test_build_nx_graph_isolated_node_included():
    nodes = NODES + [{"id": "de-bund/isolated"}]
    G = build_nx_graph(nodes, EDGES)
    assert "de-bund/isolated" in G.nodes


def test_build_nx_graph_parallel_edges_accumulate_weight():
    nodes = [{"id": "A"}, {"id": "B"}]
    edges = [
        {"source": "A", "target": "B", "weight": 1.0},
        {"source": "A", "target": "B", "weight": 0.1},
    ]
    G = build_nx_graph(nodes, edges)
    assert G.number_of_edges() == 1
    assert abs(G["A"]["B"]["weight"] - 1.1) < 1e-6


def test_build_nx_graph_empty():
    G = build_nx_graph([], [])
    assert G.number_of_nodes() == 0
    assert G.number_of_edges() == 0


# ---------------------------------------------------------------------------
# run_layout — smoke test with few iterations
# ---------------------------------------------------------------------------


def test_run_layout_returns_all_nodes():
    from src.layout_builder import run_layout

    positions = run_layout(
        nodes=NODES,
        edges=EDGES,
        seed=42,
        iterations=10,
        scaling_ratio=2.0,
        gravity=1.0,
        strong_gravity=False,
        barnes_hut_theta=1.2,
        outbound_attraction_distribution=True,
    )
    assert set(positions.keys()) == {n["id"] for n in NODES}


def test_run_layout_output_schema():
    from src.layout_builder import run_layout

    positions = run_layout(
        nodes=NODES,
        edges=EDGES,
        seed=42,
        iterations=10,
        scaling_ratio=2.0,
        gravity=1.0,
        strong_gravity=False,
        barnes_hut_theta=1.2,
        outbound_attraction_distribution=True,
    )
    for nid, coords in positions.items():
        assert "x" in coords and "y" in coords
        assert isinstance(coords["x"], float)
        assert isinstance(coords["y"], float)


def test_run_layout_reproducible_with_same_seed():
    from src.layout_builder import run_layout

    kwargs = dict(
        nodes=NODES,
        edges=EDGES,
        seed=42,
        iterations=20,
        scaling_ratio=2.0,
        gravity=1.0,
        strong_gravity=False,
        barnes_hut_theta=1.2,
        outbound_attraction_distribution=True,
    )
    p1 = run_layout(**kwargs)
    p2 = run_layout(**kwargs)
    for nid in p1:
        assert abs(p1[nid]["x"] - p2[nid]["x"]) < 1e-4
        assert abs(p1[nid]["y"] - p2[nid]["y"]) < 1e-4


# ---------------------------------------------------------------------------
# pca_z — semantic z-axis for the 3D layout
# ---------------------------------------------------------------------------

def _toy_embeddings():
    # Two clear clusters along one axis → PC1 separates them.
    rng = np.random.default_rng(0)
    a = rng.normal(loc=[5.0, 0.0, 0.0], scale=0.1, size=(8, 3))
    b = rng.normal(loc=[-5.0, 0.0, 0.0], scale=0.1, size=(8, 3))
    return np.vstack([a, b]).astype(np.float32)


def test_pca_z_one_value_per_row():
    emb = _toy_embeddings()
    z = pca_z(emb)
    assert z.shape == (emb.shape[0],)


def test_pca_z_is_z_scored():
    z = pca_z(_toy_embeddings())
    assert abs(float(z.mean())) < 1e-6
    assert abs(float(z.std()) - 1.0) < 1e-6


def test_pca_z_is_deterministic():
    emb = _toy_embeddings()
    assert np.allclose(pca_z(emb), pca_z(emb))


def test_pca_z_separates_clusters():
    # The two clusters should land on opposite signs of the principal component.
    z = pca_z(_toy_embeddings())
    assert np.sign(z[:8]).sum() == -np.sign(z[8:]).sum()


def test_pca_z_constant_input_does_not_blow_up():
    # std == 0 → return scores as-is (all ~0) instead of dividing by zero.
    emb = np.ones((5, 4), dtype=np.float32)
    z = pca_z(emb)
    assert np.all(np.isfinite(z))
