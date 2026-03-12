from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CitationScore:
    citation_id: int
    section: str
    support_score: float
    supported: bool
    best_match_excerpt: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _normalize(text)))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def score_citation_against_chunks(citation_excerpt: str, chunks: list[str]) -> tuple[float, str]:
    excerpt_norm = _normalize(citation_excerpt)
    excerpt_tokens = _token_set(citation_excerpt)

    best_score = 0.0
    best_chunk = ""

    for chunk in chunks:
        chunk_norm = _normalize(chunk)

        # Strongest signal: exact normalized excerpt contained in filing chunk.
        if excerpt_norm and excerpt_norm in chunk_norm:
            return 1.0, chunk[:280]

        score = _jaccard(excerpt_tokens, _token_set(chunk))
        if score > best_score:
            best_score = score
            best_chunk = chunk[:280]

    return best_score, best_chunk
