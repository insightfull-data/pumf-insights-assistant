"""Question -> intent -> variables -> spec -> table -> guarded narrative.

Mirrors the runtime path in docs/data-architecture.md section 8. The LLM never sees
microdata and never produces a number; the number checker enforces the second rule.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import prompts
from .catalog import Catalog
from .checker import check, suppressed_leak
from .engine import Engine
from .llm import LLM
from .render import markdown, narrator_facts, pct
from .spec import SpecError, validate

CLARIFY_BELOW = 0.55
MEASURES = ["weighted_count", "col_pct", "index", "unweighted_n", "cv"]


class Pipeline:
    def __init__(self, engine: Engine, llm: LLM, log_dir: Path | None = None):
        self.engine = engine
        self.catalog: Catalog = engine.catalog
        self.llm = llm
        self.log_dir = Path(log_dir) if log_dir else None
        rel = self.catalog.release
        provinces = [v["code"] for v in self.catalog.valid_values("h_province")] if self.catalog.get("h_province") else []
        self.default_base = {"all": [{"var": "h_province", "in": provinces}]}

    # ------------------------------------------------------------------ main entry
    def ask(self, question: str, choices: dict[str, str] | None = None) -> dict:
        t0 = time.perf_counter()
        trace: dict = {"prompt_version": prompts.PROMPT_VERSION, "llm_calls": []}
        out = {"answer_id": str(uuid.uuid4()), "question": question, "release_id": self.catalog.release["release_id"]}
        try:
            res = self._run(question, choices or {}, trace)
        except SpecError as e:
            res = {"status": "error", "message": "Could not build a valid query.", "errors": e.errors}
        out.update(res)
        out["trace"] = trace
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        self._log(out)
        return out

    def _run(self, question, choices, trace) -> dict:
        rel = self.catalog.release
        # 1. intent
        intent, meta = self.llm.json(step="intent", tool=prompts.INTENT_TOOL, user=question,
                                     system=prompts.INTENT_SYSTEM.format(**rel))
        trace["llm_calls"].append(meta)
        trace["intent"] = intent
        if not intent.get("answerable", True):
            return {"status": "unsupported", "message": intent.get("reason_if_not") or "This survey cannot answer that question."}
        phrases = ([(p, "measure") for p in intent.get("measures", [])]
                   + [(p, "filter") for p in intent.get("population_filters", [])]
                   + ([(intent["breakdown"], "breakdown")] if intent.get("breakdown") else []))
        if not any(r == "measure" for _, r in phrases):
            return {"status": "unsupported", "message": "I could not find anything to measure in the question."}

        # 2. variable resolution: keyword search, then LLM rerank
        candidates = {p: self.catalog.search(p, k=8) for p, _ in phrases}
        trace["candidates"] = candidates
        cand_text = []
        for p, role in phrases:
            cards = [self.catalog.card(c["code"]) for c in candidates[p]]
            cand_text.append({"phrase": p, "role": role, "candidates": cards})
        sel, meta = self.llm.json(step="rerank", tool=prompts.RERANK_TOOL, system=prompts.RERANK_SYSTEM,
                                  user="Question: " + question + "\n\n" + json.dumps(cand_text, indent=1))
        trace["llm_calls"].append(meta)
        selections = {s["phrase"]: s for s in sel.get("selections", [])}
        trace["selections"] = selections

        chosen, ask_back = {}, []
        for p, role in phrases:
            if p in choices:
                chosen[p] = (choices[p], role)
                continue
            s = selections.get(p)
            code = s["code"] if s else ""
            if not code or self.catalog.get(code) is None or s["confidence"] < CLARIFY_BELOW:
                opts = ([code] if code and self.catalog.get(code) else []) + (s["alternatives"] if s else []) + [c["code"] for c in candidates[p]]
                opts = [o for i, o in enumerate(opts) if self.catalog.get(o) and o not in opts[:i]][:4]
                if not opts:
                    if role == "measure":
                        return {"status": "unsupported", "message": f"The survey has no variable for '{p}'."}
                    continue
                ask_back.append({"phrase": p, "role": role,
                                 "options": [{"code": o, "label": self.catalog.get(o)["label"]} for o in opts]})
            else:
                chosen[p] = (code, role)
        if ask_back:
            return {"status": "clarify", "message": "Which of these did you mean?", "clarify": ask_back}

        # 3. planner -> validated spec
        cards = {code: self.catalog.card(code) | {"universe_expr": self.catalog.get(code).get("universe_expr")}
                 for code, _ in chosen.values()}
        plan_user = json.dumps({"question": question, "intent": intent,
                                "chosen": [{"phrase": p, "role": r, "code": c} for p, (c, r) in chosen.items()],
                                "variables": cards}, indent=1)
        system = prompts.PLANNER_SYSTEM.format(release_id=rel["release_id"], survey=rel["survey"],
                                               weight=rel["weight_code"], default_base=json.dumps(self.default_base))
        spec, meta = self.llm.json(step="planner", tool=prompts.planner_tool(), system=system, user=plan_user)
        trace["llm_calls"].append(meta)
        spec = self._normalize(spec)
        try:
            validate(spec, self.catalog)
        except SpecError as e:
            trace["spec_errors_first_try"] = e.errors
            spec, meta = self.llm.json(step="planner", tool=prompts.planner_tool(), system=system,
                                       user=plan_user + "\n\nYour previous spec was rejected:\n- " + "\n- ".join(e.errors)
                                       + "\nFix these problems.")
            trace["llm_calls"].append(meta)
            spec = self._normalize(spec)
            validate(spec, self.catalog)
        trace["spec"] = spec

        # 4. deterministic tabulation + reliability guard (inside the engine)
        result = self.engine.tabulate(spec)

        # 5. narrator + number checker
        facts = narrator_facts(result)
        narrative, problems = "", []
        for attempt in range(2):
            user = prompts.narrator_user(question, facts)
            if problems:
                user += "\n\nYour previous answer used numbers not in the facts: " + "; ".join(problems) + ". Rewrite it."
            narrative, meta = self.llm.text(step="narrator", system=prompts.NARRATOR_SYSTEM, user=user)
            trace["llm_calls"].append(meta)
            problems = check(narrative, result, extra_text=question)
            if suppressed_leak(narrative, result):
                problems.append("appears to estimate a suppressed value")
            if not problems:
                break
        trace["checker"] = {"passed": not problems, "problems": problems}
        if problems:
            narrative = fallback_narrative(result)
            trace["checker"]["fallback"] = True
        return {"status": "answered", "answer": narrative, "table_markdown": markdown(result),
                "spec": spec, "result": result}

    def _normalize(self, spec: dict) -> dict:
        rel = self.catalog.release
        spec = dict(spec)
        spec.setdefault("spec_version", "1.0")
        spec.setdefault("survey", rel["survey"])
        spec.setdefault("release_id", rel["release_id"])
        spec.setdefault("weight", rel["weight_code"])
        spec.setdefault("missing", "exclude")
        spec["measures"] = MEASURES
        if not spec.get("base"):
            spec["base"] = self.default_base
        if spec.get("columns") == []:
            spec.pop("columns")
        return spec

    def _log(self, out: dict):
        if not self.log_dir:
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        rec = {k: v for k, v in out.items() if k not in ("result", "table_markdown")}
        rec["ts"] = datetime.now(timezone.utc).isoformat()
        with open(self.log_dir / "answers.jsonl", "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")


def fallback_narrative(result: dict) -> str:
    """Deterministic answer used when the narrator fails the number check twice."""
    parts = []
    for block in result["rows"]:
        bits = []
        for v in block["values"]:
            c = v["cells"]["total"]
            if c["flag"] == "F":
                bits.append(f"{v['label']}: too unreliable to report")
            else:
                bits.append(f"{v['label']}: {pct(c['col_pct']):.1f}%" + (" (use with caution)" if c["flag"] == "E" else ""))
        parts.append(f"{block['label']} ({block['universe']}): " + "; ".join(bits) + ".")
    return " ".join(parts) + " See the table for the full breakdown."
