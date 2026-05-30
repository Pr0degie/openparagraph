# Stage 06 — attach FNA classification to all parsed laws.
# Input:  build/laws_parsed/  ({slug}.json per law, from Stage 04)
#         build/fna_map.json  ({slug: fna_code}, from Stage 05)
# Output: build/laws_classified.json  ({slug: compact classified record})
#
# Compact = metadata + opening_text only; full norm lists stay in laws_parsed/.
# Laws with no FNA match get fna_code=null, main_group=null (→ embedding fallback).

rule classify:
    input:
        laws="build/laws_parsed",
        fna="build/fna_map.json",
    output: "build/laws_classified.json"
    threads: 8
    run:
        import json
        import logging
        import sys
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.classifier import classify_law

        _log = logging.getLogger("stage06")

        fna_map: dict = json.loads(Path(input.fna).read_text())
        laws_dir = Path(input.laws)
        json_files = sorted(laws_dir.glob("*.json"))
        _log.info("Classifying %d laws", len(json_files))

        classified: dict = {}
        lock = __import__("threading").Lock()

        def process_one(json_path: Path) -> None:
            slug = json_path.stem
            law_dict = json.loads(json_path.read_text())
            fna_code = fna_map.get(slug)
            record = classify_law(slug, law_dict, fna_code)
            with lock:
                classified[slug] = record

        total = len(json_files)
        done = 0
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futs = {pool.submit(process_one, p): p.stem for p in json_files}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    _log.warning("error classifying %s: %s", futs[fut], exc)
                done += 1
                if done % 1000 == 0:
                    _log.info("classified %d / %d", done, total)

        matched = sum(1 for r in classified.values() if r["fna_code"] is not None)
        _log.info(
            "Classification complete: %d / %d with FNA code (%.1f%%)",
            matched, total, 100 * matched / total if total else 0,
        )

        Path(output[0]).write_text(
            json.dumps(classified, indent=2, ensure_ascii=False)
        )
