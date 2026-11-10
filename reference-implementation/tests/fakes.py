"""Scripted LLMs for tests. They exercise the plumbing, not model quality."""
from __future__ import annotations

import re


class OracleLLM:
    """Answers each step from a golden item's expected spec, as a perfect model would."""

    def __init__(self, golden: list[dict], release: dict, narrative: str | None = None):
        self.by_q = {g["question"]: g["expected"] for g in golden}
        self.release = release
        self.narrative = narrative
        self.calls = []

    def _exp(self, user):
        for q, e in self.by_q.items():
            if q in user:
                return e
        raise KeyError(user[:80])

    def json(self, *, step, system, user, tool, model=None):
        self.calls.append(step)
        e = self._exp(user)
        meta = {"step": step, "model": "oracle"}
        if step == "intent":
            if e["status"] != "answered":
                return {"answerable": False, "reason_if_not": "not in this survey", "question_type": "other",
                        "measures": [], "population_filters": [], "breakdown": ""}, meta
            return {"answerable": True, "reason_if_not": "", "question_type": "share", "measures": list(e["rows"]),
                    "population_filters": list(e["base"]), "breakdown": e["columns"][0] if e["columns"] else ""}, meta
        if step == "rerank":
            phrases = re.findall(r'"phrase": "([^"]+)",\s*"role": "(\w+)"', user)
            return {"selections": [{"phrase": p, "role": r, "code": p, "confidence": 0.95, "alternatives": []}
                                   for p, r in phrases]}, meta
        if step == "planner":
            conds = [{"var": v, "in": vals} for v, vals in e["base"].items()]
            spec = {"spec_version": "1.0", "survey": self.release["survey"], "release_id": self.release["release_id"],
                    "base": {"all": conds} if conds else None, "rows": [{"var": r} for r in e["rows"]],
                    "weight": self.release["weight_code"], "measures": ["col_pct"], "missing": "exclude"}
            if e["columns"]:
                spec["columns"] = [{"var": e["columns"][0]}]
            if not conds:
                spec.pop("base")
            return spec, meta
        raise ValueError(step)

    def text(self, *, step, system, user, model=None):
        self.calls.append(step)
        if self.narrative is not None:
            return self.narrative, {"step": step, "model": "oracle"}
        m = re.search(r": (\d+\.\d)% \(", user)
        return f"In this synthetic release, {m.group(1)}% of the base said yes.", {"step": step, "model": "oracle"}


class ScriptedLLM:
    """Returns queued responses per step, in order."""

    def __init__(self, **queues):
        self.queues = {k: list(v) for k, v in queues.items()}
        self.calls = []

    def json(self, *, step, system, user, tool, model=None):
        self.calls.append((step, user))
        return self.queues[step].pop(0), {"step": step, "model": "scripted"}

    def text(self, *, step, system, user, model=None):
        self.calls.append((step, user))
        return self.queues[step].pop(0), {"step": step, "model": "scripted"}
