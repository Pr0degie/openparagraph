#!/usr/bin/env python3
"""
Spike C — reference extraction & resolver prototype.

Tests `legal-reference-extraction` (module name: refex) on 5 diverse laws,
measures citation recall, and prototypes the reference-resolver lookup.

Run from /pipeline:
    uv run python spikes/spike_c_references.py

Outputs:
    data/spike_c/results.json
    data/spike_c/resolver_proto.json
    data/spike_c/summary.txt
"""
import io
import json
import logging
import re
import sys
import zipfile
from pathlib import Path

import requests
from lxml import etree
from refex.orchestrator import CitationExtractor

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from gii_parser import parse_law

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

GII_BASE = "https://www.gesetze-im-internet.de"
GII_TOC = f"{GII_BASE}/gii-toc.xml"
OUT_DIR = Path(__file__).parent.parent.parent / "data" / "spike_c"

# 5 diverse laws: large civil code, criminal code, constitution (Art.),
# a regulation, a short employment law
TARGET_SLUGS = ["bgb", "stgb", "gg", "bimschg", "burlg"]

HEADERS = {"User-Agent": "openparagraph-spike/0 research-prototype"}

_tag_re = re.compile(r"<[^>]+>")


def strip_tags(html: str) -> str:
    """Remove XML/HTML tags, collapse whitespace."""
    text = _tag_re.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


def fetch_toc() -> dict[str, dict]:
    """Return {slug: {title, zip_url}} for all laws in the GII TOC."""
    log.info("Fetching TOC …")
    r = requests.get(GII_TOC, timeout=60, headers=HEADERS)
    r.raise_for_status()
    root = etree.fromstring(r.content)
    items: dict[str, dict] = {}
    for item in root.findall(".//item"):
        link_el = item.find("link")
        title_el = item.find("title")
        if link_el is None or not link_el.text:
            continue
        # TOC links point directly to xml.zip, e.g.:
        # http://www.gesetze-im-internet.de/bgb/xml.zip → slug = bgb
        parts = link_el.text.rstrip("/").split("/")
        slug = parts[-2] if len(parts) >= 2 else parts[-1]
        items[slug] = {
            "title": title_el.text if title_el is not None else "",
            "zip_url": link_el.text,
        }
    log.info("TOC: %d laws", len(items))
    return items


def download_law(slug: str) -> bytes | None:
    """Download xml.zip for a GII slug, return raw zip bytes."""
    url = f"{GII_BASE}/{slug}/xml.zip"
    log.info("Downloading %s …", url)
    try:
        r = requests.get(url, timeout=60, headers=HEADERS)
        r.raise_for_status()
        return r.content
    except Exception as exc:
        log.warning("  failed: %s", exc)
        return None


