import json

import pytest

from src.ref_extractor import (
    FALSE_POSITIVES,
    init_extractor,
    is_false_positive,
    process_law_file,
    strip_tags,
)


# ── is_false_positive ─────────────────────────────────────────────────────────

def test_false_positive_blocklist_words():
    for word in ["vorschriften", "verordnung", "rechtsverordnung", "anordnung",
                 "haftung", "bundes", "überwachung", "ordnungswidrigkeiten"]:
        assert is_false_positive(word), f"{word!r} should be a false positive"

def test_false_positive_case_insensitive():
    assert is_false_positive("Vorschriften")
    assert is_false_positive("VERORDNUNG")

def test_false_positive_valid_law_names():
    for word in ["bgb", "stgb", "gg", "aufenthaltsgesetz", "bürgerlichesgesetzbuch"]:
        assert not is_false_positive(word), f"{word!r} should not be filtered"

def test_false_positive_empty_string_is_not_in_blocklist():
    # Empty book is rejected by "if not book" guard in process_law_file,
    # not by is_false_positive — so it correctly returns False here.
    assert not is_false_positive("")

def test_false_positive_none_is_not_in_blocklist():
    assert not is_false_positive(None)


# ── strip_tags ────────────────────────────────────────────────────────────────

def test_strip_tags_removes_element():
    assert strip_tags("<P>Hello</P>") == "Hello"

def test_strip_tags_nested():
    assert strip_tags("<P>A <B>bold</B> word.</P>") == "A bold word."

def test_strip_tags_collapses_whitespace():
    result = strip_tags("<P>A</P>  <P>B</P>")
    assert "  " not in result

def test_strip_tags_empty_string():
    assert strip_tags("") == ""

def test_strip_tags_no_tags():
    assert strip_tags("plain text") == "plain text"


# ── process_law_file (integration with real refex) ───────────────────────────

@pytest.fixture(scope="module")
def extractor_ready():
    """Initialize the module-level extractor once for the module."""
    init_extractor()


def test_process_law_file_finds_citation(tmp_path, extractor_ready):
    law = {
        "norms": [{
            "norm_id": "433",
            "enbez": "§ 433",
            "text_xml": "<P>Gemäß § 242 BGB ist der Schuldner zur Leistung verpflichtet.</P>",
        }]
    }
    p = tmp_path / "test_bgb.json"
    p.write_text(json.dumps(law))

    results = process_law_file(str(p))

    assert len(results) >= 1
    r = results[0]
    assert r["source_slug"] == "test_bgb"
    assert r["book"] == "bgb"
    assert r["number"] == "242"


def test_process_law_file_filters_false_positives(tmp_path, extractor_ready):
    law = {
        "norms": [{
            "norm_id": "1",
            "enbez": "§ 1",
            "text_xml": "<P>Die einschlägigen Vorschriften und Verordnungen gelten entsprechend.</P>",
        }]
    }
    p = tmp_path / "test_law.json"
    p.write_text(json.dumps(law))

    results = process_law_file(str(p))

    books = [r["book"] for r in results]
    assert "vorschriften" not in books
    assert "verordnung" not in books


def test_process_law_file_skips_empty_norms(tmp_path, extractor_ready):
    law = {
        "norms": [
            {"norm_id": "1", "enbez": "§ 1", "text_xml": None},
            {"norm_id": "2", "enbez": "§ 2", "text_xml": ""},
        ]
    }
    p = tmp_path / "empty_law.json"
    p.write_text(json.dumps(law))

    results = process_law_file(str(p))
    assert results == []


def test_process_law_file_bad_json_returns_empty(tmp_path, extractor_ready):
    p = tmp_path / "bad.json"
    p.write_text("NOT JSON {{{")

    results = process_law_file(str(p))
    assert results == []


def test_process_law_file_record_shape(tmp_path, extractor_ready):
    law = {
        "norms": [{
            "norm_id": "433",
            "enbez": "§ 433",
            "text_xml": "<P>Gemäß § 242 BGB ist der Schuldner zur Leistung verpflichtet.</P>",
        }]
    }
    p = tmp_path / "shape_test.json"
    p.write_text(json.dumps(law))

    results = process_law_file(str(p))
    assert results  # at least one citation

    r = results[0]
    assert "source_slug" in r
    assert "source_norm_id" in r
    assert "book" in r
    assert "number" in r
    assert "unit" in r
    assert "span_text" in r
    assert "confidence" in r
