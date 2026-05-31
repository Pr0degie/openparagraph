"""Serialize Law objects to JSON dicts and base HTML.

JSON (build/laws_parsed/{slug}.json) — used by Stage 06 (classify),
  Stage 07 (extract_refs), and Stage 08 (resolve_refs).

HTML (build/laws_parsed/{slug}.html) — stable base for Stage 14
  (diff_cache). Each norm is a <section id="{norm_id}"> so forward
  patches can target individual paragraphs.  Citation <span data-ref-id>
  elements are added by the frontend at render time via reference-resolver.json.
"""
from __future__ import annotations

import html
import re

from src.gii_parser import Law, Norm


def norm_id(enbez: str | None, idx: int) -> str:
    """Stable, URL-safe ID for a norm, derived from its enbez.

    § 1      -> "1"
    § 1a     -> "1a"
    Art. 2   -> "art-2"
    Anlage 3 -> "anlage-3"
    None     -> "norm-{idx}"
    """
    if not enbez:
        return f"norm-{idx}"
    s = enbez.strip()
    s = re.sub(r"^§\s*", "", s)
    s = re.sub(r"^Art\.\s*", "art-", s)
    s = re.sub(r"\s+", "-", s.lower())
    s = re.sub(r"[^\w-]", "", s)
    s = s.strip("-")
    return s or f"norm-{idx}"


def law_to_dict(slug: str, law: Law) -> dict:
    """Serialize a Law to a JSON-serializable dict."""
    return {
        "slug": slug,
        "jurabk": law.jurabk,
        "amtabk": law.amtabk,
        "ausfertigung_datum": law.ausfertigung_datum,
        "repealed_at": law.repealed_at,
        "langue": law.langue,
        "norm_count": law.norm_count,
        "parse_warnings": law.parse_warnings,
        "norms": [
            {
                "norm_id": norm_id(n.enbez, i),
                "enbez": n.enbez,
                "titel": n.titel,
                "text_xml": n.text_xml,
            }
            for i, n in enumerate(law.norms)
        ],
    }


def law_to_html(slug: str, law: Law) -> str:
    """Render a Law as base HTML for the diff cache.

    Each norm becomes <section id="{norm_id}"> so Stage 14 can generate
    per-paragraph patches.  The text_xml content is embedded verbatim —
    it comes from lxml serialization of GII's own XML, not user input.
    """
    abk = html.escape(law.jurabk or slug)
    title = html.escape(law.langue or law.jurabk or slug)

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="de">',
        "<head>",
        '  <meta charset="UTF-8">',
        f"  <title>{abk} – {title}</title>",
        "</head>",
        "<body>",
        f'<h1 data-slug="{html.escape(slug)}">{abk} – {title}</h1>',
    ]

    for idx, norm in enumerate(law.norms):
        nid = norm_id(norm.enbez, idx)
        heading = html.escape(norm.enbez or "")
        if norm.titel:
            heading += f" {html.escape(norm.titel)}"

        parts.append(f'<section id="{nid}">')
        if heading:
            parts.append(f"  <h2>{heading}</h2>")
        if norm.text_xml:
            parts.append(f'  <div class="norm-text">{norm.text_xml}</div>')
        parts.append("</section>")

    parts += ["</body>", "</html>"]
    return "\n".join(parts)
