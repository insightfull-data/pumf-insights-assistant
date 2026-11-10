"""Parse the SPSS syntax files that ship with StatCan PUMFs.

Handles the parts the assistant needs: DATA LIST column positions (with implied decimals),
VARIABLE LABELS, VALUE LABELS and MISSING VALUES. StatCan's convention for reserved
codes (the last digit 6, 7, 8 or 9 of the widest code) maps to valid skip, don't know,
refusal and not stated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MISSING_TYPE_BY_LAST_DIGIT = {"6": "valid_skip", "7": "dont_know", "8": "refusal", "9": "not_stated"}


@dataclass
class Column:
    name: str
    start: int  # 1-based
    end: int    # inclusive
    decimals: int = 0
    label: str = ""
    value_labels: dict[str, str] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)

    @property
    def width(self) -> int:
        return self.end - self.start + 1


def _blocks(text: str, keyword: str) -> list[str]:
    """Return the bodies of every '<KEYWORD> ... .' command (terminated by a period at line end)."""
    out = []
    for m in re.finditer(rf"^\s*{keyword}\b(.*?)\.\s*$", text, flags=re.I | re.S | re.M):
        out.append(m.group(1))
    return out


def parse(text: str) -> dict[str, Column]:
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("*"))
    cols: dict[str, Column] = {}

    for body in _blocks(text, "DATA LIST"):
        for m in re.finditer(r"([A-Za-z][A-Za-z0-9_]*)\s+(\d+)(?:\s*-\s*(\d+))?(?:\s*\((\d+)\))?", body):
            name = m.group(1).upper()
            if name in {"FILE", "RECORDS"}:
                continue
            start = int(m.group(2))
            cols[name] = Column(name, start, int(m.group(3) or start), int(m.group(4) or 0))

    for body in _blocks(text, "VARIABLE LABELS"):
        for m in re.finditer(r"/?\s*([A-Za-z][A-Za-z0-9_]*)\s+(['\"])(.*?)\2", body):
            if m.group(1).upper() in cols:
                cols[m.group(1).upper()].label = m.group(3).strip()

    for body in _blocks(text, "VALUE LABELS"):
        for chunk in re.split(r"(?m)^\s*/", body):
            chunk = chunk.strip()
            if not chunk:
                continue
            head = re.match(r"((?:[A-Za-z][A-Za-z0-9_]*\s+)+?)(?=-?\d+(?:\.\d+)?\s+['\"])", chunk)
            if not head:
                continue
            names = [n.upper() for n in head.group(1).split()]
            labs = {m.group(1): m.group(3) for m in re.finditer(r"(-?\d+(?:\.\d+)?)\s+(['\"])(.*?)\2", chunk[head.end():])}
            for n in names:
                if n in cols:
                    cols[n].value_labels.update(labs)

    for body in _blocks(text, "MISSING VALUES"):
        for m in re.finditer(r"([A-Za-z][A-Za-z0-9_ ]*?)\s*\(([^)]*)\)", body):
            names = [n.upper() for n in m.group(1).split()]
            spec = m.group(2).upper()
            codes: set[str] = set()
            rng = re.match(r"\s*(-?\d+)\s+THRU\s+(-?\d+)\s*$", spec)
            if rng:
                lo, hi = int(rng.group(1)), int(rng.group(2))
                codes = {str(v) for v in range(lo, hi + 1)}
            else:
                codes = {c.strip() for c in spec.split(",") if c.strip()}
            for n in names:
                if n in cols:
                    cols[n].missing |= codes
    return cols


def missing_type(code: str, col: Column) -> str:
    if code not in col.missing:
        return "valid"
    return MISSING_TYPE_BY_LAST_DIGIT.get(code[-1], "not_stated")


def read_fixed_width(path, cols: dict[str, Column]):
    """Yield dict rows from a fixed-width PUMF data file (small files; use DuckDB for large ones)."""
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            row = {}
            for c in cols.values():
                raw = line[c.start - 1:c.end].strip()
                if raw == "":
                    row[c.name] = None
                elif c.decimals:
                    row[c.name] = float(raw) if "." in raw else int(raw) / 10 ** c.decimals
                else:
                    row[c.name] = int(raw)
            yield row
