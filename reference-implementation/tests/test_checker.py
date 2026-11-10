import pytest

from pumfai.checker import check
from pumfai.render import display_table


@pytest.fixture(scope="module")
def result(engine):
    spec = {"spec_version": "1.0", "survey": "cius", "release_id": "cius_synth_2022", "weight": "wtpp",
            "measures": ["col_pct"], "base": {"var": "h_province", "eq": "ON"},
            "rows": [{"var": "ac_pod"}], "columns": [{"var": "h_gender"}]}
    return engine.tabulate(spec)


def test_accepts_numbers_from_table(result):
    cells = display_table(result)
    yes = next(c for c in cells if c["row_value"] == "Yes" and c["column"] == "Total")
    men = next(c for c in cells if c["row_value"] == "Yes" and c["column"] == "Men+")
    women = next(c for c in cells if c["row_value"] == "Yes" and c["column"] == "Women+")
    gap = round(abs(men["pct"] - women["pct"]), 1)
    text = (f"{yes['pct']:.1f}% of Ontario Internet users listen to podcasts, about {round(yes['pct'])}%. "
            f"That is {yes['count'] / 1e6:.1f} million people. Men+ are at {men['pct']:.1f}% "
            f"and Women+ at {women['pct']:.1f}%, a gap of {gap} percentage points.")
    assert check(text, result) == []


def test_rejects_invented_numbers(result):
    problems = check("About 97.3% listen to podcasts, or 42.1 million people, with an index of 999.", result)
    assert len(problems) == 3


def test_allows_numbers_from_question_and_labels(result):
    assert check("Among Ontarians aged 25 to 44 in 2022...", result, extra_text="aged 25 to 44 in 2022") == []
