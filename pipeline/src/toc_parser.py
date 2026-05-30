"""Parse GII table of contents XML (gii-toc.xml) into a slug-keyed dict."""
from __future__ import annotations

from lxml import etree


def slug_from_link(link: str) -> str:
    """Extract slug from a GII law index URL.

    https://www.gesetze-im-internet.de/bgb/index.html  ->  bgb
    https://www.gesetze-im-internet.de/tkg_2021/index.html  ->  tkg_2021
    """
    parts = link.rstrip("/").rsplit("/", 2)
    return parts[-2] if len(parts) >= 2 else link


def zip_url_from_link(link: str) -> str:
    """Convert a GII law index URL to its xml.zip download URL."""
    base = link.rsplit("/", 1)[0]
    return base + "/xml.zip"


def parse_toc_xml(xml_bytes: bytes) -> dict[str, dict]:
    """Parse raw gii-toc.xml bytes.

    Returns {slug: {"zip_url": str, "title": str}}.
    Items without both <title> and <link> are silently skipped.
    """
    root = etree.fromstring(xml_bytes)
    result: dict[str, dict] = {}
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is None or link_el is None:
            continue
        link = (link_el.text or "").strip()
        if not link:
            continue
        slug = slug_from_link(link)
        result[slug] = {
            "zip_url": zip_url_from_link(link),
            "title": (title_el.text or "").strip(),
        }
    return result
