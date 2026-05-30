import pytest

from src.fna_parser import (
    build_join_maps,
    join_fna,
    norm_abbr,
    norm_title,
    pdf_abbr,
)


# ── norm_title ────────────────────────────────────────────────────────────────

def test_norm_title_strips_parentheticals():
    assert norm_title("Bürgerliches Gesetzbuch (BGB)") == norm_title("Bürgerliches Gesetzbuch")

def test_norm_title_strips_accents():
    assert "a" in norm_title("Aufenthaltsgesetz")
    assert norm_title("Aufenthaltsgesetz") == norm_title("Aufenthaltsgesetz")

def test_norm_title_drops_spaces_and_punctuation():
    t = norm_title("Gesetz über den  Aufenthalt, die Erwerbstätigkeit")
    assert " " not in t
    assert "," not in t

def test_norm_title_lowercases():
    assert norm_title("BGB") == norm_title("bgb")

def test_norm_title_absorbs_hyphenation_artifact():
    # PDF extraction sometimes drops spaces: "Verord-nung" vs "Verordnung"
    a = norm_title("Anti-Doping-Gesetz")
    b = norm_title("AntiDopingGesetz")
    assert a == b


# ── norm_abbr ─────────────────────────────────────────────────────────────────

def test_norm_abbr_basic():
    assert norm_abbr("BGB") == "bgb"

def test_norm_abbr_strips_special_chars():
    assert norm_abbr("Anti-DopG") == "antidopg"

def test_norm_abbr_none_input():
    assert norm_abbr(None) is None

def test_norm_abbr_empty_string_returns_none():
    assert norm_abbr("") is None


# ── pdf_abbr ─────────────────────────────────────────────────────────────────

def test_pdf_abbr_simple():
    assert pdf_abbr("Bürgerliches Gesetzbuch (BGB)") == "bgb"

def test_pdf_abbr_with_dash_separator():
    # "Gesetz – AntiDopG" → last segment after dash
    assert pdf_abbr("Anti-Doping-Gesetz (Anti-Doping-Gesetz – AntiDopG)") == "antidopg"

def test_pdf_abbr_no_parens_returns_none():
    assert pdf_abbr("Bürgerliches Gesetzbuch") is None

def test_pdf_abbr_uses_last_parenthetical():
    # Multiple parens: last one should win
    result = pdf_abbr("Gesetz (Alt) (BGB)")
    assert result == "bgb"


# ── build_join_maps ───────────────────────────────────────────────────────────

def _sample_entries() -> dict[str, str]:
    return {
        "400-2": "Bürgerliches Gesetzbuch (BGB)\n",
        "451-1": "Strafgesetzbuch (StGB)\n",
        "26-1":  "X",   # too short title key — should be excluded from by_title
    }


def test_build_join_maps_by_title_has_long_keys_only():
    by_title, _ = build_join_maps(_sample_entries())
    # norm_title("X") is "x" → length 1 < 6 → must not be in by_title
    assert all(len(k) >= 6 for k in by_title)


def test_build_join_maps_title_lookup():
    by_title, _ = build_join_maps(_sample_entries())
    key = norm_title("Bürgerliches Gesetzbuch")
    assert by_title.get(key) == "400-2"


def test_build_join_maps_abbr_lookup():
    _, by_abbr = build_join_maps(_sample_entries())
    assert by_abbr.get("bgb") == "400-2"
    assert by_abbr.get("stgb") == "451-1"


def test_build_join_maps_first_occurrence_wins():
    entries = {
        "400-2": "Bürgerliches Gesetzbuch (BGB)\n",
        "400-9": "Bürgerliches Gesetzbuch (BGB)\n",   # duplicate title
    }
    by_title, _ = build_join_maps(entries)
    key = norm_title("Bürgerliches Gesetzbuch")
    assert by_title[key] == "400-2"   # first one wins


# ── join_fna ──────────────────────────────────────────────────────────────────

def _maps():
    entries = {
        "400-2": "Bürgerliches Gesetzbuch (BGB)\n",
        "451-1": "Strafgesetzbuch (StGB)\n",
        "860-3": "Telekommunikationsgesetz (TKG)\n",
        "100-1": "Soldatengesetz (SG)\n",
    }
    return build_join_maps(entries)


def test_join_fna_by_langue():
    by_title, by_abbr = _maps()
    slug_table = {"bgb": {"jurabk": "BGB", "langue": "Bürgerliches Gesetzbuch"}}
    toc = {"bgb": {"title": "Bürgerliches Gesetzbuch", "zip_url": ""}}
    result = join_fna(slug_table, toc, by_title, by_abbr)
    assert result["bgb"] == "400-2"


def test_join_fna_by_toc_title_when_langue_absent():
    by_title, by_abbr = _maps()
    slug_table = {"bgb": {"jurabk": "BGB", "langue": None}}
    toc = {"bgb": {"title": "Bürgerliches Gesetzbuch", "zip_url": ""}}
    result = join_fna(slug_table, toc, by_title, by_abbr)
    assert result["bgb"] == "400-2"


def test_join_fna_by_jurabk_abbr():
    by_title, by_abbr = _maps()
    # Give a title that won't match anything → falls through to jurabk
    slug_table = {"sg": {"jurabk": "SG", "langue": "Etwas völlig anderes"}}
    toc = {"sg": {"title": "Auch anders", "zip_url": ""}}
    result = join_fna(slug_table, toc, by_title, by_abbr)
    assert result["sg"] == "100-1"


def test_join_fna_by_slug_abbr_fallback():
    by_title, by_abbr = _maps()
    # slug "stgb" normalizes to "stgb" → by_abbr["stgb"] == "451-1"
    slug_table = {}
    toc = {"stgb": {"title": "Unbekannter Titel XYZ", "zip_url": ""}}
    result = join_fna(slug_table, toc, by_title, by_abbr)
    assert result["stgb"] == "451-1"


def test_join_fna_unmatched_slug_absent():
    by_title, by_abbr = _maps()
    slug_table = {}
    toc = {"unknownlaw123": {"title": "Gesetz über xyz", "zip_url": ""}}
    result = join_fna(slug_table, toc, by_title, by_abbr)
    assert "unknownlaw123" not in result


def test_join_fna_uses_all_toc_slugs():
    by_title, by_abbr = _maps()
    # slug_table has fewer slugs than toc (parse failures)
    slug_table = {"bgb": {"jurabk": "BGB", "langue": "Bürgerliches Gesetzbuch"}}
    toc = {
        "bgb":  {"title": "Bürgerliches Gesetzbuch", "zip_url": ""},
        "stgb": {"title": "Strafgesetzbuch", "zip_url": ""},
    }
    result = join_fna(slug_table, toc, by_title, by_abbr)
    # Both should be matched (bgb via langue, stgb via toc_title)
    assert result["bgb"] == "400-2"
    assert result["stgb"] == "451-1"
