"""Thin LLM client. Anthropic API first; any object with the same two methods can replace it
(tests use a scripted fake; Bedrock or Vertex AI clients can be dropped in later)."""
from __future__ import annotations

import os
import time
from typing import Protocol


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    def json(self, *, step: str, system: str, user: str, tool: dict, model: str | None = None) -> tuple[dict, dict]: ...
    def text(self, *, step: str, system: str, user: str, model: str | None = None) -> tuple[str, dict]: ...


class AnthropicLLM:
    """Structured output via a strict tool with tool_choice left on auto, which works on
    every current Claude model (forcing a named tool is rejected on some models)."""

    def __init__(self, model: str | None = None, planner_model: str | None = None, max_tokens: int = 4096):
        import anthropic  # imported here so tests and the engine run without the SDK configured

        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model or os.getenv("PUMFAI_MODEL", "claude-haiku-5-5")
        self.planner_model = planner_model or os.getenv("PUMFAI_PLANNER_MODEL", self.model)
        self.max_tokens = max_tokens

    def _model_for(self, step: str, model: str | None) -> str:
        return model or (self.planner_model if step == "planner" else self.model)

    def json(self, *, step, system, user, tool, model=None):
        m = self._model_for(step, model)
        messages = [{"role": "user", "content": user}]
        for attempt in range(2):
            t0 = time.perf_counter()
            resp = self.client.messages.create(model=m, max_tokens=self.max_tokens, system=system,
                                               tools=[tool], tool_choice={"type": "auto"}, messages=messages)
            meta = self._meta(resp, m, t0, step)
            block = next((b for b in resp.content if b.type == "tool_use" and b.name == tool["name"]), None)
            if block is not None:
                return dict(block.input), meta
            messages = messages + [{"role": "assistant", "content": resp.content},
                                   {"role": "user", "content": f"Reply only by calling the {tool['name']} tool."}]
        raise LLMError(f"{step}: model did not call {tool['name']}")

    def text(self, *, step, system, user, model=None):
        m = self._model_for(step, model)
        t0 = time.perf_counter()
        resp = self.client.messages.create(model=m, max_tokens=self.max_tokens, system=system,
                                           messages=[{"role": "user", "content": user}])
        out = "".join(b.text for b in resp.content if b.type == "text").strip()
        return out, self._meta(resp, m, t0, step)

    @staticmethod
    def _meta(resp, model, t0, step) -> dict:
        u = getattr(resp, "usage", None)
        return {"step": step, "model": model, "ms": round((time.perf_counter() - t0) * 1000),
                "input_tokens": getattr(u, "input_tokens", None), "output_tokens": getattr(u, "output_tokens", None)}
