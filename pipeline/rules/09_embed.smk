# Stage 09 — Sentence embeddings for all laws.
# Input:  build/laws_classified.json   (Stage 06)
# Output: build/embeddings.npy         (float32, L2-normalised, rows = sorted slugs)
#
# Model is downloaded once to the HuggingFace cache; subsequent runs are instant.
# Row order is deterministic: sorted(laws_classified.keys()).

rule embed:
    input:
        classified="build/laws_classified.json",
    output:
        embeddings="build/embeddings.npy",
    run:
        import json
        import logging
        import sys
        import numpy as np
        from pathlib import Path

        sys.path.insert(0, str(Path(workflow.snakefile).parent))
        from src.embedder import texts_for_embedding, embed

        _log = logging.getLogger("stage09")

        classified = json.loads(Path(input.classified).read_text())
        slugs, texts = texts_for_embedding(classified)

        _log.info("Embedding %d laws with model %s", len(texts), config["embeddings"]["model"])

        emb = embed(texts, model_name=config["embeddings"]["model"])

        np.save(output.embeddings, emb)
        _log.info("Saved embeddings shape %s to %s", emb.shape, output.embeddings)
