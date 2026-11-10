"""Deterministic tabulation engine: query spec -> weighted crosstab with reliability flags.

Every number the assistant shows comes from here. For each row variable (and the
optional column variable) it computes, within the base and universe:

  weighted count  N_rc = sum(w_i * 1[r_i] * 1[c_i])
  column percent  p_r|c = N_rc / N_c         (valid responses only)
  row percent     N_rc / N_r
  index           100 * p_r|c / p_r|total
  bootstrap SE    sqrt(mean_b (theta_b - mean(theta_b))^2), CV = SE / theta

and applies the release's reliability rule: E = use with caution, F = too unreliable
(value withheld), following StatCan's flag convention.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np

from .catalog import Catalog
from .spec import validate


class Engine:
    def __init__(self, release_dir: Path, catalog: Catalog | None = None):
        self.release_dir = Path(release_dir)
        self.catalog = catalog or Catalog.load(self.release_dir)
        self.con = duckdb.connect()
        pq = (self.release_dir / "microdata.parquet").as_posix()
        self.con.execute(f"CREATE VIEW t AS SELECT * FROM read_parquet('{pq}')")
        self.columns = {r[0] for r in self.con.execute("DESCRIBE t").fetchall()}
        rel = self.catalog.release
        self.w = rel["weight_code"]
        self.boot = rel["bootstrap_codes"]
        self.rule = rel["reliability"]

    # ---------- SQL building (identifiers checked against the schema, values bound) ----------
    def _col(self, code: str) -> str:
        if code not in self.columns or self.catalog.get(code) is None:
            raise ValueError(f"unknown column {code!r}")
        return f'"{code}"'

    def _cast(self, code: str, v):
        return str(v) if self.catalog.get(code)["value_type"] == "string" else int(v)

    def _where(self, f: dict | None, params: list) -> str:
        if not f:
            return "TRUE"
        if "var" in f:
            c, code = self._col(f["var"]), f["var"]
            if "eq" in f:
                params.append(self._cast(code, f["eq"]))
                return f"{c} = ?"
            if "in" in f:
                params.extend(self._cast(code, v) for v in f["in"])
                return f"{c} IN ({', '.join('?' * len(f['in']))})"
            lo, hi = f["between"]
            params.extend([lo, hi])
            return f"{c} BETWEEN ? AND ?"
        if "all" in f:
            return "(" + " AND ".join(self._where(s, params) for s in f["all"]) + ")"
        if "any" in f:
            return "(" + " OR ".join(self._where(s, params) for s in f["any"]) + ")"
        if "not" in f:
            return "(NOT " + self._where(f["not"], params) + ")"
        raise ValueError("bad filter")

    def _valid(self, code: str, params: list) -> str:
        miss = self.catalog.missing_codes(code)
        c = self._col(code)
        if not miss:
            return f"{c} IS NOT NULL"
        params.extend(self._cast(code, m) for m in miss)
        return f"{c} IS NOT NULL AND {c} NOT IN ({', '.join('?' * len(miss))})"

    # ---------- public API ----------
    def tabulate(self, spec: dict) -> dict:
        validate(spec, self.catalog)
        col_var = spec["columns"][0]["var"] if spec.get("columns") else None
        col_subset = [str(v) for v in spec["columns"][0].get("values", [])] if col_var else []
        blocks, notes = [], []
        for ax in spec["rows"]:
            blocks.append(self._block(spec, ax, col_var, col_subset, notes))
        cols = [{"code": "total", "label": "Total"}]
        if col_var:
            vals = self.catalog.valid_values(col_var)
            cols += [{"code": x["code"], "label": x["label"]} for x in vals if not col_subset or x["code"] in col_subset]
        return {
            "release_id": self.catalog.release["release_id"],
            "title": self.catalog.release["title"],
            "spec": spec,
            "column_var": {"code": col_var, "label": self.catalog.get(col_var)["label"]} if col_var else None,
            "columns": cols,
            "rows": blocks,
            "reliability": self.rule,
            "notes": notes,
        }

    def _block(self, spec, ax, col_var, col_subset, notes) -> dict:
        rv = ax["var"]
        params: list = []
        conds = [self._where(spec.get("base"), params), self._where(spec.get("universe"), params)]
        # Universes of the variables shown are always enforced, even if the planner forgot them.
        for code in [rv] + ([col_var] if col_var else []):
            uni = self.catalog.get(code).get("universe_expr")
            if uni:
                conds.append(self._where(uni, params))
        if spec.get("missing", "exclude") == "exclude":
            conds.append(self._valid(rv, params))
            if col_var:
                conds.append(self._valid(col_var, params))
        where = " AND ".join(conds)

        wcols = [self.w] + self.boot
        sums = ", ".join(f'SUM("{c}")' for c in wcols)
        rexpr = self._col(rv)
        cexpr = self._col(col_var) if col_var else "'all'"
        sql = (f"SELECT {rexpr} AS r, {cexpr} AS c, GROUPING({rexpr}, {cexpr}) AS g, COUNT(*) AS n, {sums} "
               f"FROM t WHERE {where} GROUP BY GROUPING SETS (({rexpr}, {cexpr}), ({rexpr}), ({cexpr}), ())")
        res = self.con.execute(sql, params).fetchall()
        # g: 0 = (row, col) cell, 1 = row total, 2 = column total, 3 = grand total
        cells = {(g, r if g in (0, 1) else None, c if g in (0, 2) else None): (n, np.array(ws, dtype=float))
                 for r, c, g, n, *ws in res}
        zero = (0, np.zeros(1 + len(self.boot)))

        def get(r, c):
            g = (0 if c is not None else 1) if r is not None else (2 if c is not None else 3)
            return cells.get((g, r, c), zero)

        n_tot, W_tot = get(None, None)
        if col_var:
            col_codes = [x["code"] for x in self.catalog.valid_values(col_var) if not col_subset or x["code"] in col_subset]
        else:
            col_codes = []
        show_missing = spec.get("missing", "exclude") == "show"
        row_vals = self.catalog.get(rv)["values"] if show_missing else self.catalog.valid_values(rv)
        if ax.get("values"):
            keep = {str(v) for v in ax["values"]}
            row_vals = [x for x in row_vals if x["code"] in keep]

        out_rows = []
        for x in row_vals:
            rcode = self._cast(rv, x["code"])
            cells_out = {"total": self._cell(*get(rcode, None), *get(None, None), W_row=get(rcode, None)[1], W_base_r=get(rcode, None)[1], W_base=W_tot)}
            for cc in col_codes:
                ccv = self._cast(col_var, cc)
                n_rc, W_rc = get(rcode, ccv)
                n_c, W_c = get(None, ccv)
                cells_out[cc] = self._cell(n_rc, W_rc, n_c, W_c, W_row=get(rcode, None)[1],
                                           W_base_r=get(rcode, None)[1], W_base=W_tot)
            out_rows.append({"code": x["code"], "label": x["label"], "cells": cells_out})
        if n_tot == 0:
            notes.append(f"No respondents match the base for {rv}.")
        return {"var": rv, "label": self.catalog.get(rv)["label"],
                "universe": self.catalog.get(rv).get("universe_text"),
                "base_unweighted_n": int(n_tot), "base_weighted": float(W_tot[0]), "values": out_rows}

    def _cell(self, n_rc, W_rc, n_c, W_c, W_row, W_base_r, W_base) -> dict:
        """Estimates for one cell. W_* are arrays [final, boot_1..boot_B]."""
        with np.errstate(divide="ignore", invalid="ignore"):
            p = np.where(W_c > 0, W_rc / W_c, np.nan)            # column share, per replicate
            p_tot = np.where(W_base > 0, W_base_r / W_base, np.nan)  # row share in total column
            rowp = np.where(W_row > 0, W_rc / W_row, np.nan)
        est_p, est_N = p[0], W_rc[0]
        se_p = _boot_se(p)
        se_N = _boot_se(W_rc)
        cv_p = se_p / est_p * 100 if est_p and est_p > 0 else None
        cv_N = se_N / est_N * 100 if est_N > 0 else None
        flag = "ok"
        if n_c < self.rule["min_unweighted_n"] or (cv_p is not None and cv_p > self.rule["suppress_cv_pct"]):
            flag = "F"
        elif cv_p is not None and cv_p > self.rule["caution_cv_pct"]:
            flag = "E"
        idx = est_p / p_tot[0] * 100 if p_tot[0] and p_tot[0] > 0 else None
        cell = {
            "flag": flag, "unweighted_n": int(n_rc), "denominator_n": int(n_c),
            "weighted_count": float(est_N), "col_pct": float(est_p * 100) if not np.isnan(est_p) else None,
            "row_pct": float(rowp[0] * 100) if not np.isnan(rowp[0]) else None,
            "index": float(idx) if idx is not None else None,
            "se_pct": float(se_p * 100), "cv_pct": None if cv_p is None else float(cv_p),
            "cv_count_pct": None if cv_N is None else float(cv_N),
        }
        if flag == "F":  # withhold values so nothing downstream (including the narrator) can use them
            for k in ("weighted_count", "col_pct", "row_pct", "index", "se_pct"):
                cell[k] = None
        return cell


def _boot_se(theta: np.ndarray) -> float:
    reps = theta[1:]
    reps = reps[~np.isnan(reps)]
    if len(reps) < 2:
        return float("nan")
    return float(np.sqrt(np.mean((reps - reps.mean()) ** 2)))
