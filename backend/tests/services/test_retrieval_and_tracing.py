import pytest

from app import observability
from app.services import retrieval
from app.services.analysis_orchestrator import run_analysis_agent_loop
from app.services.report_builder import build_report_payload

from ..fake_langfuse import FakeLangfuse

CHUNKS = [
    "Revenue increased 12 percent to $4.1 billion driven by subscription growth. Margin expanded.",
    "Item 1A. Risk Factors. Competition is intense and a key supplier shortage could delay shipments.",
    "Net cash provided by operating activities was $900 million. Liquidity remains strong.",
    "Our segment reporting covers two operating segments across North America and Europe.",
    "The board approved a new office lease in Austin with a ten year term.",
]


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.delenv("LLM_ENABLED", raising=False)
    monkeypatch.setenv("RETRIEVAL_EMBEDDINGS", "fake")
    retrieval._index.cache_clear()
    observability.reset_for_tests(None)
    yield
    observability.reset_for_tests(None)


# ---------- retrieval ----------
def test_lexical_is_the_default_and_unchanged():
    assert retrieval.retrieval_mode() == retrieval.LEXICAL
    payload = build_report_payload("ACME", CHUNKS, "focused")
    sections = [c["section"] for c in payload["citations"]]
    # Original keyword behaviour: first chunk containing each keyword; no chunk says "cash flow", so the
    # keyword-density fallback fills the third citation.
    # Original keyword behaviour: first chunk containing each keyword. No chunk says "cash flow", and the
    # keyword-density fallback only finds the same two chunks again, so there are two citations.
    assert sections == ["Item 7 - Management Discussion and Analysis", "Item 1A - Risk Factors"]


def test_hybrid_uses_langchain_and_still_cites_real_text(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid_langchain")
    assert retrieval.retrieval_mode() == retrieval.HYBRID
    # With the keyword side weighted fully, BM25 (lowercased tokens) finds the cash-flow chunk.
    monkeypatch.setenv("RETRIEVAL_BM25_WEIGHT", "1.0")
    assert retrieval.hybrid_rank(CHUNKS, "cash flows from operating activities and liquidity", 1) == [CHUNKS[2]]
    # The default fused ranking returns k distinct, real chunks.
    monkeypatch.setenv("RETRIEVAL_BM25_WEIGHT", "0.5")
    fused = retrieval.hybrid_rank(CHUNKS, "revenue growth", 3)
    assert len(fused) == 3 and len(set(fused)) == 3 and all(c in CHUNKS for c in fused)
    payload = build_report_payload("ACME", CHUNKS, "focused")
    assert len(payload["citations"]) == 3
    for citation in payload["citations"]:
        assert any(citation["excerpt"] in chunk for chunk in CHUNKS)


def test_hybrid_falls_back_to_lexical_when_packages_are_missing(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid_langchain")
    monkeypatch.setattr(retrieval, "hybrid_available", lambda: False)
    assert retrieval.retrieval_mode() == retrieval.LEXICAL
    assert run_analysis_agent_loop("ACME", CHUNKS)["retrievalMode"] == "lexical"


# ---------- tracing ----------
def test_no_keys_means_no_tracing_and_the_same_result():
    assert observability.client() is None
    result = run_analysis_agent_loop("ACME", CHUNKS)
    assert result["rounds"] >= 1 and 0.0 <= result["finalPrecision"] <= 1.0


def test_report_loop_is_one_trace_with_scored_rounds():
    fake = FakeLangfuse()
    observability.reset_for_tests(fake)
    result = run_analysis_agent_loop("ACME", CHUNKS)
    root = fake.named("report-analysis")[0]
    assert root["as_type"] == "agent" and root["parent"] is None
    checks = fake.named("citation-check")
    assert len(checks) == result["rounds"]
    assert all(c["as_type"] == "evaluator" and c["scores"][0]["name"] == "citation_precision" for c in checks)
    assert {s["name"] for s in root["trace_scores"]} == {"final_citation_precision", "rounds"}
    assert fake.named("round-1")[0]["parent"] == "report-analysis"
