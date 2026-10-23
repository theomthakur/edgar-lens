"""Talk to any OpenAI-compatible chat model (OpenRouter, OpenAI, a local Ollama). Swapping models is configuration."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import httpx


@dataclass
class ModelReply:
    content: str
    tool_calls: list[dict]            # [{"id", "name", "arguments": dict}]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0
    raw_message: dict = field(default_factory=dict)


class ChatModel(Protocol):
    name: str

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelReply: ...


class OpenAICompatibleModel:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 90.0, temperature: float = 0.0):
        self.base_url = base_url.rstrip("/")
        self.name = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelReply:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body: dict[str, Any] = {"model": self.name, "messages": messages, "tools": tools, "temperature": self.temperature}
        if "openrouter.ai" in self.base_url:
            body["usage"] = {"include": True}  # ask OpenRouter to report the real cost
        started = time.monotonic()
        response = httpx.post(f"{self.base_url}/chat/completions", headers=headers, json=body, timeout=self.timeout)
        seconds = time.monotonic() - started
        if response.status_code != 200:
            raise RuntimeError(f"The model service returned {response.status_code}: {response.text[:200]}")
        data = response.json()
        message = data["choices"][0]["message"]
        calls = []
        for call in message.get("tool_calls") or []:
            raw_args = call["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                args = {"_unparsed": raw_args}
            calls.append({"id": call.get("id") or f"call_{len(calls)}", "name": call["function"]["name"], "arguments": args})
        usage = data.get("usage") or {}
        return ModelReply(
            content=message.get("content") or "",
            tool_calls=calls,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            cost_usd=float(usage.get("cost") or 0.0),
            seconds=seconds,
            raw_message=message,
        )


class ScriptedModel:
    """A stand-in model for tests. Each step is a function that sees the conversation and returns what to do next."""

    name = "scripted"

    def __init__(self, steps: list[Callable[[list[dict]], ModelReply]]):
        self.steps = list(steps)

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelReply:
        if not self.steps:
            return ModelReply(content="(script ended)", tool_calls=[])
        return self.steps.pop(0)(messages)


def call(name: str, **arguments: Any) -> ModelReply:
    """Shorthand for a scripted tool call."""
    return ModelReply(content="", tool_calls=[{"id": f"c_{name}", "name": name, "arguments": arguments}])
