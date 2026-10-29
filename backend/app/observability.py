"""Optional Langfuse tracing.

Tracing is on only when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set (plus LANGFUSE_HOST for a
self-hosted or non-default region). Without them every helper here is a no-op, so the app behaves exactly
as before. A tracing failure never breaks a request: errors from the SDK are swallowed and the work runs.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

_client: Any = None
_checked = False


def enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def client() -> Any:
    global _client, _checked
    if not _checked:
        _checked = True
        if enabled():
            try:
                from langfuse import get_client

                _client = get_client()
            except Exception:  # noqa: BLE001 - missing package or bad config must not break the app
                _client = None
    return _client


def reset_for_tests(fake_client: Any = None) -> None:
    global _client, _checked
    _client = fake_client
    _checked = fake_client is not None


class _NullObservation:
    def update(self, **_: Any) -> "_NullObservation":
        return self

    def score(self, **_: Any) -> None:
        return None

    def score_trace(self, **_: Any) -> None:
        return None


@contextmanager
def observe(name: str, as_type: str = "span", **kwargs: Any) -> Iterator[Any]:
    """Open a Langfuse observation that nests under whatever observation is current."""
    lf = client()
    if lf is None:
        yield _NullObservation()
        return
    try:
        manager = lf.start_as_current_observation(name=name, as_type=as_type, **kwargs)
        observation = manager.__enter__()
    except Exception:  # noqa: BLE001
        yield _NullObservation()
        return
    try:
        yield observation
    except BaseException as error:
        manager.__exit__(type(error), error, error.__traceback__)
        raise
    else:
        manager.__exit__(None, None, None)


@contextmanager
def trace_attributes(**kwargs: Any) -> Iterator[None]:
    """Set trace-level tags, name, metadata or session on everything opened inside (a no-op when tracing is off)."""
    if client() is None:
        yield
        return
    try:
        from langfuse import propagate_attributes

        manager = propagate_attributes(**kwargs)
        manager.__enter__()
    except Exception:  # noqa: BLE001
        yield
        return
    try:
        yield
    except BaseException as error:
        manager.__exit__(type(error), error, error.__traceback__)
        raise
    else:
        manager.__exit__(None, None, None)


def current_trace_id() -> str | None:
    lf = client()
    if lf is None:
        return None
    try:
        return lf.get_current_trace_id()
    except Exception:  # noqa: BLE001
        return None


def score_trace(trace_id: str | None, name: str, value: float | str, comment: str | None = None) -> None:
    lf = client()
    if lf is None or not trace_id:
        return
    try:
        lf.create_score(trace_id=trace_id, name=name, value=value, comment=comment)
    except Exception:  # noqa: BLE001
        return


def flush() -> None:
    lf = client()
    if lf is None:
        return
    try:
        lf.flush()
    except Exception:  # noqa: BLE001
        return
