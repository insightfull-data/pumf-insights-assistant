"""Golden-set evaluation (governance gate G2 / G4).

For each golden question the pipeline runs end to end. When it asks to clarify, the
evaluator answers with the expected variable if offered (and counts the clarification).
Scores: status accuracy, row/column/base match, exact spec match, number-checker pass rate.

Equivalences: a base condition that lists every valid code of a variable is treated as
no condition; source variables and their harmonized versions (province <-> h_province)
are compared after mapping codes through the steward crosswalk.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .engine import Engine
from .spec import filter_vars

GOLDEN = config.ROOT / "golden" / "questions.jsonl"


def load_golden(path: Path = GOLDEN) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _crosswalk(catalog) -> dict:
    overlay_path = config.raw_dir() / "steward_overlay.json"
    if not overlay_path.exists():
        return {}
    harm = json.loads(overlay_path.read_text()).get("harmonized", {})
    return {spec["source"]: (h, spec["map"]) for h, spec in harm.items()}


def base_conditions(spec: dict, catalog, xwalk: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for var, cond in filter_vars(spec.get("base")):
        vals = {str(v) for v in (cond.get("in") or ([cond["eq"]] if "eq" in cond else []))}
        if var in xwalk:
            h, mp = xwalk[var]
            var, vals = h, {mp.get(v, v) for v in vals}
        if catalog.get(var) and vals >= {x["code"] for x in catalog.valid_values(var)}:
            continue  # covers everyone: equivalent to no filter
        out[var] = out.get(var, set()) | vals
    return out


def norm_vars(codes, xwalk) -> set[str]:
    return {xwalk[c][0] if c in xwalk else c for c in codes}


def score(item: dict, out: dict, catalog, xwalk) -> dict:
    exp = item["expected"]
    s = {"id": item["id"], "status": out["status"], "status_ok": out["status"] == exp["status"],
         "clarified": out.get("_clarified", 0)}
    if exp["status"] != "answered" or out["status"] != "answered":
        s.update(rows_ok=None, columns_ok=None, base_ok=None, exact=s["status_ok"] and exp["status"] != "answered")
        return s
    spec = out["spec"]
    rows = norm_vars([r["var"] for r in spec["rows"]], xwalk)
    cols = norm_vars([c["var"] for c in spec.get("columns", [])], xwalk)
    base = base_conditions(spec, catalog, xwalk)
    exp_base = {k: set(v) for k, v in exp["base"].items()}
    s.update(rows_ok=rows == set(exp["rows"]), columns_ok=cols == set(exp["columns"]), base_ok=base == exp_base,
             row_recall=len(rows & set(exp["rows"])) / len(exp["rows"]),
             checker_passed=out["trace"]["checker"]["passed"], got={"rows": sorted(rows), "columns": sorted(cols),
                                                                    "base": {k: sorted(v) for k, v in base.items()}})
    s["exact"] = bool(s["rows_ok"] and s["columns_ok"] and s["base_ok"])
    return s


def run_item(pipeline, item, xwalk) -> dict:
    out = pipeline.ask(item["question"])
    clarified = 0
    while out["status"] == "clarify" and clarified < 2:
        exp_codes = set(item["expected"]["rows"] + item["expected"]["columns"] + list(item["expected"]["base"]))
        choices = {}
        for c in out["clarify"]:
            codes = [o["code"] for o in c["options"]]
            pick = next((o for o in codes if norm_vars([o], xwalk) & exp_codes), codes[0])
            choices[c["phrase"]] = pick
        clarified += 1
        out = pipeline.ask(item["question"], choices)
    out["_clarified"] = clarified
    return out


def run(limit: int | None = None, out: str | None = None, pipeline=None) -> dict:
    if pipeline is None:
        from .llm import AnthropicLLM
        from .pipeline import Pipeline
        pipeline = Pipeline(Engine(config.release_dir()), AnthropicLLM(), log_dir=config.log_dir())
    catalog = pipeline.catalog
    xwalk = _crosswalk(catalog)
    items = load_golden()[:limit] if limit else load_golden()
    results = []
    for it in items:
        o = run_item(pipeline, it, xwalk)
        r = score(it, o, catalog, xwalk)
        results.append(r)
        mark = "PASS" if r["exact"] else "FAIL"
        print(f"{mark}  {it['id']}  {it['question'][:60]:<60}  status={r['status']}" + (f" got={r.get('got')}" if not r["exact"] else ""))
    answered = [r for r in results if r.get("rows_ok") is not None]
    summary = {
        "items": len(results),
        "exact_spec_match": sum(r["exact"] for r in results) / len(results),
        "status_accuracy": sum(r["status_ok"] for r in results) / len(results),
        "row_variable_recall": sum(r["row_recall"] for r in answered) / max(len(answered), 1),
        "checker_pass_rate": sum(r["checker_passed"] for r in answered) / max(len(answered), 1),
        "clarify_rate": sum(1 for r in results if r["clarified"]) / len(results),
    }
    print("\n" + json.dumps(summary, indent=1))
    if out:
        Path(out).write_text(json.dumps({"summary": summary, "results": results}, indent=1, default=str))
    return summary
