from src.search_index import build_search_index

CLASSIFIED = {
    "BGB": {
        "jurabk": "BGB",
        "langue": "Bürgerliches Gesetzbuch",
        "opening_text": "Buch 1. Allgemeiner Teil. " * 50,  # long → truncated
    },
    "StGB": {
        "jurabk": "StGB",
        "langue": "Strafgesetzbuch",
        "opening_text": "Kurz.",
    },
    "NOJURABK": {
        "jurabk": None,
        "langue": "Ein Gesetz ohne jurabk",
        "opening_text": "",
    },
}

# nodes as graph_builder emits them: id = node_id(jurabk or slug) under the jur.
NODES = [
    {"id": "de-bund/BGB", "jurabk": "BGB", "title": "Bürgerliches Gesetzbuch"},
    {"id": "de-bund/StGB", "jurabk": "StGB", "title": "Strafgesetzbuch"},
    {"id": "de-bund/NOJURABK", "jurabk": None, "title": "Ein Gesetz ohne jurabk"},
]


def test_one_doc_per_node():
    idx = build_search_index(NODES, CLASSIFIED, "de-bund")
    assert len(idx) == len(NODES)


def test_doc_has_core_fields():
    idx = build_search_index(NODES, CLASSIFIED, "de-bund")
    bgb = next(d for d in idx if d["id"] == "de-bund/BGB")
    assert bgb["jurabk"] == "BGB"
    assert bgb["title"] == "Bürgerliches Gesetzbuch"
    assert bgb["desc"].startswith("Buch 1.")


def test_desc_truncated_on_word_boundary():
    idx = build_search_index(NODES, CLASSIFIED, "de-bund", desc_max=20)
    bgb = next(d for d in idx if d["id"] == "de-bund/BGB")
    assert len(bgb["desc"]) <= 20
    assert not bgb["desc"].endswith(" ")


def test_empty_opening_text_becomes_none():
    idx = build_search_index(NODES, CLASSIFIED, "de-bund")
    n = next(d for d in idx if d["id"] == "de-bund/NOJURABK")
    assert n["desc"] is None


def test_node_without_jurabk_maps_by_slug():
    # node_id(None, slug, jur) falls back to the slug, so the classified entry
    # still lines up with the node id.
    idx = build_search_index(NODES, CLASSIFIED, "de-bund")
    n = next(d for d in idx if d["id"] == "de-bund/NOJURABK")
    assert n["title"] == "Ein Gesetz ohne jurabk"
