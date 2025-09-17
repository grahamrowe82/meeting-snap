"""Unit tests for the Meeting Snap schema layer."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from t008_meeting_snap.schema import Snapshot


def test_snapshot_accepts_valid_payload() -> None:
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

    snapshot = Snapshot.parse_obj(payload)

    assert snapshot.decisions == ["Launch approved"]
    assert snapshot.actions[0].action.startswith("Follow up with legal on contract review")
    assert len(snapshot.actions[0].action) == 120
    assert snapshot.actions[0].owner == "Alex"
    assert snapshot.actions[0].due == "Friday"
    assert snapshot.questions == ["Timeline for beta?"]
    assert snapshot.risks == ["Vendor timeline uncertain."]
    assert snapshot.next_checkin == "Next Tuesday"


def test_snapshot_rejects_bad_types() -> None:
    payload = {
        "decisions": "not-a-list",
        "actions": [],
        "questions": [],
        "risks": [],
    }

    with pytest.raises(ValidationError):
        Snapshot.parse_obj(payload)



def test_snapshot_rejects_oversized_arrays() -> None:
    payload = {
        "decisions": [f"Decision {i}" for i in range(11)],
        "actions": [],
        "questions": [],
        "risks": [],
    }

    with pytest.raises(ValidationError):
        Snapshot.parse_obj(payload)
