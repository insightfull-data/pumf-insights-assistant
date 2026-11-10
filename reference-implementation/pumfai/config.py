from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return Path(os.getenv("PUMFAI_DATA_DIR", ROOT / "data"))


def release_id() -> str:
    return os.getenv("PUMFAI_RELEASE", "cius_synth_2022")


def release_dir() -> Path:
    return data_dir() / "release" / release_id()


def raw_dir() -> Path:
    return data_dir() / "raw" / release_id()


def log_dir() -> Path:
    return Path(os.getenv("PUMFAI_LOG_DIR", ROOT / "logs"))
