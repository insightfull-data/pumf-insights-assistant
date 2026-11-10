"""Number checker: every figure in a narrative must match the table the user sees.

Checked: percentages, percentage-point gaps, counts written as millions/thousands or with
digit grouping, and index values. Numbers that appear in labels or the question (ages,
years, quintile numbers) are allowed. Anything else fails, and the pipeline regenerates
the narrative or falls back to a template.
"""
from __future__ import annotations

import itertools
import re

from .render import display_table

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
PCT = re.compile(_NUM + r"\s*(?:%|per\s*cent|percent)(?!\s*age)", re.I)
PP = re.compile(_NUM + r"\s*(?:percentage[- ]points?|pp\b|points?\b)", re.I)
MILL = re.compile(_NUM + r"\s*(million|thousand)\b", re.I)
BIG = re.compile(r"\b(\d{1,3}(?:,\d{3})+)\b(?!\s*(?:%|per|million|thousand))")
INDEX = re.compile(r"index(?:\s+(?:of|at|value|score))?\s*(?:of\s*)?(\d+(?:\.\d+)?)", re.I)


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def check(narrative: str, result: dict, extra_text: str = "") -> list[str]:
    cells = display_table(result)
    pcts = [c["pct"] for c in cells if c["pct"] is not None]
    counts = [c["count"] for c in cells if c["count"] is not None]
    counts += [round(b["base_weighted"], -3) for b in result["rows"]]
    idxs = [c["index"] for c in cells if c["index"] is not None]
    gaps = [abs(a - b) for a, b in itertools.combinations(pcts, 2)]
    allowed_plain = {float(x) for x in re.findall(r"\d+(?:\.\d+)?", extra_text)}
    for b in result["rows"]:
        for v in b["values"]:
            allowed_plain |= {float(x) for x in re.findall(r"\d+(?:\.\d+)?", v["label"])}
    for c in result["columns"]:
        allowed_plain |= {float(x) for x in re.findall(r"\d+(?:\.\d+)?", c["label"])}

    problems = []
    text = narrative
    for m in PCT.finditer(text):
        v = _f(m.group(1))
        if not any(abs(v - p) <= 0.05 or (v == round(v) and abs(v - p) < 0.5) for p in pcts):
            problems.append(f"{m.group(0)!r} is not a percentage in the table")
    for m in PP.finditer(text):
        v = _f(m.group(1))
        if not any(abs(v - g) <= 0.15 or (v == round(v) and abs(v - g) < 0.6) for g in gaps):
            problems.append(f"{m.group(0)!r} is not a difference between two table percentages")
    for m in MILL.finditer(text):
        v = _f(m.group(1)) * (1e6 if m.group(2).lower() == "million" else 1e3)
        decimals = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
        unit = 1e6 if m.group(2).lower() == "million" else 1e3
        tol = 0.5 * unit / 10 ** decimals + 500
        if not any(abs(v - c) <= tol for c in counts):
            problems.append(f"{m.group(0)!r} does not match a count in the table")
    for m in BIG.finditer(text):
        v = _f(m.group(1))
        if not any(abs(v - c) <= 500 for c in counts) and v not in allowed_plain:
            problems.append(f"{m.group(0)!r} does not match a count in the table")
    for m in INDEX.finditer(text):
        v = _f(m.group(1))
        if not any(abs(v - i) <= 0.5 for i in idxs):
            problems.append(f"index {m.group(1)} is not in the table")
    return problems


def suppressed_leak(narrative: str, result: dict) -> bool:
    """True if the narrative appears to estimate a suppressed cell (e.g. 'about 5%')."""
    return bool(re.search(r"\b(?:about|around|roughly|approximately)\s+\d", narrative, re.I)) and any(
        c["flag"] == "F" for c in display_table(result))
