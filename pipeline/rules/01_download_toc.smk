# Stage 01 — download and parse the GII table of contents.
# Input:  live HTTP (https://www.gesetze-im-internet.de/gii-toc.xml)
# Output: build/toc.json  {slug: {zip_url, title}}

rule download_toc:
    output: "build/toc.json"
    run:
        import json
        import logging
        import sys
        from pathlib import Path

        import requests

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.downloader import HEADERS
        from src.toc_parser import parse_toc_xml

        _log = logging.getLogger("stage01")
        url = config["sources"]["gii_toc"]
        _log.info("fetching TOC from %s", url)

        r = requests.get(url, timeout=30, headers=HEADERS)
        r.raise_for_status()

        toc = parse_toc_xml(r.content)
        _log.info("TOC: %d laws", len(toc))

        Path(output[0]).parent.mkdir(parents=True, exist_ok=True)
        Path(output[0]).write_text(json.dumps(toc, indent=2, ensure_ascii=False))
