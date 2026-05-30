import pytest

from src.embedder import texts_for_embedding

LAWS = {
    "stgb": {
        "langue": "Strafgesetzbuch",
        "opening_text": "Eine Straftat begeht, wer…",
        "fna_code": "450-2",
        "main_group": 4,
    },
    "bgb": {
        "langue": "Bürgerliches Gesetzbuch",
        "opening_text": "Wer geschäftsfähig ist…",
        "fna_code": "400-2",
        "main_group": 4,
    },
    "no_opening": {
        "langue": "Gesetz ohne Einleitungstext",
        "opening_text": None,
        "fna_code": None,
        "main_group": None,
    },
    "no_langue": {
        "langue": None,
        "opening_text": None,
        "fna_code": None,
        "main_group": None,
    },
}


def test_texts_for_embedding_sorted_order():
    slugs, texts = texts_for_embedding(LAWS)
    assert slugs == sorted(LAWS.keys())


def test_texts_for_embedding_count():
    slugs, texts = texts_for_embedding(LAWS)
    assert len(slugs) == len(texts) == len(LAWS)


def test_texts_for_embedding_title_and_opening_combined():
    slugs, texts = texts_for_embedding(LAWS)
    bgb_idx = slugs.index("bgb")
    assert "Bürgerliches Gesetzbuch" in texts[bgb_idx]
    assert "Wer geschäftsfähig" in texts[bgb_idx]


def test_texts_for_embedding_no_opening_text_falls_back_to_langue():
    slugs, texts = texts_for_embedding(LAWS)
    idx = slugs.index("no_opening")
    assert texts[idx] == "Gesetz ohne Einleitungstext"


def test_texts_for_embedding_no_langue_falls_back_to_slug():
    slugs, texts = texts_for_embedding(LAWS)
    idx = slugs.index("no_langue")
    assert texts[idx] == "no_langue"


def test_texts_for_embedding_deterministic():
    s1, t1 = texts_for_embedding(LAWS)
    s2, t2 = texts_for_embedding(LAWS)
    assert s1 == s2
    assert t1 == t2
