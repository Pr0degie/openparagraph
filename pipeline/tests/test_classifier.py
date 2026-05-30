from src.classifier import classify_law, extract_opening_text, main_group_from_fna


# ── main_group_from_fna ───────────────────────────────────────────────────────

def test_main_group_simple():
    assert main_group_from_fna("400-2") == 4

def test_main_group_single_digit_prefix():
    assert main_group_from_fna("51-1") == 5

def test_main_group_four_digit_prefix():
    assert main_group_from_fna("2120-3") == 2

def test_main_group_none():
    assert main_group_from_fna(None) is None

def test_main_group_all_nine_groups():
    for g in range(1, 10):
        assert main_group_from_fna(f"{g}00-1") == g


# ── extract_opening_text ──────────────────────────────────────────────────────

def _law_with_norms(*texts) -> dict:
    return {
        "norms": [
            {"enbez": f"§ {i+1}", "text_xml": t}
            for i, t in enumerate(texts)
        ]
    }


def test_extract_opening_text_strips_tags():
    law = _law_with_norms("<P>Hello <B>world</B>.</P>")
    result = extract_opening_text(law)
    assert result == "Hello world ."


def test_extract_opening_text_skips_empty_norms():
    law = _law_with_norms(None, "", "<P>Real content</P>")
    result = extract_opening_text(law)
    assert result == "Real content"


def test_extract_opening_text_truncates():
    long_text = "A" * 1000
    law = _law_with_norms(f"<P>{long_text}</P>")
    result = extract_opening_text(law)
    assert result is not None
    assert len(result) <= 500


def test_extract_opening_text_none_when_no_text():
    law = _law_with_norms(None, None)
    assert extract_opening_text(law) is None


def test_extract_opening_text_empty_norms_list():
    assert extract_opening_text({"norms": []}) is None


# ── classify_law ─────────────────────────────────────────────────────────────

def _sample_law_dict() -> dict:
    return {
        "jurabk": "BGB",
        "amtabk": "BGB",
        "langue": "Bürgerliches Gesetzbuch",
        "ausfertigung_datum": "1896-08-18",
        "norm_count": 2385,
        "norms": [
            {"enbez": "§ 1", "text_xml": "<P>Die Rechtsfähigkeit des Menschen...</P>"},
        ],
    }


def test_classify_law_metadata():
    r = classify_law("bgb", _sample_law_dict(), "400-2")
    assert r["slug"] == "bgb"
    assert r["jurabk"] == "BGB"
    assert r["langue"] == "Bürgerliches Gesetzbuch"
    assert r["ausfertigung_datum"] == "1896-08-18"
    assert r["norm_count"] == 2385


def test_classify_law_fna_fields():
    r = classify_law("bgb", _sample_law_dict(), "400-2")
    assert r["fna_code"] == "400-2"
    assert r["main_group"] == 4


def test_classify_law_unclassified():
    r = classify_law("bgb", _sample_law_dict(), None)
    assert r["fna_code"] is None
    assert r["main_group"] is None


def test_classify_law_has_opening_text():
    r = classify_law("bgb", _sample_law_dict(), "400-2")
    assert r["opening_text"] is not None
    assert "Rechtsfähigkeit" in r["opening_text"]


def test_classify_law_no_norms_list():
    law = {"jurabk": "X", "langue": "Test", "norm_count": 0}
    r = classify_law("x", law, None)
    assert r["opening_text"] is None
