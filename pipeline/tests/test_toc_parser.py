from pathlib import Path

import pytest

from src.toc_parser import parse_toc_xml, slug_from_link, zip_url_from_link

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_slug_from_link_simple():
    assert slug_from_link("https://www.gesetze-im-internet.de/bgb/index.html") == "bgb"


def test_slug_from_link_versioned():
    assert slug_from_link("https://www.gesetze-im-internet.de/tkg_2021/index.html") == "tkg_2021"


def test_zip_url_from_link():
    link = "https://www.gesetze-im-internet.de/bgb/index.html"
    assert zip_url_from_link(link) == "https://www.gesetze-im-internet.de/bgb/xml.zip"


def test_parse_toc_xml_returns_three_complete_entries():
    xml = (FIXTURE_DIR / "sample_toc.xml").read_bytes()
    toc = parse_toc_xml(xml)
    # Two incomplete items (no link / no title) must be skipped.
    assert set(toc.keys()) == {"bgb", "tkg_2021", "stgb"}


def test_parse_toc_xml_entry_shape():
    xml = (FIXTURE_DIR / "sample_toc.xml").read_bytes()
    toc = parse_toc_xml(xml)
    assert toc["bgb"]["title"] == "Bürgerliches Gesetzbuch"
    assert toc["bgb"]["zip_url"] == "https://www.gesetze-im-internet.de/bgb/xml.zip"
    assert toc["tkg_2021"]["zip_url"] == "https://www.gesetze-im-internet.de/tkg_2021/xml.zip"
