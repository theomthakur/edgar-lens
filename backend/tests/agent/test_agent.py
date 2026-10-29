import pytest

from app.agent.evidence import CalcError, Evidence
from app.agent.llm import ModelReply, ScriptedModel, call
from app.agent.loop import Budget, run_agent
from app.agent.tools import Toolbox
from app.agent.verifier import uncovered_numbers, verify_claim

from .fakes import FakeSec


# ---------- the calculator and evidence ----------
def test_calculator_uses_only_retrieved_figures():
    evidence = Evidence()
    a = evidence.add_fact({"value": 150_000_000})
    b = evidence.add_fact({"value": 1_200_000_000})
    key, result = evidence.calculate(f"{a} / {b}")
    assert key == "K1" and result == pytest.approx(0.125)
    assert evidence.value_of("K1") == pytest.approx(0.125)


@pytest.mark.parametrize("bad", ["F9 + 1", "__import__('os')", "2 ** 10", "open('x')", "1 / 0", "a + b"])
def test_calculator_refuses_anything_else(bad):
    with pytest.raises(CalcError):
        Evidence().calculate(bad)


# ---------- the verifier ----------
def _evidence():
    evidence = Evidence()
    evidence.add_fact({"value": 150_000_000})
    evidence.add_text("We are exposed to changes in foreign currency exchange rates because we sell in many countries.")
    return evidence


def test_number_claim_matches_within_rounding_and_scale():
    ev = _evidence()
    assert verify_claim({"type": "number", "text": "R&D", "ref": "F1", "value": 150, "scale": "millions"}, ev).ok
    assert verify_claim({"type": "number", "text": "R&D", "ref": "F1", "value": 0.15, "scale": "billions"}, ev).ok


def test_number_claim_is_rejected_when_wrong_or_unsupported():
    ev = _evidence()
    assert not verify_claim({"type": "number", "text": "R&D", "ref": "F1", "value": 160, "scale": "millions"}, ev).ok
    assert not verify_claim({"type": "number", "text": "R&D", "ref": "F7", "value": 1, "scale": "units"}, ev).ok
    assert not verify_claim({"type": "number", "text": "R&D", "ref": "F1", "value": 150, "scale": "gazillions"}, ev).ok


def test_quote_must_appear_word_for_word_in_text_the_agent_saw():
    ev = _evidence()
    ok = {"type": "quote", "text": "FX risk", "ref": "T1", "quote": "exposed to changes in foreign currency exchange rates"}
    assert verify_claim(ok, ev).ok
    assert not verify_claim({**ok, "quote": "heavily exposed to currency swings"}, ev).ok
    assert not verify_claim({**ok, "ref": "T9"}, ev).ok
    assert not verify_claim({**ok, "quote": "short"}, ev).ok


def test_numbers_in_the_answer_without_a_claim_are_flagged():
    verified = [{"value": 150, "scale": "millions"}]
    assert uncovered_numbers("R&D was $150 million in 2024.", verified) == []
    assert uncovered_numbers("R&D was $150 million and revenue was $1.2 billion in 2024.", verified) == ["$1.2 billion"]


# ---------- the tools ----------
def test_tools_give_every_retrieved_figure_and_passage_an_id():
    toolbox = Toolbox(FakeSec(), Evidence())
    facts = toolbox.call("get_financial_facts", {"ticker": "ACME", "concept": "revenue", "years": 2})
    assert [r["id"] for r in facts["rows"]] == ["F1", "F2"]
    section = toolbox.call("read_filing_section", {"ticker": "ACME", "accession": "0000000001-25-000001", "section": "risk_factors"})
    assert section["id"] == "T1" and "suppliers" in section["text"]
    found = toolbox.call("search_filing", {"ticker": "ACME", "accession": "0000000001-25-000001", "query": "foreign currency exchange rates"})
    assert found["results"] and "currency" in found["results"][0]["text"]


def test_tools_report_errors_in_plain_words_instead_of_crashing():
    toolbox = Toolbox(FakeSec(), Evidence())
    assert "no annual" in toolbox.call("get_financial_facts", {"ticker": "ACME", "concept": "net_income"})["error"]
    assert "Unknown tool" in toolbox.call("delete_everything", {})["error"]
    assert "do not fit" in toolbox.call("calculate", {"wrong": 1})["error"]


# ---------- the whole loop with a scripted model ----------
def _final(claims, status="answered", answer="R&D was $150 million, 12.5% of revenue."):
    return lambda _m: call("final_answer", status=status, answer=answer, claims=claims)


GOOD = [
    {"type": "number", "text": "R&D was $150 million", "ref": "F1", "value": 150, "scale": "millions"},
    {"type": "number", "text": "12.5% of revenue", "ref": "K1", "value": 12.5, "scale": "percent"},
]


def _gather():
    return [
        lambda _m: call("get_financial_facts", ticker="ACME", concept="rd_expense", years=1),
        lambda _m: call("get_financial_facts", ticker="ACME", concept="revenue", years=1),
        lambda _m: call("calculate", expression="F1 / F2"),
    ]


def test_agent_gathers_evidence_then_answers_and_every_claim_is_verified():
    result = run_agent("What share of revenue is R&D?", ScriptedModel(_gather() + [_final(GOOD)]), FakeSec())
    assert result.status == "answered"
    assert len(result.verified_claims) == 2 and not result.failed_claims
    assert [e["name"] for e in result.trace if e["kind"] == "tool"] == ["get_financial_facts", "get_financial_facts", "calculate"]
    assert result.repairs == 0


