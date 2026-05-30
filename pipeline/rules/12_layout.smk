# Stage 12 — ForceAtlas2 layout on the union graph.
# Input:  build/graph_nodes.json       (Stage 11)
#         data/_global/edges.json      (Stage 11, hard + soft union)
# Output: data/_global/layout.json     {node_id: {x, y}} for every node

rule layout:
    input:
        nodes="build/graph_nodes.json",
        edges=f"{DATA}/_global/edges.json",
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
        )

        _log.info("Layout done; x range %.1f–%.1f",
                  min(v["x"] for v in positions.values()),
                  max(v["x"] for v in positions.values()))

        layout_path = Path(output.layout)
        layout_path.parent.mkdir(parents=True, exist_ok=True)
        layout_path.write_text(
            json.dumps(positions, indent=2, ensure_ascii=False)
        )
