import numpy as np
import pytest

from pumfai.spec import SpecError


def test_matches_independent_calculation(engine, microdata, spec_base):
    """Column %, counts, row %, index and bootstrap SE equal a plain pandas computation."""
    spec = spec_base | {"base": {"all": [{"var": "h_province", "eq": "ON"}]},
                        "rows": [{"var": "ac_pod"}], "columns": [{"var": "h_age_band"}]}
    res = engine.tabulate(spec)
    d = microdata
    d = d[(d.h_province == "ON") & (d.ui_010 == 1) & d.ac_pod.isin([1, 2]) & d.h_age_band.notna()]
    boot = [c for c in d.columns if c.startswith("wtbs_")]
    yes = res["rows"][0]["values"][0]
    assert yes["label"] == "Yes"
    for band in ["15-24", "25-34", "35-44", "45-54", "55-64"]:
        sub = d[d.h_age_band == band]
        num, den = sub[sub.ac_pod == 1], sub
        p = num.wtpp.sum() / den.wtpp.sum()
        p_tot = d[d.ac_pod == 1].wtpp.sum() / d.wtpp.sum()
        reps = np.array([num[b].sum() / den[b].sum() for b in boot])
        se = np.sqrt(np.mean((reps - reps.mean()) ** 2))
        cell = yes["cells"][band]
        assert cell["col_pct"] == pytest.approx(p * 100, abs=1e-9)
        assert cell["weighted_count"] == pytest.approx(num.wtpp.sum(), rel=1e-12)
        assert cell["index"] == pytest.approx(p / p_tot * 100, rel=1e-9)
        assert cell["se_pct"] == pytest.approx(se * 100, rel=1e-9)
        assert cell["unweighted_n"] == len(num)
        assert cell["row_pct"] == pytest.approx(num.wtpp.sum() / d[d.ac_pod == 1].wtpp.sum() * 100, rel=1e-9)
    tot = yes["cells"]["total"]
    assert tot["col_pct"] == pytest.approx(d[d.ac_pod == 1].wtpp.sum() / d.wtpp.sum() * 100, rel=1e-12)
    assert tot["index"] == pytest.approx(100)


def test_universe_enforced_even_if_spec_omits_it(engine, microdata, spec_base):
    res = engine.tabulate(spec_base | {"base": {"var": "h_province", "eq": "QC"}, "rows": [{"var": "ac_strm"}]})
    d = microdata
    users = d[(d.h_province == "QC") & (d.ui_010 == 1) & d.ac_strm.isin([1, 2])]
    assert res["rows"][0]["base_unweighted_n"] == len(users)


def test_missing_excluded_from_denominator(engine, microdata, spec_base):
    res = engine.tabulate(spec_base | {"base": {"var": "h_province", "eq": "ON"}, "rows": [{"var": "ac_shop"}]})
    pcts = [v["cells"]["total"]["col_pct"] for v in res["rows"][0]["values"]]
    assert sum(pcts) == pytest.approx(100.0)
    shown = engine.tabulate(spec_base | {"base": {"var": "h_province", "eq": "ON"}, "rows": [{"var": "ac_shop"}],
                                         "missing": "show"})
    labels = [v["label"] for v in shown["rows"][0]["values"]]
    assert "Not stated" in labels


def test_small_cells_suppressed_and_values_withheld(engine, spec_base):
    spec = spec_base | {"base": {"all": [{"var": "h_province", "eq": "PE"}, {"var": "h_age_band", "eq": "65+"},
                                         {"var": "h_income_quintile", "eq": "Q5"}]},
                        "rows": [{"var": "ac_pod"}]}
    cell = engine.tabulate(spec)["rows"][0]["values"][0]["cells"]["total"]
    assert cell["flag"] == "F"
    assert cell["col_pct"] is None and cell["weighted_count"] is None


def test_caution_flag_when_cv_high(engine, spec_base):
    spec = spec_base | {"base": {"var": "h_province", "eq": "ON"}, "rows": [{"var": "ac_pod"}],
                        "columns": [{"var": "h_age_band"}]}
    res = engine.tabulate(spec)
    flags = {c["flag"] for v in res["rows"][0]["values"] for c in v["cells"].values()}
    rule = engine.rule
    for v in res["rows"][0]["values"]:
        for c in v["cells"].values():
            if c["flag"] == "E":
                assert rule["caution_cv_pct"] < c["cv_pct"] <= rule["suppress_cv_pct"]
    assert "E" in flags


@pytest.mark.parametrize("bad, msg", [
    ({"rows": [{"var": 'ac_pod" OR 1=1 --'}]}, "does not match"),
    ({"rows": [{"var": "no_such_var"}]}, "unknown variable"),
    ({"rows": [{"var": "ac_pod"}], "base": {"var": "h_province", "eq": "ZZ"}}, "not a code"),
    ({"rows": [{"var": "ac_pod"}], "release_id": "cius_2099"}, "published release"),
    ({"rows": [{"var": "ac_pod"}], "estimate_type": "model_based_sizing"}, "Census"),
])
def test_invalid_specs_rejected(engine, spec_base, bad, msg):
    spec = spec_base | {"base": {"var": "h_province", "eq": "ON"}} | bad
    with pytest.raises(SpecError) as e:
        engine.tabulate(spec)
    assert msg in str(e.value)