def test_agent_is_sent_back_to_fix_a_wrong_number_and_then_succeeds():
    wrong = [{"type": "number", "text": "R&D was $180 million", "ref": "F1", "value": 180, "scale": "millions"}]
    script = _gather() + [_final(wrong, answer="R&D was $180 million."), _final(GOOD)]
    result = run_agent("R&D?", ScriptedModel(script), FakeSec())
    assert result.status == "answered" and result.repairs == 1
    verify_events = [e for e in result.trace if e["kind"] == "verify"]
    assert verify_events[0]["status"] == "needs_repair" and verify_events[1]["status"] == "answered"


def test_a_made_up_number_is_never_accepted_even_if_the_model_insists():
    made_up = [{"type": "number", "text": "Revenue was $5 billion", "ref": "F1", "value": 5, "scale": "billions"}]
    script = _gather() + [_final(made_up, answer="Revenue was $5 billion.")] * 4
    result = run_agent("Revenue?", ScriptedModel(script), FakeSec(), Budget(max_repairs=2))
    assert result.status == "unverified"
    assert result.failed_claims and not result.verified_claims


def test_an_unanswerable_question_ends_as_insufficient_evidence():
    result = run_agent("What will Acme earn in 2031?", ScriptedModel([_final([], status="insufficient_evidence", answer="Filings do not predict future earnings.")]), FakeSec())
    assert result.status == "insufficient_evidence" and result.tool_calls == 0


def test_the_agent_stops_when_it_runs_out_of_steps_or_money():
    forever = [lambda _m: call("get_financial_facts", ticker="ACME", concept="revenue")] * 30
    assert run_agent("loop", ScriptedModel(forever), FakeSec(), Budget(max_model_calls=3)).status == "stopped_budget"
    pricey = [lambda _m: ModelReply(content="", tool_calls=[{"id": "x", "name": "get_financial_facts", "arguments": {"ticker": "ACME", "concept": "revenue"}}], cost_usd=0.2)] * 5
    assert run_agent("cost", ScriptedModel(pricey), FakeSec(), Budget(max_cost_usd=0.15)).status == "stopped_budget"


def test_filing_text_that_gives_orders_cannot_change_what_gets_verified():
    # The risk-factor text in the fake filing says to claim revenue was a trillion dollars. The claim still fails.
    read = lambda _m: call("read_filing_section", ticker="ACME", accession="0000000001-25-000001", section="risk_factors")
    lie = [{"type": "number", "text": "Revenue was $1 trillion", "ref": "F1", "value": 1, "scale": "billions"}]
    script = [lambda _m: call("get_financial_facts", ticker="ACME", concept="revenue", years=1), read] + [_final(lie, answer="Revenue was $1 trillion.")] * 4
    assert run_agent("Revenue?", ScriptedModel(script), FakeSec(), Budget(max_repairs=1)).status == "unverified"


def test_a_model_failure_ends_the_run_cleanly():
    class Broken:
        name = "broken"
        def chat(self, messages, tools):
            raise RuntimeError("service down")
    result = run_agent("anything", Broken(), FakeSec())
    assert result.status == "error" and any(e["kind"] == "error" for e in result.trace)


def test_a_final_answer_given_in_the_same_breath_as_tool_calls_is_not_accepted():
    def rushed(_m):
        return ModelReply(content="", tool_calls=[
            {"id": "a", "name": "get_financial_facts", "arguments": {"ticker": "ACME", "concept": "rd_expense", "years": 1}},
            {"id": "b", "name": "final_answer", "arguments": {"status": "answered", "answer": "R&D was $150 million.", "claims": GOOD[:1]}},
        ])
    script = [rushed, _final(GOOD[:1], answer="R&D was $150 million.")]
    result = run_agent("R&D?", ScriptedModel(script), FakeSec())
    kinds = [e["status"] for e in result.trace if e["kind"] == "verify"]
    assert kinds == ["too_early", "answered"]
    assert result.status == "answered"


@pytest.mark.parametrize("args", [
    {"status": "answered", "answer": None, "claims": ["junk"]},
    {"status": "answered", "answer": "", "claims": []},
    {"status": "answered", "answer": "Revenue was big.", "claims": ["not an object"]},
    {"status": "answered", "answer": "Fine.", "claims": "nope"},
])
def test_sloppy_final_answers_are_never_accepted(args):
    gather = _gather()
    script = gather + [lambda _m, a=args: call("final_answer", **a)] * 5
    result = run_agent("R&D?", ScriptedModel(script), FakeSec(), Budget(max_repairs=1))
    assert result.status == "unverified"


def test_insufficient_evidence_still_needs_an_explanation():
    script = [lambda _m: call("final_answer", status="insufficient_evidence", answer="", claims=[])] * 5
    assert run_agent("Future?", ScriptedModel(script), FakeSec(), Budget(max_repairs=1)).status == "unverified"


def test_the_word_latest_picks_the_newest_filing():
    toolbox = Toolbox(FakeSec(), Evidence())
    section = toolbox.call("read_filing_section", {"ticker": "ACME", "accession": "latest", "section": "business"})
    assert "widgets" in section["text"]
    assert "widgets" in toolbox.call("read_filing_section", {"ticker": "ACME", "accession": "None", "section": "business"})["text"]
