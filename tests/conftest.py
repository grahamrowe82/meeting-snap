"""Test configuration ensuring project modules are importable."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from t008_meeting_snap import app as app_module


@pytest.fixture(autouse=True)
def reset_snapshot_cache() -> None:
    app_module._SNAPSHOT_CACHE.clear()
    yield
    app_module._SNAPSHOT_CACHE.clear()
