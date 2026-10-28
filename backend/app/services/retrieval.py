"""Which filing chunks the report draws from.

RETRIEVAL_MODE=lexical (the default) keeps the original keyword-density ranking in report_builder and
llm_report_agent, untouched.

RETRIEVAL_MODE=hybrid_langchain fuses BM25 keyword search with embedding search through LangChain's
EnsembleRetriever (reciprocal rank fusion). Embeddings come from FastEmbed, which runs locally with no API
key; set RETRIEVAL_EMBEDDINGS=fake for offline tests. If the optional packages are missing, the app falls
back to lexical and says so in the result.

Either way, the citation check in citation_eval stays exactly the same, so the two modes are graded by the
same deterministic rule.
"""
from __future__ import annotations

import hashlib
import os
import re
from functools import lru_cache
from typing import Any

LEXICAL = "lexical"
HYBRID = "hybrid_langchain"


def requested_mode() -> str:
    return HYBRID if os.getenv("RETRIEVAL_MODE", LEXICAL).strip().lower() == HYBRID else LEXICAL


def hybrid_available() -> bool:
    try:
        import langchain_classic.retrievers  # noqa: F401
        import langchain_community.retrievers  # noqa: F401
        import langchain_core.vectorstores  # noqa: F401
        import rank_bm25  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def retrieval_mode() -> str:
    """The mode that will actually run."""
    if requested_mode() == HYBRID and hybrid_available():
        return HYBRID
    return LEXICAL


def _embeddings() -> Any:
    kind = os.getenv("RETRIEVAL_EMBEDDINGS", "fastembed").strip().lower()
    if kind == "fake":
        from langchain_core.embeddings import DeterministicFakeEmbedding

        return DeterministicFakeEmbedding(size=64)
    from langchain_community.embeddings import FastEmbedEmbeddings

    return FastEmbedEmbeddings(model_name=os.getenv("RETRIEVAL_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"))


def _tokens(text: str) -> list[str]:
    """Lowercase word tokens, so 'Liquidity.' matches 'liquidity' (BM25's default is a raw whitespace split)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _keyword_weight() -> float:
    """Share of the fused ranking given to BM25 (RETRIEVAL_BM25_WEIGHT, default 0.5); the rest goes to embeddings."""
    try:
        return min(max(float(os.getenv("RETRIEVAL_BM25_WEIGHT", "0.5")), 0.0), 1.0)
    except ValueError:
        return 0.5


@lru_cache(maxsize=8)
def _index(chunk_key: str, chunks: tuple[str, ...], k: int, keyword_weight: float) -> Any:
    """Build the BM25 and vector retrievers once per filing; rounds and sections reuse them."""
    from langchain_classic.retrievers import EnsembleRetriever
    from langchain_community.retrievers import BM25Retriever
    from langchain_core.documents import Document
    from langchain_core.vectorstores import InMemoryVectorStore

    documents = [Document(page_content=text, metadata={"chunk_index": i}) for i, text in enumerate(chunks)]
    keyword = BM25Retriever.from_documents(documents, preprocess_func=_tokens)
    keyword.k = k
    store = InMemoryVectorStore.from_documents(documents, embedding=_embeddings())
    semantic = store.as_retriever(search_kwargs={"k": k})
    return EnsembleRetriever(retrievers=[keyword, semantic], weights=[keyword_weight, 1.0 - keyword_weight])


def hybrid_rank(chunks: list[str], query: str, k: int = 3) -> list[str]:
    """Top-k chunks for a query using BM25 plus embeddings, fused by LangChain's EnsembleRetriever."""
    if not chunks:
        return []
    k = max(1, min(k, len(chunks)))
    key = hashlib.sha1("\x00".join(chunks).encode("utf-8")).hexdigest()
    retriever = _index(key, tuple(chunks), max(k, 8), _keyword_weight())
    seen: set[str] = set()
    ranked: list[str] = []
    for document in retriever.invoke(query):
        if document.page_content not in seen:
            seen.add(document.page_content)
            ranked.append(document.page_content)
        if len(ranked) >= k:
            break
    return ranked
