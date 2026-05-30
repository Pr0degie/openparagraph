"""Compute sentence embeddings for all laws.

Rows in the output array correspond to sorted(laws_classified.keys()).
Embeddings are L2-normalised so cosine similarity = dot product.
"""

import numpy as np


def texts_for_embedding(laws_classified: dict[str, dict]) -> tuple[list[str], list[str]]:
    """Return (slugs, texts) in sorted-slug order."""
    slugs = sorted(laws_classified.keys())
    texts = []
    for slug in slugs:
        meta = laws_classified[slug]
        langue = (meta.get("langue") or slug).strip()
        opening = (meta.get("opening_text") or "").strip()
        texts.append(f"{langue} {opening}".strip() if opening else langue)
    return slugs, texts


def embed(texts: list[str], model_name: str, batch_size: int = 64) -> np.ndarray:
    """Load SentenceTransformer model and encode texts.

    Returns float32 ndarray of shape (N, D), L2-normalised.
    Importing sentence_transformers here so the module is importable without it installed.
    """
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    model = SentenceTransformer(model_name)
    return model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
