# Stage 11 — Assemble graph nodes + union of hard + soft edges.
# Input:  build/laws_classified.json   (Stage 06)
#         build/edges_structural.json  (Stage 08 — explicit §-reference edges)
#         build/edges_soft.json        (Stage 10 — embedding neighbour edges)
# Output: build/graph_nodes.json       (for Stage 12 layout + Stage 13 color)
#         data/_global/edges.json      (union edge list for frontend + layout)

rule build_graph:
    input:
        classified="build/laws_classified.json",
        edges_struct="build/edges_structural.json",
        edges_soft="build/edges_soft.json",
    output:
        nodes="build/graph_nodes.json",
        edges=f"{DATA}/_global/edges.json",
    run:
        import json
        import logging
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.graph_builder import build_graph

        _log = logging.getLogger("stage11")

        classified  = json.loads(Path(input.classified).read_text())
        edges_hard  = json.loads(Path(input.edges_struct).read_text())
        edges_soft  = json.loads(Path(input.edges_soft).read_text())
        edges_raw   = edges_hard + edges_soft

        _log.info(
            "Loaded %d laws, %d hard edges, %d soft edges",
            len(classified), len(edges_hard), len(edges_soft),
        )

        jurisdiction = config["jurisdiction"]
        nodes, edges = build_graph(classified, edges_raw, jurisdiction)

        _log.info(
            "Built %d nodes; degree range %d–%d",
            len(nodes),
            min(n["degree"] for n in nodes) if nodes else 0,
            max(n["degree"] for n in nodes) if nodes else 0,
        )

        Path(output.nodes).write_text(
            json.dumps(nodes, indent=2, ensure_ascii=False)
        )

        edges_path = Path(output.edges)
        edges_path.parent.mkdir(parents=True, exist_ok=True)
        edges_path.write_text(
            json.dumps(edges, indent=2, ensure_ascii=False)
        )
