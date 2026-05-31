"""Stage 15 — search index documents for the frontend.

Emits a compact JSON array of documents; the frontend builds its FlexSearch
index from these at load time. We ship the searchable *documents*, not a binary
FlexSearch export, because the pipeline is Python and FlexSearch is a JS library.

Searchable fields per document: jurabk + title + a short description (the law's
opening_text, truncated).
"""

from src.graph_builder import node_id  # reuse the canonical slug→node-id rule

DESC_MAX = 200


def _short_desc(text: str | None, desc_max: int) -> str | None:
    """Trim opening_text to a compact, word-boundary description (or None)."""
    desc = (text or "").strip()
    if not desc:
        return None
    if desc_max and len(desc) > desc_max:
        # cut near the limit on a space so the last token isn't sliced mid-word
        head = desc[:desc_max]
        desc = head.rsplit(" ", 1)[0].rstrip() if " " in head else head
    return desc or None


def build_search_index(
    nodes: list[dict],
    classified: dict[str, dict],
    jurisdiction: str,
    desc_max: int = DESC_MAX,
) -> list[dict]:
    """One search document per node: ``{id, jurabk, title, desc}``.

    Nodes already carry jurabk + title; ``classified`` supplies opening_text,
    mapped back to each node via the same ``node_id()`` the graph builder used,
    so ids line up exactly.
    """
    nid_to_meta = {
        node_id(meta.get("jurabk"), slug, jurisdiction): meta
        for slug, meta in classified.items()
    }
    docs = []
    for n in nodes:
        meta = nid_to_meta.get(n["id"], {})
        docs.append({
            "id": n["id"],
            "jurabk": n.get("jurabk"),
            "title": n.get("title"),
            "desc": _short_desc(meta.get("opening_text"), desc_max),
        })
    return docs