def extract_plain_texts(zip_bytes: bytes, slug: str) -> tuple[object, list[dict]]:
    """Parse zip → Law; return (law, [{enbez, titel, text}])."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
        xml_bytes = zf.read(xml_names[0])
    law = parse_law(xml_bytes, source=slug)
    norms = []
    for n in law.content_norms:
        plain = strip_tags(n.text_xml) if n.text_xml else ""
        norms.append({"enbez": n.enbez, "titel": n.titel, "text": plain})
    return law, norms


def run_extraction(norms: list[dict]) -> list[dict]:
    """Run refex over all norms, return list of citation dicts."""
    extractor = CitationExtractor()
    citations: list[dict] = []
    for norm in norms:
        if not norm["text"]:
            continue
        result = extractor.extract(norm["text"])
        for c in result.citations:
            # Only law citations (not case references)
            if not hasattr(c, "book"):
                continue
            citations.append({
                "enbez": norm["enbez"],
                "span_text": c.span.text,
                "book": c.book,
                "number": c.number,
                "unit": c.unit,
                "confidence": c.confidence,
                "source": c.source,
            })
    return citations


def build_resolver(toc: dict[str, str]) -> dict[str, str]:
    """Build {normalized_name → slug} resolver with three lookup layers.

    Layer 1 — slug identity: refex short codes (bgb, stgb, gg) → slug directly.
    Layer 2 — exact title: "Beurkundungsgesetz" in TOC title → beurkg.
    Layer 3 — new/old spelling: ß↔ss normalization (strafprozeßordnung → stpo).
    For ambiguous titles (same keyword in many laws) we keep the earliest/shortest
    slug as the canonical one, since derivative Verordnungen have longer slugs.

    `toc` maps slug → TOC entry (fetched separately with titles).
    """
    resolver: dict[str, str] = {}

    def _key(s: str) -> str:
        return re.sub(r"\s+", "", s.lower())

    def _alt(s: str) -> str:
        """ß↔ss alternative key."""
        return s.replace("ß", "ss") if "ß" in s else s.replace("ss", "ß")

    def _register(key: str, slug: str) -> None:
        # Prefer shorter slugs (canonical law vs. derivative) on collision
        existing = resolver.get(key)
        if existing is None or len(slug) < len(existing):
            resolver[key] = slug

    # Layer 1: slug → slug (covers short refex codes)
    for slug in toc:
        _register(slug.lower(), slug)

    # Layer 2 & 3: title-based lookup
    for slug, entry in toc.items():
        title = entry.get("title", "")
        if not title:
            continue
        key = _key(title)
        _register(key, slug)
        alt = _alt(key)
        if alt != key:
            _register(alt, slug)
        # Also map the last parenthesized shortname, e.g. "... (BUrlG)"
        m = re.search(r"\(([^)]{3,})\)\s*$", title)
        if m:
            _register(_key(m.group(1)), slug)
            alt2 = _alt(_key(m.group(1)))
            if alt2 != _key(m.group(1)):
                _register(alt2, slug)

    log.info("Resolver: %d entries", len(resolver))
    return resolver


def assess_resolution(citations: list[dict], resolver: dict[str, str]) -> dict:
    """Count how many citations resolve to a known slug."""
    total = len(citations)
    resolved = 0
    unresolved_books: dict[str, int] = {}
    for c in citations:
        book = (c["book"] or "").lower()
        if book in resolver:
            resolved += 1
        else:
            unresolved_books[book] = unresolved_books.get(book, 0) + 1
    top_unresolved = sorted(unresolved_books.items(), key=lambda x: -x[1])[:20]
    return {
        "total": total,
        "resolved": resolved,
        "resolution_rate": round(resolved / total, 3) if total else 0,
        "top_unresolved_books": top_unresolved,
    }


def sample_manual_check(citations: list[dict], n: int = 15) -> list[dict]:
    """Return a stratified sample for manual recall check."""
    step = max(1, len(citations) // n)
    return citations[::step][:n]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    toc = fetch_toc()
    resolver = build_resolver(toc)

    all_results: list[dict] = []
    all_citations: list[dict] = []

    for slug in TARGET_SLUGS:
        zip_bytes = download_law(slug)
        if not zip_bytes:
            all_results.append({"slug": slug, "error": "download failed"})
            continue

        law, norms = extract_plain_texts(zip_bytes, slug)
        log.info("  %s: jurabk=%s, norms=%d", slug, law.jurabk, len(norms))

        citations = run_extraction(norms)
        log.info("  %s: %d citations extracted", slug, len(citations))

        resolution = assess_resolution(citations, resolver)
        log.info(
            "  %s: resolved %d/%d (%.1f%%)",
            slug, resolution["resolved"], resolution["total"],
            resolution["resolution_rate"] * 100,
        )

        result = {
            "slug": slug,
            "jurabk": law.jurabk,
            "langue": law.langue,
            "norm_count": len(norms),
            "citation_count": len(citations),
            "resolution": resolution,
            "parse_warnings": law.parse_warnings,
            # Sample 10 citations for inspection
            "sample_citations": citations[:10],
        }
        all_results.append(result)
        for c in citations:
            c["law_slug"] = slug
        all_citations.extend(citations)

    # Aggregate across all 5 laws
    total_norms = sum(r.get("norm_count", 0) for r in all_results if "error" not in r)
    total_cit = len(all_citations)
    agg_resolution = assess_resolution(all_citations, resolver)

    summary_lines = [
        "=== Spike C — Reference Extraction Summary ===",
        "",
        f"Laws tested: {len(TARGET_SLUGS)}  |  Norms with text: {total_norms}",
        f"Total citations: {total_cit}  |  Resolved: {agg_resolution['resolved']}  |  Rate: {agg_resolution['resolution_rate']*100:.1f}%",
        "",
        "Per-law breakdown:",
    ]
    for r in all_results:
        if "error" in r:
            summary_lines.append(f"  {r['slug']}: ERROR — {r['error']}")
            continue
        res = r["resolution"]
        summary_lines.append(
            f"  {r['jurabk']:12s} ({r['slug']:10s}): "
            f"{r['norm_count']:4d} norms, "
            f"{r['citation_count']:5d} citations, "
            f"resolved {res['resolved']}/{res['total']} ({res['resolution_rate']*100:.1f}%)"
        )
    summary_lines += [
        "",
        "Top unresolved book codes (aggregate):",
    ]
    for book, count in agg_resolution["top_unresolved_books"]:
        summary_lines.append(f"  {book:20s}: {count}")
    summary_lines += [
        "",
        "Manual recall sample (first 15 citations across all laws):",
    ]
    for c in sample_manual_check(all_citations, 15):
        summary_lines.append(
            f"  [{c['law_slug']}] {c['enbez']:8s} | {c['span_text']:30s} | book={c['book']} num={c['number']}"
        )

    summary = "\n".join(summary_lines)
    print("\n" + summary)

    # Save outputs
    (OUT_DIR / "results.json").write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False)
    )
    (OUT_DIR / "resolver_proto.json").write_text(
        json.dumps(resolver, indent=2, ensure_ascii=False)
    )
    (OUT_DIR / "summary.txt").write_text(summary)
    log.info("Results written to %s", OUT_DIR)


if __name__ == "__main__":
    main()
