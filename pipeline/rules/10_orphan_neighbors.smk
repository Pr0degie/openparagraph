# Stage 10 — Soft edges from embedding neighbours for orphan laws.
# Input:  build/embeddings.npy          (Stage 09, rows = sorted slugs)
#         build/laws_classified.json    (Stage 06, for slug list + jurabk)
# Output: build/edges_soft.json         (orphan→neighbour soft edges, weight ≈ 0.1)

rule orphan_neighbors:
    input:
        embeddings="build/embeddings.npy",
        classified="build/laws_classified.json",
    output:
        soft="build/edges_soft.json",
    run:
        import json
        import logging
        import sys
        import numpy as np
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.embedder import texts_for_embedding
        from src.orphan_neighbors import orphan_indices, compute_soft_edges

        _log = logging.getLogger("stage10")

        classified = json.loads(Path(input.classified).read_text())
        emb = np.load(input.embeddings)

        slugs, _ = texts_for_embedding(classified)
        o_idxs = orphan_indices(classified, slugs)

        _log.info(
            "%d orphan laws (no FNA) out of %d total",
            len(o_idxs), len(slugs),
        )

        k         = config["orphan_neighbors"]["k"]
        weight    = config["orphan_neighbors"]["soft_edge_weight"]
        jur       = config["jurisdiction"]

        soft_edges = compute_soft_edges(
            slugs, emb, classified, o_idxs, k=k, weight=weight, jurisdiction=jur
        )

        _log.info("Emitted %d soft edges (%d orphans × up to %d each)", len(soft_edges), len(o_idxs), k)

        Path(output.soft).write_text(
            json.dumps(soft_edges, indent=2, ensure_ascii=False)
        )
