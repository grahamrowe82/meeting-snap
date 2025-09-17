"""Runtime checks ensuring the CLI entry point requires real Flask."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "tests" / "_stubs"


def _pythonpath_with_stubs(env: dict[str, str]) -> str:
    """Return a PYTHONPATH that ensures the Flask stub appears first."""

    parts = [str(STUBS), str(ROOT)]
    existing = env.get("PYTHONPATH")
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def test_module_entry_point_rejects_stub_runtime() -> None:
    """Running the app as a module should not accept the Flask test stub."""

    env = os.environ.copy()
    env["PYTHONPATH"] = _pythonpath_with_stubs(env)
    env["MEETING_SNAP_SKIP_RUN"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "t008_meeting_snap.app"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "Real Flask is required" in result.stderr
