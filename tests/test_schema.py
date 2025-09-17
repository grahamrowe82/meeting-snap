"""Unit tests for the Meeting Snap schema layer."""

from __future__ import annotations

import importlib

import pytest

from t008_meeting_snap import schema


def test_validate_snapshot_accepts_valid_payload() -> None:
    payload = {
        "decisions": ["  Launch approved  "],
        "actions": [
            {
                "action": " Follow up with legal on contract review " + "x" * 200,
                "owner": "Alex",
                "due": "Friday",
            }
        ],
        "questions": ["Timeline for beta?"],
        "risks": ["Vendor timeline uncertain."],
        "next_checkin": "Next Tuesday",
    }

    snapshot = schema.validate_snapshot(payload)

    assert snapshot["decisions"] == ["Launch approved"]
    assert snapshot["actions"][0]["action"].startswith(
        "Follow up with legal on contract review"
    )
    assert len(snapshot["actions"][0]["action"]) == 240
    assert snapshot["actions"][0]["owner"] == "Alex"
    assert snapshot["actions"][0]["due"] == "Friday"
    assert snapshot["questions"] == ["Timeline for beta?"]
    assert snapshot["risks"] == ["Vendor timeline uncertain."]
    assert snapshot["next_checkin"] == "Next Tuesday"


def test_validate_snapshot_rejects_bad_types() -> None:
    payload = {
        "decisions": "not-a-list",
        "actions": [],
        "questions": [],
        "risks": [],
        "next_checkin": None,
    }

    with pytest.raises(TypeError):
        schema.validate_snapshot(payload)


def test_oversize_lists_are_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEETING_SNAP_MAX_ITEMS", "50")

    payload = {
        "decisions": [f"Decision {i}" for i in range(200)],
        "actions": [],
        "questions": [],
        "risks": [],
        "next_checkin": None,
    }

    importlib.reload(schema)
    try:
        snapshot = schema.validate_snapshot(payload)
        assert len(snapshot["decisions"]) == 50
    finally:
        monkeypatch.delenv("MEETING_SNAP_MAX_ITEMS", raising=False)
        importlib.reload(schema)


def test_validate_snapshot_returns_empty_for_non_mapping() -> None:
    snapshot = schema.validate_snapshot("not-a-dict")

    assert snapshot == schema.UI_EMPTY
    assert snapshot is not schema.UI_EMPTY
    assert snapshot["decisions"] is not schema.UI_EMPTY["decisions"]
