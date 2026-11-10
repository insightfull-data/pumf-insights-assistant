"""Validate a query spec: JSON Schema first, then semantic checks against the catalog."""
from __future__ import annotations

import json
from importlib import resources

import jsonschema

from .catalog import Catalog

SCHEMA = json.loads(resources.files("pumfai").joinpath("schemas/query-spec.schema.json").read_text())
_VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)


class SpecError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def filter_vars(f: dict | None) -> list[tuple[str, dict]]:
    """Flatten a filter tree into (var, condition) pairs."""
    if not f:
        return []
    if "var" in f:
        return [(f["var"], f)]
    for key in ("all", "any"):
        if key in f:
            return [p for sub in f[key] for p in filter_vars(sub)]
    if "not" in f:
        return filter_vars(f["not"])
    return []


def validate(spec: dict, catalog: Catalog) -> dict:
    errors = [f"{'/'.join(map(str, e.path)) or 'spec'}: {e.message}" for e in _VALIDATOR.iter_errors(spec)]
    if errors:
        raise SpecError(errors)
    rel = catalog.release
    if spec["release_id"] != rel["release_id"]:
        errors.append(f"release_id {spec['release_id']} is not the published release ({rel['release_id']})")
    if spec["survey"] != rel["survey"]:
        errors.append(f"survey {spec['survey']} not loaded")
    if spec.get("estimate_type", "direct") != "direct":
        errors.append("model_based_sizing needs the Census PUMF, which this minimal implementation does not load")
    if spec["weight"] != rel["weight_code"]:
        errors.append(f"weight must be {rel['weight_code']}")
    if len(spec.get("columns", [])) > 1:
        errors.append("this implementation supports at most one column variable")

    def check_var(code: str, where: str):
        if catalog.get(code) is None:
            errors.append(f"{where}: unknown variable '{code}'")
            return False
        return True

    for i, ax in enumerate(spec["rows"]):
        if check_var(ax["var"], f"rows[{i}]"):
            _check_values(ax["var"], ax.get("values", []), catalog, errors, f"rows[{i}]")
    for i, ax in enumerate(spec.get("columns", [])):
        if check_var(ax["var"], f"columns[{i}]"):
            _check_values(ax["var"], ax.get("values", []), catalog, errors, f"columns[{i}]")
    for part in ("base", "universe"):
        for var, cond in filter_vars(spec.get(part)):
            if check_var(var, part):
                vals = cond.get("in") or ([cond["eq"]] if "eq" in cond else [])
                _check_values(var, vals, catalog, errors, part)
    row_codes = [r["var"] for r in spec["rows"]]
    if len(set(row_codes)) != len(row_codes):
        errors.append("rows repeat a variable")
    if errors:
        raise SpecError(errors)
    return spec


def _check_values(var, values, catalog, errors, where):
    allowed = {x["code"] for x in catalog.get(var)["values"]}
    for v in values:
        if str(v) not in allowed:
            errors.append(f"{where}: value {v!r} is not a code of {var} (codes: {sorted(allowed)})")
