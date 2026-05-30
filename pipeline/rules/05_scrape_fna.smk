# Stage 05 — parse BMJ FNA PDF and join codes to GII law slugs.
# Input:  build/toc.json + build/slug_table.json (from Stage 02)
# Output: build/fna_map.json       — {slug: fna_code}  (used by Stage 06)
#         build/fna_pdf_entries.json — extracted PDF entries (resumable cache)
#
# The PDF itself is downloaded to build/FNA_{year}.pdf and cached on disk.
# If fna_pdf_entries.json already exists from a prior run, PDF parsing is
# skipped (saving ~75 s).

rule scrape_fna:
    input:
        toc="build/toc.json",
        slug_table="build/slug_table.json",
    output:
        fna_map="build/fna_map.json",
        entries_cache="build/fna_pdf_entries.json",
    run:
        import json
        import logging
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.fna_parser import (
            build_join_maps,
            download_fna_pdf,
            extract_entries_from_pdf,
            join_fna,
        )

        _log = logging.getLogger("stage05")

        year = config["sources"]["fna_pdf_year"]
        pdf_url = (
            "https://www.recht.bund.de/shareddocs/downloads/de/fundstellennachweise/"
            f"fna/FNA_{year}.pdf?__blob=publicationFile&v=3"
        )
        pdf_path = Path("build") / f"FNA_{year}.pdf"
        entries_path = Path(output.entries_cache)

        # ── PDF acquisition ──────────────────────────────────────────────────
        download_fna_pdf(pdf_url, pdf_path)

        # ── Entry extraction (cached) ────────────────────────────────────────
        if entries_path.exists():
            _log.info("Loading cached PDF entries from %s", entries_path)
            entries = json.loads(entries_path.read_text())
        else:
            entries = extract_entries_from_pdf(pdf_path)
            entries_path.write_text(json.dumps(entries, ensure_ascii=False))

        _log.info("%d FNA-coded entries loaded", len(entries))

        # ── Build join maps ──────────────────────────────────────────────────
        by_title, by_abbr = build_join_maps(entries)
        _log.info("Join maps: by_title=%d  by_abbr=%d", len(by_title), len(by_abbr))

        # ── Join to GII corpus ───────────────────────────────────────────────
        toc = json.loads(Path(input.toc).read_text())
        slug_table = json.loads(Path(input.slug_table).read_text())

        fna_map = join_fna(slug_table, toc, by_title, by_abbr)

        Path(output.fna_map).write_text(
            json.dumps(fna_map, indent=2, ensure_ascii=False)
        )
        _log.info("fna_map written: %d entries", len(fna_map))
