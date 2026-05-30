# Stage 02 — parallel download of all ~6000 law xml.zips.
# Input:  build/toc.json
# Output: build/laws_xml/   — one {slug}.xml per law (used by Stage 04)
#         build/slug_table.json — {slug: {jurabk, langue, ausfertigung_datum}}
#                                  (used by Stage 08 resolver)
#
# Resumable: already-present {slug}.xml files are skipped.  Interrupt and
# re-run; only missing laws are fetched.

rule download_laws:
    input: "build/toc.json"
    output:
        laws_xml=directory("build/laws_xml"),
        slug_table="build/slug_table.json",
    threads: 8
    run:
        import json
        import logging
        import sys
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from pathlib import Path

        import requests

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.downloader import HEADERS, fetch_law_xml
        from src.gii_parser import parse_law

        _log = logging.getLogger("stage02")
        toc: dict = json.loads(Path(input[0]).read_text())
        xml_dir = Path(output.laws_xml)
        xml_dir.mkdir(parents=True, exist_ok=True)

        # Per-thread HTTP session (requests.Session is not thread-safe for writes).
        _tls = threading.local()

        def _session() -> requests.Session:
            if not hasattr(_tls, "s"):
                _tls.s = requests.Session()
                _tls.s.headers.update(HEADERS)
            return _tls.s

        slug_table: dict = {}
        lock = threading.Lock()

        def process_one(item: tuple) -> None:
            slug, info = item
            xml_path = xml_dir / f"{slug}.xml"

            if xml_path.exists() and xml_path.stat().st_size > 0:
                xml_bytes = xml_path.read_bytes()
            else:
                xml_bytes = fetch_law_xml(info["zip_url"], slug, _session())
                if xml_bytes is None:
                    return
                xml_path.write_bytes(xml_bytes)

            law = parse_law(xml_bytes, source=slug)
            # Only add to slug_table if we got at least one identifying field.
            if law.jurabk or law.langue:
                with lock:
                    slug_table[slug] = {
                        "jurabk": law.jurabk,
                        "langue": law.langue,
                        "ausfertigung_datum": law.ausfertigung_datum,
                    }

        total = len(toc)
        done = 0
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futs = {pool.submit(process_one, item): item[0] for item in toc.items()}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    _log.warning("unhandled error for %s: %s", futs[fut], exc)
                done += 1
                if done % 500 == 0:
                    _log.info("processed %d / %d", done, total)

        _log.info("slug_table: %d / %d laws have jurabk or langue", len(slug_table), total)
        Path(output.slug_table).write_text(
            json.dumps(slug_table, indent=2, ensure_ascii=False)
        )
