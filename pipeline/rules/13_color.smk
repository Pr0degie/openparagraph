# Stage 13 — Three-rule FNA color logic + merge layout coordinates.
# Input:  build/graph_nodes.json         (Stage 11 — nodes with degree/size)
#         data/_global/layout.json       (Stage 12 — {node_id: {x, y}})
#         data/_global/edges.json        (Stage 11 — hard + soft union)
# Output: data/<jur>/nodes.json          (final node list: x, y, color, meta_cluster)
#         data/_global/meta-taxonomy.json (FNA group → cluster + color, for frontend)

rule color:
    input:
        nodes="build/graph_nodes.json",
        layout=f"{DATA}/_global/layout.json",
        edges=f"{DATA}/_global/edges.json",
    output:
        nodes=f"{DATA}/{JUR}/nodes.json",
        taxonomy=f"{DATA}/_global/meta-taxonomy.json",
    run:
        import json
        import logging
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.color_builder import assign_colors, build_meta_taxonomy, merge_layout

        _log = logging.getLogger("stage13")

        nodes  = json.loads(Path(input.nodes).read_text())
        layout = json.loads(Path(input.layout).read_text())
        edges  = json.loads(Path(input.edges).read_text())

        _log.info("Loaded %d nodes, %d layout entries, %d edges", len(nodes), len(layout), len(edges))

        nodes = merge_layout(nodes, layout)
        nodes = assign_colors(nodes, edges)

        classified = sum(1 for n in nodes if n["meta_cluster"] != "unclassified")
        _log.info(
            "Colored %d nodes: %d classified, %d orphan",
            len(nodes), classified, len(nodes) - classified,
        )

        nodes_path = Path(output.nodes)
        nodes_path.parent.mkdir(parents=True, exist_ok=True)
        nodes_path.write_text(json.dumps(nodes, indent=2, ensure_ascii=False))

        taxonomy_path = Path(output.taxonomy)
        taxonomy_path.parent.mkdir(parents=True, exist_ok=True)
        taxonomy_path.write_text(
            json.dumps(build_meta_taxonomy(), indent=2, ensure_ascii=False)
        )
