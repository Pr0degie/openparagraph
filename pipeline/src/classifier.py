"""Attach FNA classification to parsed law metadata.

Stage 06 reads build/laws_parsed/{slug}.json (from Stage 04) and
build/fna_map.json (from Stage 05) and emits build/laws_classified.json:
a compact per-law record used by Stages 09, 10, 11, and 13.

Fields produced per law:
  slug, jurabk, amtabk, langue, ausfertigung_datum, norm_count
  fna_code    — "400-2" or null for unclassified laws
  main_group  — int 1–9 (first digit of FNA code) or null
  opening_text — first usable norm text, XML tags stripped, ≤ 500 chars
                 (used by Stage 09 as one of the two embedding fields)
"""
from __future__ import annotations

import re


def main_group_from_fna(fna_code: str | None) -> int | None:
    """Extract the 1-9 Sachgebiet main group from an FNA code.

    "400-2" → 4   "51-1" → 5   "2120-3" → 2   None → None
    """
    if not fna_code:
        return None
    try:
        return int(fna_code[0])
    except (IndexError, ValueError):
        return None


def _strip_xml_tags(s: str) -> str:
    """Replace XML/HTML tags with spaces and collapse whitespace."""
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_opening_text(law_dict: dict, max_chars: int = 500) -> str | None:
    """Return the first usable norm text, tags stripped, truncated.

    Skips norms whose text is empty after stripping.  Returns None if no
    usable text is found (e.g. purely structural laws with no body text).
    """
    for norm in law_dict.get("norms", []):
        text_xml = norm.get("text_xml")
        if not text_xml:
            continue
        text = _strip_xml_tags(text_xml)
        if text:
            return text[:max_chars]
    return None


def classify_law(slug: str, law_dict: dict, fna_code: str | None) -> dict:
    """Build a compact classified law record.

    Strips the full norms list — downstream stages that need norm-level
    detail read build/laws_parsed/{slug}.json directly.
    """
    return {
        "slug": slug,
        "jurabk": law_dict.get("jurabk"),
        "amtabk": law_dict.get("amtabk"),
        "langue": law_dict.get("langue"),
        "ausfertigung_datum": law_dict.get("ausfertigung_datum"),
        "repealed_at": law_dict.get("repealed_at"),
        "norm_count": law_dict.get("norm_count", 0),
        "fna_code": fna_code,
        "main_group": main_group_from_fna(fna_code),
        "opening_text": extract_opening_text(law_dict),
    }
