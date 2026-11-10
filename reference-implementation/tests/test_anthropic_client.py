"""Exercise AnthropicLLM through the real SDK with a mocked HTTP transport (no network, no key)."""
import json

import pytest

try:  # newer anthropic SDKs use httpx2; older ones use httpx
    import httpx2 as httpx
except ImportError:
    import httpx

from pumfai import prompts
from pumfai.llm import AnthropicLLM, LLMError


def _client(responses, seen):
    import anthropic

    def handler(request: httpx.Request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=responses.pop(0))

    return anthropic.Anthropic(api_key="test", base_url="https://mock.local",
                               http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def _msg(content, stop="end_turn"):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
            "content": content, "stop_reason": stop, "stop_sequence": None,
            "usage": {"input_tokens": 120, "output_tokens": 30}}


def _llm(responses, seen):
    llm = AnthropicLLM.__new__(AnthropicLLM)
    llm.client = _client(responses, seen)
    llm.model, llm.planner_model, llm.max_tokens = "claude-haiku-5-5", "claude-sonnet-5-5", 1024
    return llm


def test_json_step_sends_strict_tool_and_reads_tool_use():
    seen = []
    intent = {"answerable": True, "reason_if_not": "", "question_type": "share", "measures": ["podcasts"],
              "population_filters": ["Ontario"], "breakdown": ""}
    llm = _llm([_msg([{"type": "tool_use", "id": "tu_1", "name": "record_intent", "input": intent}], "tool_use")], seen)
    out, meta = llm.json(step="intent", system="s", user="q", tool=prompts.INTENT_TOOL)
    assert out == intent
    body = seen[0]
    assert body["model"] == "claude-haiku-5-5"
    assert body["tool_choice"] == {"type": "auto"}
    assert body["tools"][0]["strict"] is True
    assert "temperature" not in body
    assert meta["input_tokens"] == 120


def test_planner_uses_planner_model_and_retries_when_no_tool_call():
    seen = []
    spec = {"rows": [{"var": "ac_pod"}]}
    llm = _llm([_msg([{"type": "text", "text": "Here is my plan."}]),
                _msg([{"type": "tool_use", "id": "tu_2", "name": "emit_query_spec", "input": spec}], "tool_use")], seen)
    out, _ = llm.json(step="planner", system="s", user="q", tool=prompts.planner_tool())
    assert out == spec
    assert seen[0]["model"] == "claude-sonnet-5-5"
    assert "emit_query_spec tool" in seen[1]["messages"][-1]["content"]


def test_gives_up_after_two_attempts_without_tool_call():
    seen = []
    llm = _llm([_msg([{"type": "text", "text": "no"}]), _msg([{"type": "text", "text": "still no"}])], seen)
    with pytest.raises(LLMError):
        llm.json(step="intent", system="s", user="q", tool=prompts.INTENT_TOOL)


def test_text_step_joins_text_blocks():
    seen = []
    llm = _llm([_msg([{"type": "text", "text": "31.9% listen."}])], seen)
    out, _ = llm.text(step="narrator", system="s", user="q")
    assert out == "31.9% listen."
