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
import re
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
    repealed_at: Optional[str] = None   # ISO date of repeal, if known (see extract_repealed_at)
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


# ── Repeal-date extraction ──────────────────────────────────────────────────────
#
# A repealed law carries a <standangabe><standtyp>Aufh</standtyp> block whose
# <standkommentar> is free German prose, e.g.
#   "Die V tritt gem. § 10 ... mit Ablauf d. 31.12.2026 außer Kraft"
#   "V aufgeh. durch § 9a idF d. Art. 2 V v. 8.7.2025 mWv 1.7.2026"
# Only ~4 % of laws have this; ~10 % of those state no concrete date (conditional
# or open-ended repeal) — those correctly yield None.
#
# Strategy: anchor-based, in priority order. The date of the *amending* act
# ("... v. 8.7.2025 ...") is NOT an anchor and is therefore never picked up by
# mistake. Within the winning class, the latest date wins (conservative for
# selective/partial repeals like "mWv 7.10.2025 ... mit Ausnahme ... mWv 18.8.2026").

_DATE = r"(\d{1,2})\.(\d{1,2})\.(\d{4})"
_RE_VERLAENGERT = re.compile(rf"bis zum\s+{_DATE}", re.IGNORECASE)
_RE_MIT_ABLAUF = re.compile(rf"mit Ablauf\s+(?:d(?:es|\.)\s+)?{_DATE}", re.IGNORECASE)
_RE_MWV = re.compile(rf"mWv\s+{_DATE}", re.IGNORECASE)
_RE_AM_AUSSER = re.compile(rf"\bam\s+{_DATE}\b[^.]*außer Kraft", re.IGNORECASE)


def _latest_iso(matches: list[tuple[str, str, str]]) -> Optional[str]:
    """(day, month, year) tuples → latest date as ISO 'YYYY-MM-DD' (max works
    lexicographically on zero-padded ISO = chronologically)."""
    isos = [f"{y}-{m.zfill(2)}-{d.zfill(2)}" for (d, m, y) in matches]
    return max(isos) if isos else None


def parse_repeal_date(text: Optional[str]) -> Optional[str]:
    """Extract a repeal date (ISO 'YYYY-MM-DD') from a <standkommentar> string.

    Returns None if no date can be anchored. Pure function — unit-tested directly.
    """
    if not text:
        return None
    # 1. Sequential Verlängerung overrides earlier expiry — only when explicitly extended.
    if re.search(r"verläng", text, re.IGNORECASE):
        iso = _latest_iso(_RE_VERLAENGERT.findall(text))
        if iso:
            return iso
    # 2. "mit Ablauf [des] DD.MM.YYYY"
    iso = _latest_iso(_RE_MIT_ABLAUF.findall(text))
    if iso:
        return iso
    # 3. "mWv DD.MM.YYYY" (mit Wirkung vom)
    iso = _latest_iso(_RE_MWV.findall(text))
    if iso:
        return iso
    # 4. "am DD.MM.YYYY ... außer Kraft"
    iso = _latest_iso(_RE_AM_AUSSER.findall(text))
    if iso:
        return iso
    return None


def extract_repealed_at(
    header_meta: Optional[etree._Element],
    warnings: Optional[list[str]] = None,
    source: str = "",
) -> Optional[str]:
    """Scan the header <metadaten> for Aufh standangabe(n) and return the latest
    parseable repeal date, or None. A law may carry several standangabe blocks
    (Stand/Sonst/Neuf/Hinweis/Aufh); only standtyp == 'Aufh' is relevant."""
    if header_meta is None:
        return None
    candidates: list[str] = []
    for sa in header_meta.findall("standangabe"):
        typ = sa.find("standtyp")
        if typ is None or (typ.text or "").strip() != "Aufh":
            continue
        komm = sa.find("standkommentar")
        iso = parse_repeal_date(komm.text if komm is not None else None)
        if iso:
            candidates.append(iso)
        elif warnings is not None:
            warnings.append(f"Aufh standangabe without parseable date in {source}")
    return max(candidates) if candidates else None


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

    # Repeal date from an Aufh standangabe, if present (defensive: never raises)
    try:
        repealed_at = extract_repealed_at(header_meta, warnings, source)
    except Exception as exc:  # noqa: BLE001 — dirty XML must never abort the parse
        warnings.append(f"repealed_at extraction failed in {source}: {exc}")
        repealed_at = None

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
        repealed_at=repealed_at,
        norms=norms,
        parse_warnings=warnings,
    )
