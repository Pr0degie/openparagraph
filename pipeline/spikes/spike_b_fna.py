#!/usr/bin/env python3
"""
Spike B — FNA acquisition, PRIMARY path: parse the BMJ annual FNA PDF.

This is the single most strategic decision in the project: how do we attach an
official FNA Sachgebiet code (→ main group 1..9 → base hue) to each GII law?

Two sources were evaluated (see docs/spike_b.md + ADR 002):

  1. buzer.de FNA tree (HTML)  — clean structure, BUT an aggressive behavioural
     anti-bot blocks unattended crawling ("use gateway to start" / connection
     refusal that persists). Prototyped separately in spike_b_buzer.py.
  2. BMJ FNA annual PDF (recht.bund.de) — THIS FILE. A single authoritative
     download, no rate-limit risk, ideal for a reproducible pipeline. The cost
     is real PDF-parsing pain (two-column layout, hyphenation, glyph artifacts,
     varied citation formats, 1–4 digit code prefixes).

Result: the PDF is the robust acquisition path. A spike-level parser reaches
~51 % exact-title coverage of the 6 123-law corpus (ceiling ~62 % for the 2023
edition; ~60 % of the remaining misses are present in the PDF and recoverable
with fuzzy joining + better entry segmentation). Recommendation: PDF-primary,
buzer as best-effort enrichment, embedding-gravitation for the tail.

PDF entry shape (after column-aware text extraction):

    400-2 Bürgerliches Gesetzbuch (BGB)
    vom 18. 8. 1896 ...

i.e.  <FNA code>  <full title> (<abbr>)  vom <DD. MM. YYYY> <citation>

Outputs:
  data/spike_b/FNA_2023.pdf            — cached source (gitignored; large)
  data/spike_b/fna_pdf_entries.json    — code → extracted title block (cache)
  data/spike_b/fna_map.json            — GII law → FNA code (the deliverable)
  data/spike_b/results.json            — coverage stats
  data/spike_b/summary.txt             — human-readable summary

Run:  uv run python spikes/spike_b_fna.py
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path

import requests
from lxml import etree

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("spike_b")

# Latest annual edition available at run time. The URL pattern is stable:
# https://www.recht.bund.de/shareddocs/downloads/de/fundstellennachweise/fna/FNA_<year>.pdf
FNA_YEAR = 2023
FNA_PDF_URL = (
    "https://www.recht.bund.de/shareddocs/downloads/de/fundstellennachweise/"
    f"fna/FNA_{FNA_YEAR}.pdf?__blob=publicationFile&v=3"
)
GII_TOC = "https://www.gesetze-im-internet.de/gii-toc.xml"

OUT_DIR = Path(__file__).parent.parent.parent / "data" / "spike_b"
PDF_PATH = OUT_DIR / f"FNA_{FNA_YEAR}.pdf"
ENTRIES_CACHE = OUT_DIR / "fna_pdf_entries.json"

HEADERS = {"User-Agent": "openparagraph-spike-b/0.1 (research; github.com/openparagraph)"}

# A law entry begins with an FNA code at the start of a line. Codes are
# <1–4 digit Sachgebiet>-<serial>, optionally a second "-N" segment
# (e.g. 100-1, 51-1, 2120-3, 860-4-1). The 1–4 digit range matters: an early
# version of this parser used \d{3,4} and silently dropped every 2-digit-prefix
# code — e.g. all of main group 5 (Verteidigung: 51-1 Soldatengesetz).
CODE_RE = re.compile(r"(?m)^(\d{1,4}-\d+(?:-\d+)?)\s+(.*?)(?=^\d{1,4}-\d+(?:-\d+)?\s|\Z)", re.S)
# The Fundstelle (citation) anchors the END of the title. It is a fully numeric
# date; a spelled-out month ("vom 23. November 1964") is part of a treaty title,
# not the citation, so anchoring on the numeric form avoids truncating those.
CITE_RE = re.compile(r"vom\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{4}")


# ── PDF acquisition + column-aware extraction ───────────────────────────────
def ensure_pdf() -> None:
    if PDF_PATH.exists():
        log.info("PDF already cached: %s (%d bytes)", PDF_PATH, PDF_PATH.stat().st_size)
        return
    log.info("Downloading FNA %d PDF …", FNA_YEAR)
    r = requests.get(FNA_PDF_URL, timeout=120, headers=HEADERS)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise RuntimeError("download is not a PDF (got %r…)" % r.content[:20])
    PDF_PATH.write_bytes(r.content)
    log.info("Saved %s (%d bytes)", PDF_PATH, len(r.content))


def _column_text(page) -> str:
    """Extract a two-column FNA page in correct reading order.

    The FNA is laid out in two columns. A naive extract_text() either loses one
    column (pypdf) or interleaves them (pdfplumber). Cropping each half and
    concatenating left-then-right linearises it cleanly. Inter-word spaces are
    sometimes dropped — harmless, because the join key strips all separators.
    """
    w, h = page.width, page.height
    mid = w / 2
    left = page.crop((0, 0, mid, h)).extract_text() or ""
    right = page.crop((mid, 0, w, h)).extract_text() or ""
    return left + "\n" + right


def extract_entries() -> dict[str, str]:
    """Return {fna_code: title_block}. Cached to ENTRIES_CACHE."""
    if ENTRIES_CACHE.exists():
        entries = json.loads(ENTRIES_CACHE.read_text(encoding="utf-8"))
        log.info("Loaded %d cached PDF entries", len(entries))
        return entries

    import pdfplumber  # local import: heavy, only needed for extraction

    log.info("Extracting PDF text column-by-column (this takes ~75 s) …")
    parts: list[str] = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            parts.append(_column_text(page))
            if i % 200 == 0:
                log.info("  page %d/%d", i, len(pdf.pages))
    full = "\n".join(parts)

    entries: dict[str, str] = {}
    for m in CODE_RE.finditer(full):
        code, block = m.group(1), m.group(2)
        cite = CITE_RE.search(block)
        title_block = block[: cite.start()] if cite else block[:140]
        entries.setdefault(code, title_block.strip())  # first occurrence wins

    ENTRIES_CACHE.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    log.info("Extracted %d FNA-coded entries → %s", len(entries), ENTRIES_CACHE)
    return entries


# ── normalization / join keys ───────────────────────────────────────────────
def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def norm_title(s: str) -> str:
    """Aggressive title key: drop (abbr), accents, and every non-alphanumeric.

    This single normalization absorbs all the PDF extraction noise at once:
    end-of-line hyphenation, dropped inter-word spaces, and the recurring
    "V ertrag" / "V orschriften" glyph artifact all vanish.
    """
    s = _strip_accents(s).lower()
    s = re.sub(r"\([^()]*\)", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def norm_abbr(s: str | None) -> str | None:
    if not s:
        return None
    return re.sub(r"[^a-z0-9]", "", _strip_accents(s).lower()) or None


def pdf_abbr(block: str) -> str | None:
    """Abbreviation from the last parenthetical, e.g. '(Anti-Doping-Gesetz – AntiDopG)'."""
    parens = re.findall(r"\(([^()]+)\)", block)
    if not parens:
        return None
    return norm_abbr(re.split(r"[–-]", parens[-1])[-1])


# ── GII corpus ──────────────────────────────────────────────────────────────
def fetch_gii() -> list[dict]:
    """Each GII TOC <link> is already the law's xml.zip URL; slug is its parent dir."""
    log.info("Fetching GII TOC")
    r = requests.get(GII_TOC, timeout=40, headers=HEADERS)
    r.raise_for_status()
    laws = []
    for item in etree.fromstring(r.content).findall(".//item"):
        title = item.findtext("title") or ""
        link = (item.findtext("link") or "").replace("http://", "https://")
        slug = link.rstrip("/").split("/")[-2] if link.endswith("/xml.zip") else ""
        if title and slug:
            laws.append({"title": title, "slug": slug, "zip": link})
    log.info("GII TOC: %d laws", len(laws))
    return laws


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_pdf()
    entries = extract_entries()

    by_title: dict[str, str] = {}
    by_abbr: dict[str, str] = {}
    for code, block in entries.items():
        kt = norm_title(block)
        if len(kt) >= 6:
            by_title.setdefault(kt, code)
        ka = pdf_abbr(block)
        if ka and len(ka) >= 2:
            by_abbr.setdefault(ka, code)
    log.info("Join maps: by_title=%d by_abbr=%d", len(by_title), len(by_abbr))

    gii = fetch_gii()
    fna_map: dict[str, str] = {}
    matched_title = matched_abbr = 0
    hist: dict[str, int] = {}
    for law in gii:
        code = by_title.get(norm_title(law["title"]))
        how = "title"
        if not code:
            code = by_abbr.get(norm_abbr(law["slug"]))
            how = "abbr"
        if code:
            fna_map[law["slug"]] = code
            hist[code[0]] = hist.get(code[0], 0) + 1
            if how == "title":
                matched_title += 1
            else:
                matched_abbr += 1

    n = len(gii)
    total = matched_title + matched_abbr
    ceiling = 100 * len(entries) / n

    results = {
        "fna_year": FNA_YEAR,
        "gii_law_count": n,
        "pdf_entry_count": len(entries),
        "coverage_ceiling_pct": round(ceiling, 1),
        "matched_total": total,
        "matched_by_title": matched_title,
        "matched_by_abbr_fallback": matched_abbr,
        "coverage_pct": round(100 * total / n, 1),
        "main_group_histogram": dict(sorted(hist.items())),
    }
    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "fna_map.json").write_text(json.dumps(fna_map, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"=== Spike B — FNA Acquisition (BMJ PDF {FNA_YEAR}) ===",
        f"GII corpus:        {n} laws",
        f"PDF FNA-coded entries: {len(entries)}  (coverage ceiling {ceiling:.1f}%)",
        "",
        f"COVERAGE: {total}/{n} = {100 * total / n:.1f}%",
        f"  by title:           {matched_title}",
        f"  by abbr (fallback):  {matched_abbr}",
        f"  unmatched (→ buzer enrichment / embedding): {n - total}",
        "",
        "Main-group distribution (the 9 base hues):",
    ]
    mx = max(hist.values()) if hist else 1
    for mg, cnt in sorted(hist.items()):
        lines.append(f"  {mg}: {cnt:5}  {'█' * (cnt * 40 // mx)}")
    summary = "\n".join(lines)
    (OUT_DIR / "summary.txt").write_text(summary, encoding="utf-8")
    print("\n" + summary)


if __name__ == "__main__":
    main()
