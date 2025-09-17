"""Tests for the deterministic fake LLM adapter."""
from __future__ import annotations

from t008_meeting_snap import llm_fake
from t008_meeting_snap.schema import validate_snapshot


def test_llm_fake_extract_produces_valid_snapshot() -> None:
    raw = llm_fake.extract("Team decided to adopt the new process.")
    snapshot = validate_snapshot(raw)

    assert set(snapshot.keys()) == {
        "decisions",
        "actions",
        "questions",
        "risks",
        "next_checkin",
    }
    assert snapshot["decisions"] and all(isinstance(item, str) for item in snapshot["decisions"])

    assert snapshot["actions"] and isinstance(snapshot["actions"], list)
    action = snapshot["actions"][0]
    assert set(action.keys()) == {"action", "owner", "due"}
    assert isinstance(action["action"], str) and action["action"].strip()
    owner = action["owner"]
    assert owner is None or (isinstance(owner, str) and owner.strip())
    due = action["due"]
    assert due is None or (isinstance(due, str) and due.strip())

    assert snapshot["questions"] and all(
        isinstance(item, str) and item.strip() for item in snapshot["questions"]
    )
    assert snapshot["risks"] and all(
        isinstance(item, str) and item.strip() for item in snapshot["risks"]
    )
    assert snapshot["next_checkin"] is None or isinstance(snapshot["next_checkin"], str)
