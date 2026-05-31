"""ForceAtlas2 layout for the law reference graph.

Builds an undirected weighted networkx graph from the node list and edge list,
then runs fa2_modified with the settings from ARCHITECTURE.md §7.
"""

import numpy as np
import networkx as nx


def build_nx_graph(nodes: list[dict], edges: list[dict]) -> nx.Graph:
    G: nx.Graph = nx.Graph()
    for n in nodes:
        G.add_node(n["id"])
    known = set(G.nodes)
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src not in known or tgt not in known:
            continue                    # skip cross-jurisdiction edges
        w = float(e.get("weight") or 1.0)
        if G.has_edge(src, tgt):
            G[src][tgt]["weight"] += w  # accumulate parallel soft+hard weights
        else:
            G.add_edge(src, tgt, weight=w)
    return G


def run_layout(
    nodes: list[dict],
    edges: list[dict],
    seed: int,
    iterations: int,
    scaling_ratio: float,
    gravity: float,
    strong_gravity: bool,
    barnes_hut_theta: float,
    outbound_attraction_distribution: bool,
    adjust_sizes: bool = False,
) -> dict[str, dict]:
    """
    Returns {node_id: {"x": float, "y": float}} for every node.
    """
    from fa2_modified import ForceAtlas2  # noqa: PLC0415

    G = build_nx_graph(nodes, edges)

    # Build deterministic initial positions from the fixed seed.
    # Passing pos= explicitly avoids networkx's internal RNG that fa2 calls
    # when pos=None, which doesn't respect np.random.seed().
    rng = np.random.default_rng(seed)
    node_ids = sorted(G.nodes())
    coords = rng.uniform(-10.0, 10.0, size=(len(node_ids), 2))
    pos = {nid: coords[i] for i, nid in enumerate(node_ids)}

    fa2 = ForceAtlas2(
        outboundAttractionDistribution=outbound_attraction_distribution,
        barnesHutOptimize=True,
        barnesHutTheta=barnes_hut_theta,
        scalingRatio=scaling_ratio,
        gravity=gravity,
        strongGravityMode=strong_gravity,
        adjustSizes=adjust_sizes,
        verbose=False,
    )

    positions = fa2.forceatlas2_networkx_layout(G, pos=pos, iterations=iterations)

    return {
        nid: {"x": float(xy[0]), "y": float(xy[1])}
        for nid, xy in positions.items()
    }
