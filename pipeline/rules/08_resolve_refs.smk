# Stage 08 — resolve raw citations to graph edges + frontend resolver.
# Input:  build/refs_raw.json     (filtered citation records, Stage 07)
#         build/slug_table.json   (jurabk + langue per slug, Stage 02)
#         build/toc.json          (common law titles, Stage 01)
# Output: build/edges_structural.json          (deduplicated explicit edges)
#         data/_global/reference-resolver.json  (span_text → node_id map)

rule resolve_refs:
    input:
        refs="build/refs_raw.json",
        slug_table="build/slug_table.json",
        toc="build/toc.json",
    output:
        edges_struct="build/edges_structural.json",
        resolver=f"{DATA}/_global/reference-resolver.json",
    run:
        import json
        import logging
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.ref_resolver import build_edges_and_resolver, build_jurabk_index

        _log = logging.getLogger("stage08")

        refs_raw   = json.loads(Path(input.refs).read_text())
        slug_table = json.loads(Path(input.slug_table).read_text())
        toc        = json.loads(Path(input.toc).read_text())

        _log.info(
            "Loaded %d citations, %d slug_table entries, %d toc entries",
            len(refs_raw), len(slug_table), len(toc),
        )

        index = build_jurabk_index(slug_table, toc)
        _log.info("jurabk_index: %d keys", len(index))

        jurisdiction = config["jurisdiction"]
        edges, resolver, stats = build_edges_and_resolver(
            refs_raw, index, slug_table, jurisdiction
        )

        _log.info(
            "Resolution: %d / %d (%.1f%%) → %d unique edges, %d resolver entries",
            stats["resolved"],
            stats["resolved"] + stats["unresolved"],
            stats["coverage_pct"],
            stats["unique_edges"],
            stats["resolver_entries"],
        )

        Path(output.edges_struct).write_text(
            json.dumps(edges, indent=2, ensure_ascii=False)
        )

        resolver_path = Path(output.resolver)
        resolver_path.parent.mkdir(parents=True, exist_ok=True)
        resolver_path.write_text(
            json.dumps(resolver, indent=2, ensure_ascii=False)
        )
