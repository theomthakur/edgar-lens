"""Settings come from the environment, so the same code runs against OpenRouter, OpenAI or a local model."""
from __future__ import annotations

import os
from pathlib import Path

from .llm import OpenAICompatibleModel
from .sec import SecClient

CACHE = Path(__file__).resolve().parents[2] / ".cache" / "sec"


def sec_from_env() -> SecClient:
    return SecClient(os.environ.get("SEC_USER_AGENT", ""), cache_dir=CACHE)


def model_from_env(model: str | None = None) -> OpenAICompatibleModel:
    return OpenAICompatibleModel(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        model=model or os.environ.get("LLM_MODEL", "llama3.2"),
        api_key=os.environ.get("LLM_API_KEY", ""),
    )
