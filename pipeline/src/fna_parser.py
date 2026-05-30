"""Parse the BMJ annual FNA PDF and join codes to GII law slugs.

The FNA (Fundstellennachweis A) is the authoritative catalogue of German
federal laws, organised in a 9-group Sachgebiet taxonomy that drives the
graph's base hue.  The PDF is the primary source (ADR 002).

PDF entry shape (after column-aware extraction):

    400-2 Bürgerliches Gesetzbuch (BGB)
    vom 18. 8. 1896 ...

i.e. <FNA code>  <full title> (<abbr>)  [vom <date>] [<citation>]

Join key priority when matching a GII slug to a code:
  1. norm_title(langue)    — authoritative XML title
  2. norm_title(toc_title) — GII TOC title (fallback; differs for some laws)
  3. norm_abbr(jurabk)     — official abbreviation from XML
  4. norm_abbr(slug)       — GII slug as abbreviation (last resort)
"""
from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

import requests

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "openparagraph/1.0 (research; github.com/openparagraph)"}

# FNA code pattern: 1–4 digit Sachgebiet prefix, then -serial, optionally -N.
# The 1-digit floor matters: main group 5 (Verteidigung) codes start with "51-".
CODE_RE = re.compile(
    r"(?m)^(\d{1,4}-\d+(?:-\d+)?)\s+(.*?)(?=^\d{1,4}-\d+(?:-\d+)?\s|\Z)", re.S
)
# The Fundstelle citation anchors the END of the title block.  Numeric date only
# to avoid truncating treaty titles that contain spelled-out months.
CITE_RE = re.compile(r"vom\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{4}")


# ── normalization ─────────────────────────────────────────────────────────────

def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def norm_title(s: str) -> str:
    """Aggressive title join key: strip (abbr), accents, non-alphanumerics.

    Absorbs PDF extraction noise: end-of-line hyphenation, dropped spaces,
    and glyph artifacts ("V ertrag") all vanish after this normalization.
    """
    s = _strip_accents(s).lower()
    s = re.sub(r"\([^()]*\)", " ", s)   # drop parentheticals
    return re.sub(r"[^a-z0-9]+", "", s)


def norm_abbr(s: str | None) -> str | None:
    """Normalize an abbreviation to lowercase alphanumeric for join."""
    if not s:
        return None
    return re.sub(r"[^a-z0-9]", "", _strip_accents(s).lower()) or None


def pdf_abbr(block: str) -> str | None:
    """Extract the abbreviation from the last parenthetical in a title block.

    Example: 'Anti-Doping-Gesetz (Anti-DopG)' -> 'antidopg'
    Example: 'Bürgerliches Gesetzbuch (BGB)' -> 'bgb'
    Example: 'Gesetz über X (Gesetz – AntiDopG)' -> 'antidopg' (last segment)
    """
    parens = re.findall(r"\(([^()]+)\)", block)
    if not parens:
        return None
    return norm_abbr(re.split(r"[–-]", parens[-1])[-1])


# ── PDF acquisition + extraction ─────────────────────────────────────────────

def download_fna_pdf(url: str, dest: Path) -> None:
    """Download the FNA PDF to dest. No-op if dest already exists."""
    if dest.exists():
        log.info("PDF already cached: %s (%d bytes)", dest, dest.stat().st_size)
        return
    log.info("Downloading FNA PDF from %s", url)
    r = requests.get(url, timeout=120, headers=HEADERS)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise RuntimeError(f"download is not a PDF (got {r.content[:20]!r}…)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    log.info("Saved %s (%d bytes)", dest, len(r.content))


def _column_text(page) -> str:
    """Extract a two-column FNA page in reading order (left then right).

    pdfplumber's default extract_text() interleaves the two columns.
    Cropping each half and concatenating linearises them correctly.
    """
    w, h = page.width, page.height
    left  = page.crop((0, 0, w / 2, h)).extract_text() or ""
    right = page.crop((w / 2, 0, w, h)).extract_text() or ""
    return left + "\n" + right


def extract_entries_from_pdf(pdf_path: Path) -> dict[str, str]:
    """Return {fna_code: title_block} from the FNA PDF.

    Uses pdfplumber for column-aware extraction.  Takes ~75 s on the full
    FNA 2023 PDF; call sparingly and cache the result.
    """
    import pdfplumber   # deferred: heavy, only needed here

    log.info("Extracting PDF text column-by-column (takes ~75 s) …")
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            parts.append(_column_text(page))
            if i % 200 == 0:
                log.info("  page %d / %d", i, len(pdf.pages))
    full = "\n".join(parts)

    entries: dict[str, str] = {}
    for m in CODE_RE.finditer(full):
        code, block = m.group(1), m.group(2)
        cite = CITE_RE.search(block)
        title_block = block[: cite.start()] if cite else block[:140]
        entries.setdefault(code, title_block.strip())   # first occurrence wins
    log.info("Extracted %d FNA-coded entries", len(entries))
    return entries


# ── join maps + joining ───────────────────────────────────────────────────────

def build_join_maps(entries: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Build two lookup dicts from extracted FNA entries.

    Returns (by_title, by_abbr):
      by_title: {norm_title(block): fna_code}
      by_abbr:  {norm_abbr(abbr_from_block): fna_code}

    Short keys (< 6 / < 2 chars after normalization) are dropped to avoid
    false-positive collisions with very short law abbreviations.
    """
    by_title: dict[str, str] = {}
    by_abbr:  dict[str, str] = {}
    for code, block in entries.items():
        kt = norm_title(block)
        if len(kt) >= 6:
            by_title.setdefault(kt, code)
        ka = pdf_abbr(block)
        if ka and len(ka) >= 2:
            by_abbr.setdefault(ka, code)
    return by_title, by_abbr


def join_fna(
    slug_table: dict[str, dict],
    toc: dict[str, dict],
    by_title: dict[str, str],
    by_abbr: dict[str, str],
) -> dict[str, str]:
    """Join FNA codes to GII law slugs.

    Returns {slug: fna_code} for every slug that could be matched.

    Uses all slugs from toc (the complete corpus) and enriches lookups with
    jurabk + langue from slug_table.  Match priority:
      1. norm_title(langue)    — authoritative XML title
      2. norm_title(toc_title) — GII TOC title
      3. norm_abbr(jurabk)     — official abbreviation (e.g. "BGB", "TKG")
      4. norm_abbr(slug)       — GII slug as fallback abbreviation
    """
    result: dict[str, str] = {}
    stats = {"langue": 0, "toc_title": 0, "jurabk": 0, "slug": 0}

    for slug, toc_info in toc.items():
        meta = slug_table.get(slug, {})
        code: str | None = None
        how: str = ""

        if not code and meta.get("langue"):
            code = by_title.get(norm_title(meta["langue"]))
            how = "langue"

        if not code and toc_info.get("title"):
            code = by_title.get(norm_title(toc_info["title"]))
            how = "toc_title"

        if not code and meta.get("jurabk"):
            code = by_abbr.get(norm_abbr(meta["jurabk"]))
            how = "jurabk"

        if not code:
            code = by_abbr.get(norm_abbr(slug))
            how = "slug"

        if code:
            result[slug] = code
            stats[how] += 1

    total = len(toc)
    matched = len(result)
    log.info(
        "FNA join: %d / %d matched (%.1f%%) — "
        "langue=%d toc_title=%d jurabk=%d slug=%d",
        matched, total, 100 * matched / total if total else 0,
        stats["langue"], stats["toc_title"], stats["jurabk"], stats["slug"],
    )
    return result
