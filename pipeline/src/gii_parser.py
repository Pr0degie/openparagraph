"""
Parse GII (gesetze-im-internet.de) law XML into structured Python objects.

GII XML structure:
  <dokument>
    <norm>          ← first norm = law header (Stammnorm)
      <metadaten>
        <jurabk>    ← abbreviation  (BGB, StGB, …)
        <amtabk>    ← official abk  (may differ or be absent)
        <ausfertigung-datum>  ← ISO date of enactment
        <langue>    ← full title
        <gliederungseinheit> ← optional sub-classification
      </metadaten>
      <textdaten>   ← preamble / Eingangsformel
    </norm>
    <norm>          ← subsequent norms = individual §§
      <metadaten>
        <jurabk>
        <enbez>     ← "§ 1", "§ 2", "Art. 1", …
        <titel>     ← § heading (may be absent)
      </metadaten>
      <textdaten>
        <text>      ← rendered paragraph content (format="XML" or "text")
    </norm>
    …
  </dokument>

The XML is intentionally dirty (style markup, inconsistent nesting).
Parse defensively: log problems and continue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from lxml import etree

log = logging.getLogger(__name__)


@dataclass
class Norm:
    enbez: Optional[str]        # "§ 1", "Art. 2", …; None for the header norm
    titel: Optional[str]        # § heading, if present
    text_xml: Optional[str]     # raw inner XML of <textdaten><text>


@dataclass
class Law:
    jurabk: Optional[str]
    amtabk: Optional[str]
    ausfertigung_datum: Optional[str]   # ISO date string, e.g. "1896-08-18"
    langue: Optional[str]               # full German title
    norms: list[Norm] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)

    @property
    def norm_count(self) -> int:
        return len(self.norms)

    @property
    def content_norms(self) -> list[Norm]:
        """Norms that are actual §§ (enbez present), not the header."""
        return [n for n in self.norms if n.enbez is not None]


def _text(el: Optional[etree._Element], xpath: str) -> Optional[str]:
    if el is None:
        return None
    found = el.find(xpath)
    return found.text if found is not None else None


def _inner_xml(el: Optional[etree._Element]) -> Optional[str]:
    """Serialize inner XML of an element as a string."""
    if el is None:
        return None
    parts = [el.text or ""]
    for child in el:
        parts.append(etree.tostring(child, encoding="unicode"))
    return "".join(parts).strip() or None


def parse_law(xml_bytes: bytes, source: str = "") -> Law:
    """
    Parse raw GII law XML bytes into a Law object.

    Handles malformed input gracefully: logs warnings, fills missing fields
    with None, and continues. Never raises on dirty XML.
    """
    warnings: list[str] = []

    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        # Try recovery parser for really broken documents
        try:
            root = etree.fromstring(xml_bytes, parser=etree.XMLParser(recover=True))
            warnings.append(f"XMLSyntaxError recovered: {exc}")
        except Exception:
            warnings.append(f"Unrecoverable XMLSyntaxError: {exc}")
            return Law(
                jurabk=None, amtabk=None,
                ausfertigung_datum=None, langue=None,
                parse_warnings=warnings,
            )

    all_norms = root.findall(".//norm")
    if not all_norms:
        warnings.append(f"No <norm> elements found in {source}")
        return Law(
            jurabk=None, amtabk=None,
            ausfertigung_datum=None, langue=None,
            parse_warnings=warnings,
        )

    # Header norm: first <norm>
    header = all_norms[0]
    header_meta = header.find("metadaten")

    jurabk = _text(header_meta, "jurabk")
    amtabk = _text(header_meta, "amtabk")
    langue = _text(header_meta, "langue")

    # ausfertigung-datum: the element text is the date; attribute "manuell" is metadata
    datum_el = header_meta.find("ausfertigung-datum") if header_meta is not None else None
    ausfertigung_datum = datum_el.text if datum_el is not None else None

    if jurabk is None:
        warnings.append(f"Missing <jurabk> in header norm of {source}")
    if langue is None:
        warnings.append(f"Missing <langue> in header norm of {source}")

    # Parse individual §§ (skip the header norm itself)
    norms: list[Norm] = []
    for norm_el in all_norms[1:]:
        meta = norm_el.find("metadaten")
        enbez = _text(meta, "enbez")
        titel = _text(meta, "titel")
        text_el = norm_el.find(".//textdaten/text")
        text_xml = _inner_xml(text_el)
        norms.append(Norm(enbez=enbez, titel=titel, text_xml=text_xml))

    return Law(
        jurabk=jurabk,
        amtabk=amtabk,
        ausfertigung_datum=ausfertigung_datum,
        langue=langue,
        norms=norms,
        parse_warnings=warnings,
    )
