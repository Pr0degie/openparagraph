# Stage 15 — search index documents for the frontend.
# Input:  data/<jur>/nodes.json        (Stage 13)
#         build/laws_classified.json   (Stage 06; supplies opening_text)
# Output: data/_global/search-index.json   [{id, jurabk, title, desc}, ...]

rule search_index:
    input:
        nodes=f"{DATA}/{JUR}/nodes.json",
        classified="build/laws_classified.json",
    output:
        index=f"{DATA}/_global/search-index.json",
    run:
        import json
        import logging
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.search_index import build_search_index

        _log = logging.getLogger("stage15")

        nodes = json.loads(Path(input.nodes).read_text())
        classified = json.loads(Path(input.classified).read_text())

        docs = build_search_index(nodes, classified, config["jurisdiction"])
        _log.info("Search index: %d documents", len(docs))

        out = Path(output.index)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(docs, ensure_ascii=False))
