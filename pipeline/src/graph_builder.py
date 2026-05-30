"""Assemble graph nodes and edges from laws_classified + edges_structural."""

import math
from collections import defaultdict


def node_id(jurabk: str | None, slug: str, jurisdiction: str) -> str:
    label = jurabk.strip() if jurabk else slug
    return f"{jurisdiction}/{label}"


def compute_size(degree: int) -> float:
    """Map degree to visual node size: 2 + sqrt(degree) * 1.25."""
    return round(2.0 + math.sqrt(max(0, degree)) * 1.25, 1)


def build_graph(
    laws_classified: dict[str, dict],
    edges_structural: list[dict],
    jurisdiction: str,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (nodes, edges).

    nodes: one per slug in laws_classified with degree and size computed.
    edges: pass-through of edges_structural (already deduplicated by Stage 08).
    """
    slug_to_nid: dict[str, str] = {
        slug: node_id(meta.get("jurabk"), slug, jurisdiction)
        for slug, meta in laws_classified.items()
    }
    known_nids = set(slug_to_nid.values())

    in_deg: dict[str, int] = defaultdict(int)
    out_deg: dict[str, int] = defaultdict(int)
    for edge in edges_structural:
        src, tgt = edge["source"], edge["target"]
        if src in known_nids:
            out_deg[src] += 1
        if tgt in known_nids:
            in_deg[tgt] += 1

    nodes = []
    for slug, meta in laws_classified.items():
        nid = slug_to_nid[slug]
        degree = in_deg[nid] + out_deg[nid]
        nodes.append({
            "id": nid,
            "jurisdiction": jurisdiction,
            "jurabk": meta.get("jurabk"),
            "title": meta.get("langue"),
            "classification": {
                "scheme": "FNA",
                "code": meta.get("fna_code"),
                "main_group": meta.get("main_group"),
            },
            "meta_cluster": None,
            "created_at": meta.get("ausfertigung_datum"),
            "repealed_at": None,
            "x": None,
            "y": None,
            "color": None,
            "size": compute_size(degree),
            "degree": degree,
        })

    return nodes, edges_structural
