"""FastAPI service.

  POST /ask          question (+ optional choices after a clarify) -> answer, table, spec, trace
  POST /tabulate     query spec -> table (no LLM; for analysts and tests)
  GET  /variables    keyword search of the catalog
  GET  /variables/{code}
  GET  /health

Run:  uvicorn pumfai.api:app --reload
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import config
from .engine import Engine
from .pipeline import Pipeline
from .render import markdown
from .spec import SpecError

app = FastAPI(title="PUMF Insights Assistant", version="0.1.0",
              description="Reference implementation. Answers come from a deterministic engine; the LLM only interprets and narrates.")


@lru_cache
def get_engine() -> Engine:
    if not (config.release_dir() / "catalog.json").exists():
        raise RuntimeError(f"No ingested release at {config.release_dir()}. Run: python -m pumfai setup")
    return Engine(config.release_dir())


@lru_cache
def _pipeline() -> Pipeline:
    from .llm import AnthropicLLM
    return Pipeline(get_engine(), AnthropicLLM(), log_dir=config.log_dir())


def get_pipeline() -> Pipeline:
    import os
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(503, "ANTHROPIC_API_KEY is not set; /ask is unavailable. /tabulate and /variables still work.")
    return _pipeline()


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    choices: dict[str, str] | None = Field(default=None, description="phrase -> variable code, from a clarify response")


@app.get("/health")
def health(engine: Engine = Depends(get_engine)):
    rel = engine.catalog.release
    return {"status": "ok", "release_id": rel["release_id"], "title": rel["title"], "variables": len(engine.catalog.variables)}


@app.post("/ask")
def ask(req: AskRequest, pipeline: Pipeline = Depends(get_pipeline)):
    try:
        return pipeline.ask(req.question, req.choices)
    except Exception as e:  # upstream LLM or network failure
        if e.__class__.__module__.startswith("anthropic"):
            raise HTTPException(502, f"LLM provider error: {e.__class__.__name__}")
        raise


@app.post("/tabulate")
def tabulate(spec: dict, engine: Engine = Depends(get_engine)):
    try:
        result = engine.tabulate(spec)
    except SpecError as e:
        raise HTTPException(422, {"errors": e.errors})
    return {"result": result, "table_markdown": markdown(result)}


@app.get("/variables")
def variables(q: str = "", k: int = 10, engine: Engine = Depends(get_engine)):
    cat = engine.catalog
    if not q:
        return [cat.card(c, with_values=False) for c in cat.variables]
    return cat.search(q, k=min(k, 50))


@app.get("/variables/{code}")
def variable(code: str, engine: Engine = Depends(get_engine)):
    v = engine.catalog.get(code)
    if v is None:
        raise HTTPException(404, f"unknown variable {code}")
    return v
