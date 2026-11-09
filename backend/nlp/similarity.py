"""Semantic similarity over SBERT embeddings.

Pure function: the API layer supplies candidate rows, this module never reads
the database. Candidate dictionaries are copied and returned with an added
`similarity` value, so fields such as `source` pass through untouched.
"""

from __future__ import annotations

import numpy as np

from backend.nlp.encoder import encode_texts
from backend.nlp.preprocess import clean_text


def rank_similar(
    query_text: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    query = clean_text(query_text) if query_text else ""
    if not query or not candidates or top_k <= 0:
        return []

    candidate_texts: list[str] = []
    active_positions: list[int] = []
    for position, candidate in enumerate(candidates):
        text = candidate.get("text") or candidate.get("normalized_text") or ""
        candidate_texts.append(clean_text(text) if text else "")
        if candidate_texts[-1]:
            active_positions.append(position)

    scores = [0.0] * len(candidates)
    if active_positions:
        vectors = encode_texts([query] + [candidate_texts[i] for i in active_positions])
        query_vector = vectors[0]
        candidate_vectors = vectors[1:]
        similarities = np.clip(candidate_vectors @ query_vector, 0.0, 1.0)
        for position, similarity in zip(active_positions, similarities):
            scores[position] = float(similarity)

    ranked: list[dict] = []
    for position, candidate in enumerate(candidates):
        item = dict(candidate)
        item["similarity"] = scores[position]
        ranked.append((position, item))

    ranked.sort(key=lambda pair: (-pair[1]["similarity"], pair[0]))
    return [item for _, item in ranked[:top_k]]


__all__ = ["rank_similar"]
