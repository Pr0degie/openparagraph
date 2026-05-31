# Stage 07 — extract cross-law citations from all parsed law norms.
# Input:  build/laws_parsed/  ({slug}.json per law, from Stage 04)
# Output: build/refs_raw.json  (list of filtered citation records)
#
# Uses pebble.ProcessPool which actually kills stuck worker processes on timeout,
# unlike concurrent.futures.ProcessPoolExecutor whose timeout only stops waiting.

rule extract_refs:
    input: "build/laws_parsed"
    output: "build/refs_raw.json"
    threads: 8
    run:
        import json
        import logging
        import sys
        from concurrent.futures import TimeoutError as FutureTimeoutError
        from pathlib import Path

        from pebble import ProcessPool

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.ref_extractor import init_extractor, process_law_file

        _log = logging.getLogger("stage07")
        laws_dir = Path(input[0])
        json_files = sorted(laws_dir.glob("*.json"))
        total = len(json_files)
        _log.info("Extracting refs from %d laws (%d workers)", total, threads)

        all_refs: list[dict] = []
        done = 0

        with ProcessPool(max_workers=threads, initializer=init_extractor) as pool:
            future = pool.map(
                process_law_file,
                [str(p) for p in json_files],
                timeout=60,
            )
            it = future.result()
            for p in json_files:
                slug = p.stem
                try:
                    refs = next(it)
                    all_refs.extend(refs)
                except StopIteration:
                    break
                except FutureTimeoutError:
                    _log.warning("timeout in %s — skipped", slug)
                except Exception as exc:
                    _log.warning("error in %s: %s", slug, exc)
                done += 1
                if done % 500 == 0:
                    _log.info(
                        "processed %d / %d  (%d refs so far)", done, total, len(all_refs)
                    )

        _log.info(
            "extract_refs complete: %d citations from %d laws", len(all_refs), total
        )
        Path(output[0]).write_text(json.dumps(all_refs, ensure_ascii=False))
