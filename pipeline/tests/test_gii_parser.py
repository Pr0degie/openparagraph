"""Unit tests for the GII XML parser (src/gii_parser.py)."""

from pathlib import Path

import pytest

from src.gii_parser import parse_law, parse_repeal_date, Law, Norm

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class TestParseWellFormedLaw:
    def setup_method(self):
        self.law = parse_law(load_fixture("sample_law.xml"), source="sample_law.xml")

    def test_returns_law_instance(self):
        assert isinstance(self.law, Law)

    def test_jurabk(self):
        assert self.law.jurabk == "TestG"

    def test_amtabk(self):
        assert self.law.amtabk == "TestG"

    def test_ausfertigung_datum(self):
        assert self.law.ausfertigung_datum == "2000-01-01"

    def test_langue(self):
        assert self.law.langue == "Testgesetz"

    def test_norm_count(self):
        # Two content norms (§ 1, § 2); header is not counted in content_norms
        assert self.law.norm_count == 2
        assert len(self.law.content_norms) == 2

    def test_first_norm_enbez(self):
        assert self.law.norms[0].enbez == "§ 1"

    def test_first_norm_titel(self):
        assert self.law.norms[0].titel == "Anwendungsbereich"

    def test_second_norm_no_titel(self):
        # § 2 has no <titel> in the fixture — must be None, not raise
        assert self.law.norms[1].titel is None

    def test_no_parse_warnings(self):
        assert self.law.parse_warnings == []

    def test_repealed_at_none_for_active_law(self):
        # sample_law.xml has no Aufh standangabe → still in force
        assert self.law.repealed_at is None

    def test_text_xml_present(self):
        assert self.law.norms[0].text_xml is not None
        assert "Testfälle" in self.law.norms[0].text_xml


class TestParseMalformedLaw:
    def setup_method(self):
        self.law = parse_law(load_fixture("malformed_law.xml"), source="malformed.xml")

    def test_returns_law_instance(self):
        # Recovery parser should salvage what it can; no exception raised
        assert isinstance(self.law, Law)

    def test_jurabk_recovered(self):
        # Even with broken XML, recovery parser should find <jurabk>
        assert self.law.jurabk == "MalG"

    def test_warning_emitted(self):
        # Parser must log the malformed condition
        assert any("recovered" in w.lower() or "syntax" in w.lower()
                   for w in self.law.parse_warnings)


class TestParseNoLangue:
    def setup_method(self):
        self.law = parse_law(load_fixture("no_langue.xml"), source="no_langue.xml")

    def test_langue_is_none(self):
        assert self.law.langue is None

    def test_warning_about_missing_langue(self):
        assert any("langue" in w.lower() for w in self.law.parse_warnings)

    def test_jurabk_still_present(self):
        assert self.law.jurabk == "NoLangG"

    def test_norm_count(self):
        assert self.law.norm_count == 1

    def test_ausfertigung_datum(self):
        assert self.law.ausfertigung_datum == "2010-06-15"


class TestParseEmptyInput:
    def test_completely_empty_bytes(self):
        law = parse_law(b"", source="empty")
        assert isinstance(law, Law)
        assert law.jurabk is None
        assert law.parse_warnings  # must have at least one warning

    def test_no_norms(self):
        xml = b"<dokument></dokument>"
        law = parse_law(xml, source="no-norms")
        assert law.norm_count == 0
        assert law.parse_warnings  # must warn about missing norms


class TestParseRepealedLaw:
    def setup_method(self):
        self.law = parse_law(
            load_fixture("sample_repealed_law.xml"), source="sample_repealed_law.xml"
        )

    def test_returns_law_instance(self):
        assert isinstance(self.law, Law)

    def test_repealed_at_uses_mwv_not_citation_date(self):
        # standkommentar holds "v. 8.7.2025" (amending act) before "mWv 1.7.2026"
        # (effective repeal). The anchor parser must pick the mWv date.
        assert self.law.repealed_at == "2026-07-01"

    def test_created_at_unaffected(self):
        assert self.law.ausfertigung_datum == "2005-03-10"

    def test_no_spurious_warnings(self):
        # Aufh date parses cleanly → no "without parseable date" warning
        assert not any("without parseable date" in w for w in self.law.parse_warnings)


class TestParseRepealDate:
    """Direct unit tests of the anchor-based repeal-date parser."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            # "mit Ablauf [des] DD.MM.YYYY außer Kraft"
            ("Die V tritt gem. § 10 ... mit Ablauf d. 31.12.2026 außer Kraft", "2026-12-31"),
            ("... mit Ablauf des 31.12.2028 außer Kraft", "2028-12-31"),
            # "mWv DD.MM.YYYY" — and the citation date "v. 8.7.2025" must be ignored
            ("V aufgeh. durch § 9a idF d. Art. 2 V v. 8.7.2025 mWv 1.7.2026", "2026-07-01"),
            # selective repeal: two mWv dates → latest wins
            (
                "G aufgeh. durch Art. 10 ... mWv 7.10.2025 mit Ausnahme des § 17 "
                "Abs. 6, dieser tritt gem. Art. 10 Satz 2 ... mWv 18.8.2026 außer Kraft",
                "2026-08-18",
            ),
            # "am DD.MM.YYYY ... außer Kraft"
            ("Die V tritt gem. § 2 am 31.12.2026 außer Kraft", "2026-12-31"),
            # sequential Verlängerung overrides earlier expiry → latest "bis zum"
            (
                "tritt am 31.12.2016 außer Kraft; durch Art. 1 ... bis zum 31.12.2026 "
                "und durch Art. 2 ... bis zum 31.12.2031 verlängert worden",
                "2031-12-31",
            ),
            # one- vs two-digit day/month normalize identically
            ("... mWv 1.7.2026", "2026-07-01"),
            ("... mWv 01.07.2026", "2026-07-01"),
            # open-ended / conditional repeal with no concrete date → None
            (
                "tritt an dem Tag außer Kraft, an dem das Abkommen außer Kraft tritt",
                None,
            ),
            # empty / missing input
            ("", None),
            (None, None),
        ],
    )
    def test_parse_repeal_date(self, text, expected):
        assert parse_repeal_date(text) == expected


class TestZipUrl:
    """Test the URL transformation logic from the spike script."""

    def test_index_html_to_xml_zip(self):
        from spikes.spike_a_data_shape import law_xml_zip_url
        url = "https://www.gesetze-im-internet.de/bgb/index.html"
        assert law_xml_zip_url(url) == "https://www.gesetze-im-internet.de/bgb/xml.zip"

    def test_preserves_scheme_and_host(self):
        from spikes.spike_a_data_shape import law_xml_zip_url
        url = "https://www.gesetze-im-internet.de/stgb/index.html"
        assert law_xml_zip_url(url).startswith("https://www.gesetze-im-internet.de/stgb/")
