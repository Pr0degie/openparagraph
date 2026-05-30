"""Find top-K cosine neighbours for orphan laws (laws with no FNA code).

Orphans are laws where main_group is None.  For each orphan we emit K soft
edges pointing at the K most similar laws (by embedding cosine similarity).
Embeddings must be L2-normalised (cosine = dot product).

Row order in the embeddings array must match sorted(laws_classified.keys()),
which is guaranteed by embedder.texts_for_embedding.
"""

import numpy as np

from .graph_builder import node_id


def orphan_indices(laws_classified: dict[str, dict], slugs: list[str]) -> list[int]:
    """Row indices (in slugs order) of laws that have no FNA main_group."""
    return [i for i, slug in enumerate(slugs) if laws_classified[slug].get("main_group") is None]


def compute_soft_edges(
    slugs: list[str],
    embeddings: np.ndarray,
    laws_classified: dict[str, dict],
    orphan_idxs: list[int],
    k: int,
    weight: float,
    jurisdiction: str,
) -> list[dict]:
    """
    For each orphan law return its top-K nearest neighbours as soft edges.

    Edges go orphan → neighbour (directed; layout treats them as undirected).
    Self-edges are excluded.  If fewer than K candidates exist, all are used.
    """
    if not orphan_idxs:
        return []

    orphan_embs = embeddings[orphan_idxs]          # (M, D)
    scores = orphan_embs @ embeddings.T             # (M, N)  cosine scores

    n_candidates = len(slugs) - 1                  # exclude self
    top_k = min(k, n_candidates)

    edges: list[dict] = []
    for local_i, global_i in enumerate(orphan_idxs):
        row = scores[local_i].copy()
        row[global_i] = -2.0                        # exclude self

        neighbour_idxs = np.argpartition(row, -top_k)[-top_k:]

        src_slug = slugs[global_i]
        src_meta = laws_classified[src_slug]
        src_id = node_id(src_meta.get("jurabk"), src_slug, jurisdiction)

        for ni in neighbour_idxs:
            tgt_slug = slugs[int(ni)]
            tgt_meta = laws_classified[tgt_slug]
            tgt_id = node_id(tgt_meta.get("jurabk"), tgt_slug, jurisdiction)
            edges.append({
                "source": src_id,
                "target": tgt_id,
                "type": "soft",
                "weight": weight,
                "valid_from": None,
                "valid_to": None,
            })

    return edges
