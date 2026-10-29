"""A stand-in for the Langfuse client that records what would have been sent."""
from __future__ import annotations

from contextlib import contextmanager


class FakeObservation:
    def __init__(self, record: dict):
        self.record = record

    def update(self, **kwargs):
        self.record.setdefault("updates", []).append(kwargs)
        return self

    def score(self, **kwargs):
        self.record.setdefault("scores", []).append(kwargs)

    def score_trace(self, **kwargs):
        self.record.setdefault("trace_scores", []).append(kwargs)


class FakeLangfuse:
    def __init__(self):
        self.observations: list[dict] = []
        self.scores: list[dict] = []
        self._stack: list[dict] = []

    @contextmanager
    def start_as_current_observation(self, *, name, as_type="span", **kwargs):
        record = {"name": name, "as_type": as_type, "parent": self._stack[-1]["name"] if self._stack else None, **kwargs}
        self.observations.append(record)
        self._stack.append(record)
        try:
            yield FakeObservation(record)
        finally:
            self._stack.pop()

    def get_current_trace_id(self):
        return "trace-1" if self._stack else None

    def create_score(self, **kwargs):
        self.scores.append(kwargs)

    def flush(self):
        pass

    def named(self, name):
        return [o for o in self.observations if o["name"] == name]
