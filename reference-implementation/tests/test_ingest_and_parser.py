import json
import shutil

import pytest

from pumfai import spss
from pumfai.ingest import QualityError, ingest

STATCAN_STYLE = """
* Example in the style of a StatCan syntax file.
DATA LIST FILE='x.txt' /
  PUMFID 1-5 PROV 6-7 Q_010 8 WTPP 9-20 (4)
.
VARIABLE LABELS
  PUMFID "Record id"
  /PROV "Province"
  /Q_010 'Any internet use'
.
VALUE LABELS
  PROV
    10 "Newfoundland and Labrador"
    35 "Ontario"
  /Q_010
    1 "Yes"
    2 "No"
    6 "Valid skip"
    9 "Not stated"
.
MISSING VALUES Q_010 (6, 9).
EXECUTE.
"""


def test_parses_statcan_style_syntax():
    cols = spss.parse(STATCAN_STYLE)
    assert (cols["PROV"].start, cols["PROV"].end) == (6, 7)
    assert cols["WTPP"].decimals == 4
    assert cols["Q_010"].label == "Any internet use"
    assert cols["PROV"].value_labels["35"] == "Ontario"
    assert cols["Q_010"].missing == {"6", "9"}
    assert spss.missing_type("6", cols["Q_010"]) == "valid_skip"
    assert spss.missing_type("9", cols["Q_010"]) == "not_stated"
    assert spss.missing_type("1", cols["Q_010"]) == "valid"


def test_generated_syntax_round_trips(data_root):
    sps = next((data_root / "raw" / "cius_synth_2022").glob("*.sps")).read_text()
    cols = spss.parse(sps)
    assert len([c for c in cols if c.startswith("WTBS_")]) == 50
    assert cols["AC_POD"].missing == {"6", "7", "8", "9"}


def test_catalog_has_universes_and_missing_types(release_dir):
    cat = json.loads((release_dir / "catalog.json").read_text())
    v = {x["code"]: x for x in cat["variables"]}
    assert v["ac_pod"]["universe_expr"] == {"var": "ui_010", "eq": 1}
    assert {x["missing_type"] for x in v["ac_pod"]["values"]} >= {"valid", "valid_skip", "not_stated"}
    assert cat["release"]["quality_report"]["status"] == "passed"


def test_quality_rule_blocks_bad_release(data_root, tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(data_root / "raw" / "cius_synth_2022", raw)
    guide = json.loads((raw / "user_guide.json").read_text())
    guide["record_count"] += 1
    (raw / "user_guide.json").write_text(json.dumps(guide))
    with pytest.raises(QualityError, match="record count"):
        ingest(raw, tmp_path / "out")


def test_value_labels_for_names_containing_digits():
    """Regression: names like Q_010 were cut at the first digit and lost their labels."""
    cols = spss.parse(STATCAN_STYLE)
    assert cols["Q_010"].value_labels == {"1": "Yes", "2": "No", "6": "Valid skip", "9": "Not stated"}


def test_quality_rule_blocks_unlabelled_categorical(data_root, tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(data_root / "raw" / "cius_synth_2022", raw)
    sps = next(raw.glob("*.sps"))
    text = sps.read_text()
    start = text.index("  /FQ_010")
    end = text.index("  /AC_STRM")
    sps.write_text(text[:start] + text[end:])
    with pytest.raises(QualityError, match="without value labels"):
        ingest(raw, tmp_path / "out")
