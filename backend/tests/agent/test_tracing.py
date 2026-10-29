from app import observability
from app.agent.llm import ScriptedModel
from app.agent.loop import run_agent

from ..fake_langfuse import FakeLangfuse
from .fakes import FakeSec
from .test_agent import GOOD, _final, _gather


def test_agent_run_is_one_trace_with_calls_tools_and_scores():
    fake = FakeLangfuse()
    observability.reset_for_tests(fake)
    try:
        result = run_agent("What share of revenue is R&D?", ScriptedModel(_gather() + [_final(GOOD)]), FakeSec())
    finally:
        observability.reset_for_tests(None)
    assert result.status == "answered"
    assert result.langfuse_trace_id == "trace-1"
    root = fake.named("research-agent")[0]
    assert root["as_type"] == "agent"
    generations = [o for o in fake.observations if o["as_type"] == "generation"]
    assert len(generations) == result.model_calls
    assert all("usage_details" in g["updates"][0] for g in generations)
    tools = [o for o in fake.observations if o["as_type"] == "tool"]
    assert len(tools) == result.tool_calls
    assert fake.named("verify-answer")[0]["as_type"] == "evaluator"
    assert {s["name"] for s in root["trace_scores"]} >= {"status", "verified_claims", "failed_claims", "cost_usd"}


def test_agent_without_tracing_has_no_trace_id():
    result = run_agent("What share of revenue is R&D?", ScriptedModel(_gather() + [_final(GOOD)]), FakeSec())
    assert result.status == "answered" and result.langfuse_trace_id is None
