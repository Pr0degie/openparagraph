# Stage 12 — ForceAtlas2 layout on the union graph.
# Input:  build/graph_nodes.json       (Stage 11)
#         data/_global/edges.json      (Stage 11, hard + soft union)
#         build/embeddings.npy         (Stage 09; only used when dimensions=3)
#         build/laws_classified.json   (Stage 06; slug→node-id map for the z axis)
# Output: data/_global/layout.json     {node_id: {x, y[, z]}} for every node

rule layout:
    input:
        nodes="build/graph_nodes.json",
        edges=f"{DATA}/_global/edges.json",
        embeddings="build/embeddings.npy",
        classified="build/laws_classified.json",
    output:
        layout=f"{DATA}/_global/layout.json",
    run:
        import json
        import logging
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.layout_builder import run_layout

        _log = logging.getLogger("stage12")

        nodes = json.loads(Path(input.nodes).read_text())
        edges = json.loads(Path(input.edges).read_text())

        _log.info("Running FA2 on %d nodes, %d edges", len(nodes), len(edges))

        cfg = config["layout"]
        positions = run_layout(
            nodes=nodes,
            edges=edges,
            seed=cfg["seed"],
            iterations=cfg["iterations"],
            scaling_ratio=cfg["scaling_ratio"],
            gravity=cfg["gravity"],
            strong_gravity=cfg["strong_gravity"],
            barnes_hut_theta=cfg["barnes_hut_theta"],
            outbound_attraction_distribution=cfg["outbound_attraction_distribution"],
            adjust_sizes=cfg.get("adjust_sizes", False),
        )

        _log.info("Layout done; x range %.1f–%.1f",
                  min(v["x"] for v in positions.values()),
                  max(v["x"] for v in positions.values()))

        # Optional semantic z-axis for the 3D / 2.5D frontend views.
        if cfg.get("dimensions", 2) == 3 and cfg.get("z_source") == "pca-embeddings":
            import numpy as np
            from src.layout_builder import pca_z
            from src.graph_builder import node_id

            classified = json.loads(Path(input.classified).read_text())
            emb = np.load(input.embeddings)
            sorted_slugs = sorted(classified.keys())   # matches embeddings row order
            if emb.shape[0] != len(sorted_slugs):
                raise ValueError(
                    f"embeddings rows ({emb.shape[0]}) != slugs ({len(sorted_slugs)})"
                )
            z = pca_z(emb, cfg.get("z_component", 0)) * cfg.get("z_scale", 6000.0)
            jur = config["jurisdiction"]
            slug_to_nid = {
                s: node_id(m.get("jurabk"), s, jur) for s, m in classified.items()
            }
            z_by_nid = {slug_to_nid[s]: float(z[i]) for i, s in enumerate(sorted_slugs)}
            for nid, p in positions.items():
                p["z"] = z_by_nid.get(nid, 0.0)
            zs = [p["z"] for p in positions.values()]
            _log.info("Added z (PCA comp %d); range %.1f–%.1f",
                      cfg.get("z_component", 0), min(zs), max(zs))

        layout_path = Path(output.layout)
        layout_path.parent.mkdir(parents=True, exist_ok=True)
        layout_path.write_text(
            json.dumps(positions, indent=2, ensure_ascii=False)
        )
