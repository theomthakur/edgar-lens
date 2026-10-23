from app.agent.evaluate import Task, score, summarize
from app.agent.loop import RunResult


def _result(status, claims=(), **extra):
    return RunResult(question="q", model="m", status=status, verified_claims=list(claims), **extra)


def test_a_lookup_is_correct_only_when_a_verified_number_matches_the_truth():
    task = Task("t", "lookup", "q", truth=391_035_000_000)
    good = _result("answered", [{"type": "number", "value": 391.035, "scale": "billions", "ref": "F1"}])
    off = _result("answered", [{"type": "number", "value": 380, "scale": "billions", "ref": "F1"}])
    assert score(task, good)["correct"] and not score(task, good)["wrong_but_answered"]
    assert not score(task, off)["correct"] and score(task, off)["wrong_but_answered"]


def test_a_ratio_is_graded_in_percentage_points_not_relative_size():
    task = Task("t", "ratio", "q", truth=0.2397, tolerance=0.001, absolute=True)
    assert score(task, _result("answered", [{"type": "number", "value": 24.0, "scale": "percent", "ref": "K1"}]))["correct"]
    assert not score(task, _result("answered", [{"type": "number", "value": 25.0, "scale": "percent", "ref": "K1"}]))["correct"]


def test_refusing_an_unanswerable_question_counts_as_right_and_guessing_does_not():
    task = Task("t", "refuse", "q")
    assert score(task, _result("insufficient_evidence"))["correct"]
    assert score(task, _result("answered"))["wrong_but_answered"]


def test_a_quote_task_needs_a_verified_quote():
    task = Task("t", "quote", "q")
    assert score(task, _result("answered", [{"type": "quote", "ref": "T1"}]))["correct"]
    assert not score(task, _result("answered", [{"type": "number", "ref": "F1", "value": 1, "scale": "units"}]))["correct"]


def test_summary_reports_the_numbers_that_matter():
    rows = [
        {"kind": "lookup", "correct": True, "wrong_but_answered": False, "repairs": 0, "model_calls": 4, "seconds": 10, "cost_usd": 0.01},
        {"kind": "lookup", "correct": False, "wrong_but_answered": True, "repairs": 1, "model_calls": 6, "seconds": 20, "cost_usd": 0.03},
        {"kind": "refuse", "correct": True, "wrong_but_answered": False, "repairs": 0, "model_calls": 1, "seconds": 2, "cost_usd": 0.0},
    ]
    s = summarize(rows)
    assert s["tasks"] == 3 and s["correct_pct"] == 66.7 and s["wrong_but_answered_pct"] == 33.3
    assert s["refused_correctly_pct"] == 100.0 and s["answerable_correct_pct"] == 50.0
