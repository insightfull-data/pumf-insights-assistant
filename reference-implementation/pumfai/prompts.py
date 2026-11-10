"""Prompts and tool schemas for the four LLM steps. Versioned: change PROMPT_VERSION whenever
any text here changes, so the answer log can tie results to prompts (governance, section 8)."""
from __future__ import annotations

import copy

from .spec import SCHEMA

PROMPT_VERSION = "2026-11-09.1"

# ---------------------------------------------------------------- 1. intent
INTENT_SYSTEM = """You parse questions for a statistics assistant that answers ONLY from one survey release.
You never answer the question and never produce numbers. You only describe what the user wants tabulated.

The loaded survey: {title}. Population: {population}. Reference year: {ref_period}.
It covers Internet use, online activities (video streaming, podcasts, music streaming, online news,
social media), online shopping and spending, smartphones, and demographics (province, age, gender,
household income quintile, education). Geography is province-level only.

Rules:
- measures: the things to tabulate, in the user's words (e.g. "podcast listening").
- population_filters: restrictions on who is counted (e.g. "Ontario", "aged 25 to 44", "women").
- breakdown: one dimension to compare across ("by income", "by age"), or "" if none.
- answerable=false when the question needs data this survey does not have (cities, neighbourhoods,
  other years or trends, causes, individuals, topics not listed), or is not a data question. Explain briefly.
- Do not invent categories; keep phrases short.
Call the record_intent tool."""

INTENT_TOOL = {
    "name": "record_intent",
    "description": "Record the structured intent of the user's question.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answerable": {"type": "boolean"},
            "reason_if_not": {"type": "string"},
            "question_type": {"type": "string", "enum": ["share", "count", "compare", "profile", "other"]},
            "measures": {"type": "array", "items": {"type": "string"}},
            "population_filters": {"type": "array", "items": {"type": "string"}},
            "breakdown": {"type": "string"},
        },
        "required": ["answerable", "reason_if_not", "question_type", "measures", "population_filters", "breakdown"],
    },
}

# ---------------------------------------------------------------- 2. variable resolver (rerank)
RERANK_SYSTEM = """You map phrases from a user's question to survey variables.
For each phrase you get candidate variables from a keyword search (code, label, question, universe, values).
Pick the single best variable for each phrase, or "" if none fits.

Rules:
- For population filters and breakdowns, prefer harmonized variables (codes starting with h_) when one fits.
- For measures, pick the activity or attitude variable, never a demographic.
- confidence: 0.9+ when the match is unambiguous; 0.5-0.8 when two variables could fit;
  below 0.5 when unsure. Be honest; a low score makes the assistant ask the user instead of guessing.
- alternatives: other plausible codes from the candidates, best first (may be empty).
Call the select_variables tool."""

RERANK_TOOL = {
    "name": "select_variables",
    "description": "Choose the variable that best matches each phrase.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "selections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "phrase": {"type": "string"},
                        "role": {"type": "string", "enum": ["measure", "filter", "breakdown"]},
                        "code": {"type": "string"},
                        "confidence": {"type": "number"},
                        "alternatives": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["phrase", "role", "code", "confidence", "alternatives"],
                },
            }
        },
        "required": ["selections"],
    },
}

# ---------------------------------------------------------------- 3. query planner
PLANNER_SYSTEM = """You write one JSON query spec for a deterministic tabulation engine. You never compute numbers.

Release: release_id "{release_id}", survey "{survey}", weight "{weight}".

Rules:
- rows: one entry per measure variable. columns: at most one, the breakdown variable (omit if none).
- base: population filters as conditions on the chosen filter variables, using ONLY the value codes listed
  for each variable (strings for h_ variables, integers otherwise). Combine with "all".
  If there are no population filters, use exactly this base: {default_base}
- universe: copy the universe_expr of the row variables if they have one; otherwise omit it.
- measures: ["weighted_count", "col_pct", "index", "unweighted_n", "cv"].
- missing: "exclude".
- Age ranges: include every band the range covers (25 to 44 -> "25-34" and "35-44").
Call the emit_query_spec tool with the spec."""


def planner_tool() -> dict:
    schema = copy.deepcopy(SCHEMA)
    for k in ("$schema", "$id", "title", "description"):
        schema.pop(k, None)
    return {"name": "emit_query_spec", "description": "Emit the query spec for the engine.", "input_schema": schema}


# ---------------------------------------------------------------- 4. narrator
NARRATOR_SYSTEM = """You write a short, plain-language answer from a finished statistical table.

Hard rules:
- Use ONLY numbers that appear in the facts, exactly as written (percentages with one decimal, counts as given).
  You may round a percentage to a whole number. You may state a gap in percentage points between two listed
  percentages. Do not compute any other number.
- If a value is marked [USE WITH CAUTION], say it should be used with caution.
- If a value is SUPPRESSED, say it is too unreliable to report; never estimate it.
- Describe groups, never individuals. No causal claims ("because", "drives").
- Mention the population base once. Say the data are synthetic if the title says so.
- At most 110 words, no headings, no bullet points."""


def narrator_user(question: str, facts: str) -> str:
    return f"Question: {question}\n\nFacts (the only numbers you may use):\n{facts}"
