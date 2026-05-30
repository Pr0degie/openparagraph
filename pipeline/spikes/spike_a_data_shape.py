#!/usr/bin/env python3
"""
Spike A — GII data shape confirmation.

Downloads gii-toc.xml, fetches 10 representative law XML.zips,
parses them with lxml, and confirms which metadata fields are
reliably present across the corpus.

Output: ../../data/spike_a/results.json
        ../../data/spike_a/summary.txt
"""

from __future__ import annotations

import io
import json
import logging
import sys
import zipfile
from pathlib import Path

import requests
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.gii_parser import parse_law, Law

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

GII_TOC = "https://www.gesetze-im-internet.de/gii-toc.xml"
SAMPLE_SIZE = 10
OUT_DIR = Path(__file__).parent.parent.parent / "data" / "spike_a"

HEADERS = {
    "User-Agent": "openparagraph-spike-a/0.1 (research; github.com/openparagraph)"
}


def fetch_toc(url: str) -> list[dict]:
    """Download and parse gii-toc.xml. Returns list of {title, link} dicts."""
    log.info("Fetching TOC from %s", url)
    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()

    # Discover the TOC element name empirically
    root = etree.fromstring(r.content)
    log.info("TOC root tag: <%s>", root.tag)

    items = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is not None and link_el is not None:
            items.append({"title": title_el.text, "link": link_el.text})

    log.info("TOC contains %d laws", len(items))
    return items


def law_xml_zip_url(html_link: str) -> str:
    """Convert law index URL to its xml.zip URL.

    e.g. https://www.gesetze-im-internet.de/bgb/index.html
    ->   https://www.gesetze-im-internet.de/bgb/xml.zip
    """
    base = html_link.rsplit("/", 1)[0]
    return base + "/xml.zip"


def download_and_parse(zip_url: str) -> dict:
    """Download xml.zip, parse the law XML, return structured result dict."""
    log.info("Downloading %s", zip_url)
    r = requests.get(zip_url, timeout=60, headers=HEADERS)
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
        if not xml_names:
            return {"error": "no xml in zip", "source": zip_url}
        xml_bytes = zf.read(xml_names[0])
        log.info("  zip contains: %s", zf.namelist())

    law: Law = parse_law(xml_bytes, source=zip_url)

    return {
        "source": zip_url,
        "jurabk": law.jurabk,
        "amtabk": law.amtabk,
        "ausfertigung_datum": law.ausfertigung_datum,
        "langue": law.langue,
        "norm_count": law.norm_count,
        "content_norm_count": len(law.content_norms),
        # Sample the first few §§ to see enbez / titel coverage
        "norms_sample": [
            {"enbez": n.enbez, "titel": n.titel, "has_text": n.text_xml is not None}
            for n in law.content_norms[:5]
        ],
        "parse_warnings": law.parse_warnings,
        "norms_have_enbez": any(n.enbez for n in law.content_norms),
        "norms_have_titel": any(n.titel for n in law.content_norms),
        "norms_have_text": any(n.text_xml for n in law.content_norms),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = fetch_toc(GII_TOC)
    if not items:
        log.error("TOC returned 0 items — check URL and format")
        sys.exit(1)

    # Sample spread across the alphabet to get varied law types
    step = max(1, len(items) // SAMPLE_SIZE)
    sample = items[::step][:SAMPLE_SIZE]
    log.info("Sampling %d laws (step=%d out of %d total)", len(sample), step, len(items))

    results = []
    for item in sample:
        zip_url = law_xml_zip_url(item["link"])
        try:
            parsed = download_and_parse(zip_url)
            parsed["toc_title"] = item["title"]
            results.append(parsed)
            log.info(
                "  OK  %s | norms=%d | jurabk=%s | datum=%s",
                item["title"][:40],
                parsed.get("norm_count", 0),
                parsed.get("jurabk"),
                parsed.get("ausfertigung_datum"),
            )
        except Exception as exc:
            log.warning("FAIL %s: %s", zip_url, exc)
            results.append({
                "toc_title": item["title"],
                "source": zip_url,
                "error": str(exc),
            })

    # Write full JSON
    out_json = OUT_DIR / "results.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    log.info("Full results written to %s", out_json)

    # Write human-readable summary
    fields = ["jurabk", "amtabk", "ausfertigung_datum", "langue"]
    ok = [r for r in results if "error" not in r]
    n = len(results)
    lines = [
        "=== Spike A — Data Shape Summary ===",
        f"Laws sampled: {n}  |  Successful: {len(ok)}  |  Failed: {n - len(ok)}",
        "",
        "Field presence (of successful parses):",
    ]
    for f in fields:
        present = sum(1 for r in ok if r.get(f) is not None)
        pct = 100 * present // len(ok) if ok else 0
        lines.append(f"  {f:<25} {present}/{len(ok)}  ({pct}%)")

    lines += [
        "",
        "Norm counts:",
        "  " + "  ".join(f"{r.get('jurabk','?')}={r.get('norm_count','err')}" for r in ok),
        "",
        "Sample §§ structure (first 3 laws):",
    ]
    for r in ok[:3]:
        lines.append(f"  {r.get('jurabk','?')}: enbez={r['norms_have_enbez']}, "
                     f"titel={r['norms_have_titel']}, text={r['norms_have_text']}")

    summary = "\n".join(lines)
    (OUT_DIR / "summary.txt").write_text(summary)
    print("\n" + summary)


if __name__ == "__main__":
    main()
