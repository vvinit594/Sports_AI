"""Provider-independent LLM interface."""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    name: str
    model_name: str

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        """Return a JSON object string. Must not invent match statistics."""
        ...
