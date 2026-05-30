# Stage 07 — extract cross-law citations from all parsed law norms.
# Input:  build/laws_parsed/  ({slug}.json per law, from Stage 04)
# Output: build/refs_raw.json  (list of filtered citation records)
#
# Uses ProcessPoolExecutor (not ThreadPoolExecutor) because refex is CPU-bound.
# Worker functions live in src/ref_extractor.py (must be module-level to be
# pickleable by multiprocessing).  One CitationExtractor per worker process.

rule extract_refs:
    input: "build/laws_parsed"
    output: "build/refs_raw.json"
    threads: 8
    run:
        import json
        import logging
        import sys
        from concurrent.futures import ProcessPoolExecutor, as_completed
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.ref_extractor import init_extractor, process_law_file

        _log = logging.getLogger("stage07")
        laws_dir = Path(input[0])
        json_files = sorted(laws_dir.glob("*.json"))
        total = len(json_files)
        _log.info("Extracting refs from %d laws (%d workers)", total, threads)

        all_refs: list[dict] = []
        done = 0

        with ProcessPoolExecutor(
            max_workers=threads, initializer=init_extractor
        ) as pool:
            futs = {
                pool.submit(process_law_file, str(p)): p.stem
                for p in json_files
            }
            for fut in as_completed(futs):
                try:
                    refs = fut.result()
                    all_refs.extend(refs)
                except Exception as exc:
                    _log.warning("error in %s: %s", futs[fut], exc)
                done += 1
                if done % 500 == 0:
                    _log.info(
                        "processed %d / %d  (%d refs so far)", done, total, len(all_refs)
                    )

        _log.info(
            "extract_refs complete: %d citations from %d laws", len(all_refs), total
        )
        Path(output[0]).write_text(json.dumps(all_refs, ensure_ascii=False))
