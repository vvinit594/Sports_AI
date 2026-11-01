from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cricsheet"


@pytest.fixture
def cricsheet_dir() -> Path:
    return FIXTURE_DIR


def cricsheet_path(name: str) -> Path:
    return FIXTURE_DIR / name
