"""Ingest a PUMF release: parse syntax, apply quality rules, write Parquet and the catalog.

Mirrors steps 4-10 of the production pipeline (docs/data-architecture.md, section 5)
on a laptop: one release folder in, one Parquet file and one catalog.json out.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from . import spss


class QualityError(Exception):
    pass


def ingest(raw_dir: Path, out_root: Path) -> Path:
    guide = json.loads((raw_dir / "user_guide.json").read_text())
    overlay = json.loads((raw_dir / "steward_overlay.json").read_text())
    syntax_path = next(raw_dir.glob("*.sps"))
    cols = spss.parse(syntax_path.read_text())
    data_path = raw_dir / _data_file_name(syntax_path.read_text())

    rows = list(spss.read_fixed_width(data_path, cols))
    report = _quality(rows, cols, guide)

    wvar = guide["weight_variable"].upper()
    boot = sorted(c for c in cols if c.startswith(guide["bootstrap_prefix"].upper()))
    table: dict[str, list] = {}
    for name, c in cols.items():
        table[name.lower()] = [r[name] for r in rows]

    # Harmonized columns (h_*) from the steward crosswalk
    for h, spec in overlay.get("harmonized", {}).items():
        src = table[spec["source"]]
        table[h] = [spec["map"].get(str(v)) for v in src]

    out_dir = out_root / "release" / guide["release_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(table), out_dir / "microdata.parquet", compression="zstd")

    catalog = _catalog(cols, overlay, guide, wvar, boot)
    catalog["release"]["source_sha256"] = hashlib.sha256(data_path.read_bytes()).hexdigest()
    catalog["release"]["quality_report"] = report
    (out_dir / "catalog.json").write_text(json.dumps(catalog, indent=1))
    return out_dir


def _data_file_name(syntax: str) -> str:
    import re
    m = re.search(r"FILE\s*=\s*['\"]([^'\"]+)['\"]", syntax, flags=re.I)
    if not m:
        raise QualityError("DATA LIST has no FILE= clause")
    return m.group(1)


def _quality(rows, cols, guide) -> dict:
    """Blocking rules from section 5 of the data architecture."""
    wvar = guide["weight_variable"].upper()
    n = len(rows)
    if n != guide["record_count"]:
        raise QualityError(f"record count {n} != user guide {guide['record_count']}")
    total = sum(r[wvar] for r in rows)
    if abs(total - guide["weight_total"]) / guide["weight_total"] > 0.005:
        raise QualityError(f"weight total {total:,.0f} differs from guide {guide['weight_total']:,.0f} by more than 0.5%")
    if any(r[wvar] is None or r[wvar] <= 0 for r in rows):
        raise QualityError("non-positive or missing final weights")
    boot_prefix = guide["bootstrap_prefix"].upper()
    unlabelled = [name for name, c in cols.items() if not c.value_labels and not c.decimals
                  and name != "PUMFID" and not name.startswith(boot_prefix)]
    if unlabelled:
        raise QualityError(f"categorical variables without value labels: {unlabelled}")
    orphans = {}
    for name, c in cols.items():
        if not c.value_labels:
            continue
        seen = {str(r[name]) for r in rows if r[name] is not None}
        bad = seen - set(c.value_labels)
        if bad:
            orphans[name] = sorted(bad)
    if orphans:
        raise QualityError(f"codes without value labels: {orphans}")
    nboot = sum(1 for c in cols if c.startswith(guide["bootstrap_prefix"].upper()))
    if nboot != guide["n_bootstrap"]:
        raise QualityError(f"expected {guide['n_bootstrap']} bootstrap weights, found {nboot}")
    return {"record_count": n, "weight_total": round(total, 1), "bootstrap_weights": nboot, "status": "passed"}


def _catalog(cols, overlay, guide, wvar, boot) -> dict:
    variables = []
    ov = overlay.get("variables", {})
    skip = {wvar} | set(boot) | {"PUMFID"}
    for name, c in cols.items():
        if name in skip:
            continue
        code = name.lower()
        meta = ov.get(code, {})
        variables.append({
            "code": code,
            "label": c.label,
            "question_text": meta.get("question_text", ""),
            "topic": meta.get("topic", ""),
            "universe_text": meta.get("universe_text", "All respondents"),
            "universe_expr": meta.get("universe_expr"),
            "measure_type": meta.get("measure_type", "categorical"),
            "description": meta.get("description", ""),
            "synonyms": meta.get("synonyms", []),
            "review_status": "approved" if meta else "draft",
            "values": [{"code": k, "label": v, "missing_type": spss.missing_type(k, c)} for k, v in c.value_labels.items()],
            "value_type": "integer",
        })
    for h, spec in overlay.get("harmonized", {}).items():
        variables.append({
            "code": h, "label": spec["label"], "question_text": "", "topic": "harmonized",
            "universe_text": "All respondents", "universe_expr": None, "measure_type": "categorical",
            "description": f"Harmonized version of {spec['source']} shared across surveys.",
            "synonyms": spec.get("synonyms", []), "review_status": "approved",
            "values": [{"code": k, "label": v, "missing_type": "valid"} for k, v in spec["labels"].items()],
            "value_type": "string",
        })
    return {
        "release": {k: guide[k] for k in ("release_id", "survey", "ref_period", "title", "record_count",
                                          "weight_total", "n_bootstrap", "reliability", "population", "licence")}
                   | {"weight_code": wvar.lower(), "bootstrap_codes": [b.lower() for b in boot], "status": "published"},
        "variables": variables,
    }
