import json

import pytest
from fastapi.testclient import TestClient

from fakes import OracleLLM, ScriptedLLM
from pumfai import evaluate
from pumfai.pipeline import Pipeline


@pytest.fixture(scope="module")
def golden():
    return evaluate.load_golden()


def oracle_pipeline(engine, golden, tmp_path=None, narrative=None):
    return Pipeline(engine, OracleLLM(golden, engine.catalog.release, narrative), log_dir=tmp_path)


def test_answered_end_to_end_and_logged(engine, golden, tmp_path):
    p = oracle_pipeline(engine, golden, tmp_path)
    out = p.ask(golden[0]["question"])
    assert out["status"] == "answered"
    assert out["trace"]["checker"]["passed"]
    assert "|" in out["table_markdown"]
    rec = json.loads((tmp_path / "answers.jsonl").read_text().splitlines()[-1])
    assert rec["spec"]["rows"] == [{"var": "ac_pod"}] and rec["trace"]["prompt_version"]


def test_unsupported_question(engine, golden):
    out = oracle_pipeline(engine, golden).ask("How many people in Scarborough watch Netflix?")
    assert out["status"] == "unsupported"


def test_bad_narrative_falls_back_to_template(engine, golden):
    p = oracle_pipeline(engine, golden, narrative="Exactly 99.9% of everyone, about 50 million people.")
    out = p.ask(golden[0]["question"])
    assert out["status"] == "answered"
    assert out["trace"]["checker"]["fallback"] is True
    assert "99.9" not in out["answer"]
    assert p.llm.calls.count("narrator") == 2


def test_low_confidence_asks_then_uses_choice(engine):
    intent = {"answerable": True, "reason_if_not": "", "question_type": "share", "measures": ["streaming"],
              "population_filters": [], "breakdown": ""}
    low = {"selections": [{"phrase": "streaming", "role": "measure", "code": "ac_strm", "confidence": 0.4,
                           "alternatives": ["ac_mus"]}]}
    spec = {"rows": [{"var": "ac_mus"}]}
    llm = ScriptedLLM(intent=[intent, intent], rerank=[low, low], planner=[spec], narrator=["Done."])
    p = Pipeline(engine, llm)
    first = p.ask("How common is streaming?")
    assert first["status"] == "clarify"
    codes = [o["code"] for o in first["clarify"][0]["options"]]
    assert codes[:2] == ["ac_strm", "ac_mus"]
    second = p.ask("How common is streaming?", {"streaming": "ac_mus"})
    assert second["status"] == "answered" and second["spec"]["rows"] == [{"var": "ac_mus"}]


def test_planner_gets_one_retry_with_errors(engine):
    intent = {"answerable": True, "reason_if_not": "", "question_type": "share", "measures": ["ac_pod"],
              "population_filters": [], "breakdown": ""}
    sel = {"selections": [{"phrase": "ac_pod", "role": "measure", "code": "ac_pod", "confidence": 0.9, "alternatives": []}]}
    bad = {"rows": [{"var": "ac_pod"}], "base": {"var": "h_province", "eq": "Ontario"}}
    good = {"rows": [{"var": "ac_pod"}], "base": {"var": "h_province", "eq": "ON"}}
    llm = ScriptedLLM(intent=[intent], rerank=[sel], planner=[bad, good], narrator=["Done."])
    out = Pipeline(engine, llm).ask("podcasts in Ontario")
    assert out["status"] == "answered"
    assert "not a code" in out["trace"]["spec_errors_first_try"][0]
    assert "rejected" in llm.calls[-2][1]


def test_golden_set_scores_perfectly_with_oracle(engine, golden):
    summary = evaluate.run(pipeline=oracle_pipeline(engine, golden))
    assert summary["exact_spec_match"] == 1.0
    assert summary["checker_pass_rate"] == 1.0


def test_api(engine, golden):
    from pumfai import api
    api.app.dependency_overrides[api.get_engine] = lambda: engine
    api.app.dependency_overrides[api.get_pipeline] = lambda: oracle_pipeline(engine, golden)
    c = TestClient(api.app)
    assert c.get("/health").json()["release_id"] == "cius_synth_2022"
    assert c.get("/variables", params={"q": "podcasts"}).json()[0]["code"] == "ac_pod"
    assert c.get("/variables/nope").status_code == 404
    r = c.post("/tabulate", json={"spec_version": "1.0", "survey": "cius", "release_id": "cius_synth_2022",
                                  "weight": "wtpp", "measures": ["col_pct"], "base": {"var": "h_province", "eq": "ON"},
                                  "rows": [{"var": "ac_pod"}]})
    assert r.status_code == 200 and "Yes" in r.json()["table_markdown"]
    assert c.post("/tabulate", json={"rows": []}).status_code == 422
    a = c.post("/ask", json={"question": golden[0]["question"]}).json()
    assert a["status"] == "answered"
    api.app.dependency_overrides.clear()


def test_package_schema_matches_repo_schema():
    from pathlib import Path
    here = Path(__file__).resolve().parents[1]
    pkg = (here / "pumfai" / "schemas" / "query-spec.schema.json").read_text()
    repo = (here.parent / "schemas" / "query-spec.schema.json").read_text()
    assert json.loads(pkg) == json.loads(repo)
