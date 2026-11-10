"""Variable catalog loaded from catalog.json, with BM25 keyword search.

Production uses PostgreSQL + pgvector with hybrid search (sql/catalog.sql). This minimal
version keeps the same contract: search(text) -> ranked variables of the published release,
with exact code matches always first.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

_TOKEN = re.compile(r"[a-z0-9$]+")


def _tokens(text: str) -> list[str]:
    toks = _TOKEN.findall(text.lower())
    return [t[:-1] if len(t) > 4 and t.endswith("s") else t for t in toks]  # crude plural folding


class Catalog:
    def __init__(self, data: dict):
        self.release = data["release"]
        self.variables = {v["code"]: v for v in data["variables"]}
        self._docs = {code: _tokens(self.search_text(v)) for code, v in self.variables.items()}
        self._df = Counter(t for toks in self._docs.values() for t in set(toks))
        self._avgdl = sum(len(d) for d in self._docs.values()) / max(len(self._docs), 1)

    @classmethod
    def load(cls, release_dir: Path) -> "Catalog":
        return cls(json.loads((Path(release_dir) / "catalog.json").read_text()))

    @staticmethod
    def search_text(v: dict) -> str:
        vals = " ".join(x["label"] for x in v["values"] if x["missing_type"] == "valid")
        return " ".join([v["code"], v["label"], v.get("question_text", ""), v.get("description", ""),
                         v.get("topic", "").replace("_", " ").replace(".", " "), " ".join(v.get("synonyms", [])), vals])

    def get(self, code: str) -> dict | None:
        return self.variables.get(code)

    def valid_values(self, code: str) -> list[dict]:
        return [x for x in self.variables[code]["values"] if x["missing_type"] == "valid"]

    def missing_codes(self, code: str) -> list[str]:
        return [x["code"] for x in self.variables[code]["values"] if x["missing_type"] != "valid"]

    def label_of(self, code: str, value) -> str:
        for x in self.variables[code]["values"]:
            if x["code"] == str(value):
                return x["label"]
        return str(value)

    def search(self, text: str, k: int = 10) -> list[dict]:
        q = _tokens(text)
        n = len(self._docs)
        scores = {}
        for code, doc in self._docs.items():
            tf = Counter(doc)
            s = 0.0
            for t in set(q):
                if t not in tf:
                    continue
                idf = math.log(1 + (n - self._df[t] + 0.5) / (self._df[t] + 0.5))
                f = tf[t]
                s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(doc) / self._avgdl))
            if text.strip().lower() == code:
                s += 1000.0
            if s > 0:
                scores[code] = s
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:k]
        return [{"code": c, "label": self.variables[c]["label"], "score": round(s, 3)} for c, s in ranked]

    def card(self, code: str, with_values: bool = True) -> dict:
        """Compact description of a variable for LLM prompts (no data, metadata only)."""
        v = self.variables[code]
        out = {"code": code, "label": v["label"], "question": v.get("question_text") or None,
               "universe": v.get("universe_text"), "description": v.get("description") or None}
        if with_values:
            out["values"] = {x["code"]: x["label"] for x in v["values"] if x["missing_type"] == "valid"}
        return {k: val for k, val in out.items() if val}
