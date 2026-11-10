import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session")
def data_root(tmp_path_factory):
    from pumfai.ingest import ingest
    from pumfai.synthetic import generate

    root = tmp_path_factory.mktemp("data")
    ingest(generate(root), root)
    return root


@pytest.fixture(scope="session")
def release_dir(data_root):
    return data_root / "release" / "cius_synth_2022"


@pytest.fixture(scope="session")
def engine(release_dir):
    from pumfai.engine import Engine
    return Engine(release_dir)


@pytest.fixture(scope="session")
def microdata(release_dir):
    import pandas as pd
    return pd.read_parquet(release_dir / "microdata.parquet")


@pytest.fixture
def spec_base():
    return {"spec_version": "1.0", "survey": "cius", "release_id": "cius_synth_2022",
            "weight": "wtpp", "measures": ["col_pct", "index", "cv"], "missing": "exclude"}
