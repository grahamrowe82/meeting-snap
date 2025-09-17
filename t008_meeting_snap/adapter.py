"""Utilities to adapt validated snapshots for template rendering."""
from __future__ import annotations

from typing import Any, Dict

from .schema import Snapshot


def to_ui(snapshot: Snapshot) -> Dict[str, Any]:
    """Return a plain dictionary representation safe for template rendering."""

    payload = snapshot.dict()
    payload["actions"] = [
        {"action": item.action, "owner": item.owner, "due": item.due}
        for item in snapshot.actions
    ]
    return payload
