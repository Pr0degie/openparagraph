# Stage 04 — parse all law XMLs into structured JSON + base HTML.
# Input:  build/laws_xml/   ({slug}.xml per law, from Stage 02)
# Output: build/laws_parsed/ ({slug}.json + {slug}.html per law)
#
# Resumable: slugs that already have both output files are skipped.

rule parse_laws:
    input: "build/laws_xml"
    output: directory("build/laws_parsed")
    threads: 8
    run:
        import json
        import logging
        import sys
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.gii_parser import parse_law
        from src.law_serializer import law_to_dict, law_to_html

        _log = logging.getLogger("stage04")
        xml_dir = Path(input[0])
        out_dir = Path(output[0])
        out_dir.mkdir(parents=True, exist_ok=True)

        xml_files = sorted(xml_dir.glob("*.xml"))
        _log.info("Found %d XML files to parse", len(xml_files))

        def process_one(xml_path: Path) -> None:
            slug = xml_path.stem
            json_out = out_dir / f"{slug}.json"
            html_out = out_dir / f"{slug}.html"
            if json_out.exists() and html_out.exists():
                return

            xml_bytes = xml_path.read_bytes()
            law = parse_law(xml_bytes, source=slug)

            json_out.write_text(
                json.dumps(law_to_dict(slug, law), ensure_ascii=False)
            )
            html_out.write_text(law_to_html(slug, law))

        total = len(xml_files)
        done = 0
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futs = {pool.submit(process_one, p): p.stem for p in xml_files}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    _log.warning("parse error for %s: %s", futs[fut], exc)
                done += 1
                if done % 500 == 0:
                    _log.info("parsed %d / %d", done, total)

        _log.info("parse_laws complete: %d laws", total)
