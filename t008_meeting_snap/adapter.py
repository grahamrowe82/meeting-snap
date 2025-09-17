"""Utilities to adapt validated snapshots for template rendering."""
from __future__ import annotations

from typing import Any, Dict, List


def to_ui(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Return a plain dictionary representation safe for template rendering."""

    actions: List[Dict[str, Any]] = [
        {"action": item["action"], "owner": item["owner"], "due": item["due"]}
        for item in snapshot["actions"]
    ]
    return {
        "decisions": list(snapshot["decisions"]),
        "actions": actions,
        "questions": list(snapshot["questions"]),
        "risks": list(snapshot["risks"]),
        "next_checkin": snapshot["next_checkin"],
    }
