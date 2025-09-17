"""Deterministic fake LLM extractor used in unit tests."""
from __future__ import annotations

from typing import Any, Dict

from .schema import empty_snapshot


def extract(transcript: str) -> Dict[str, Any]:
    """Return a predictable schema-valid snapshot for testing."""

    snapshot = empty_snapshot()
    snapshot["decisions"] = ["Use the fake LLM output for validation"]
    snapshot["actions"] = [
        {
            "action": "Share meeting notes with the wider team",
            "owner": "Alex",
            "due": "Next Monday",
        }
    ]
    snapshot["questions"] = ["Any blockers before launch?"]
    snapshot["risks"] = ["Timeline depends on vendor availability."]
    snapshot["next_checkin"] = "Next Tuesday"
    return snapshot
