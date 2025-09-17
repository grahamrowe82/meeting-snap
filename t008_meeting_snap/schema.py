"""Snapshot validation helpers for Meeting Snap."""
from __future__ import annotations

from typing import Any, Dict, List, MutableMapping, Optional


MAX_ITEMS = 10
MAX_TEXT_LENGTH = 120
_REQUIRED_KEYS = ("decisions", "actions", "questions", "risks", "next_checkin")


def _build_ui_empty() -> Dict[str, Any]:
    """Return a new empty snapshot structure."""

    return {
        "decisions": [],
        "actions": [],
        "questions": [],
        "risks": [],
        "next_checkin": None,
    }


UI_EMPTY: Dict[str, Any] = _build_ui_empty()


def _copy_ui_empty() -> Dict[str, Any]:
    """Return a shallow copy of :data:`UI_EMPTY` with fresh lists."""

    return {
        key: list(value) if isinstance(value, list) else value
        for key, value in UI_EMPTY.items()
    }


def empty_snapshot() -> Dict[str, Any]:
    """Return the canonical empty snapshot structure expected by the UI."""

    return _copy_ui_empty()


def validate_snapshot(obj: Any) -> Dict[str, Any]:
    """Validate and normalize a snapshot payload.

    Parameters
    ----------
    obj:
        The raw object to validate.

    Returns
    -------
    dict
        A dictionary ready for rendering by the UI.

    Raises
    ------
    KeyError
        If any required keys are missing from ``obj``.
    TypeError
        If the types of the values are incompatible with the schema.
    ValueError
        If constraints such as empty strings or oversized collections are violated.
    """

    if not isinstance(obj, MutableMapping):
        return _copy_ui_empty()

    _ensure_required_keys(obj)

    decisions = _normalize_string_list(obj.get("decisions"), "decisions")
    actions = _normalize_actions(obj.get("actions"))
    questions = _normalize_string_list(obj.get("questions"), "questions")
    risks = _normalize_string_list(obj.get("risks"), "risks")
    next_checkin = _normalize_optional_string(obj.get("next_checkin"), "next_checkin")

    return {
        "decisions": decisions,
        "actions": actions,
        "questions": questions,
        "risks": risks,
        "next_checkin": next_checkin,
    }


def _ensure_required_keys(obj: MutableMapping[str, Any]) -> None:
    """Ensure that all required keys are present in ``obj``."""

    missing = [key for key in _REQUIRED_KEYS if key not in obj]
    if missing:
        raise KeyError(f"snapshot missing required keys: {', '.join(missing)}")


def _normalize_string_list(value: Any, field: str) -> List[str]:
    """Normalize a list of user-facing strings."""

    items = _coerce_list(value, field)
    return [_normalize_string(item, field) for item in items]


def _coerce_list(value: Any, field: str) -> List[Any]:
    """Return ``value`` as a list enforcing the maximum size constraint."""

    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"{field} must be a list")
    if len(value) > MAX_ITEMS:
        raise ValueError(f"{field} cannot contain more than {MAX_ITEMS} items")
    return value


def _normalize_string(value: Any, field: str) -> str:
    """Return a normalized and length-clamped string value."""

    if not isinstance(value, str):
        raise TypeError(f"{field} entries must be strings")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} entries cannot be empty")
    return _clamp_text(text)


def _normalize_optional_string(value: Any, field: str) -> Optional[str]:
    """Normalize an optional string value."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string or null")
    text = value.strip()
    if not text:
        return None
    return _clamp_text(text)


def _normalize_actions(value: Any) -> List[Dict[str, Optional[str]]]:
    """Normalize the list of action dictionaries."""

    items = _coerce_list(value, "actions")
    normalized: List[Dict[str, Optional[str]]] = []
    for item in items:
        if not isinstance(item, MutableMapping):
            raise TypeError("actions entries must be dictionaries")
        if "action" not in item:
            raise ValueError("actions entries must include an 'action' field")
        action_text = _normalize_string(item.get("action"), "actions.action")
        owner = _normalize_optional_string(item.get("owner"), "actions.owner")
        due = _normalize_optional_string(item.get("due"), "actions.due")
        normalized.append({"action": action_text, "owner": owner, "due": due})
    return normalized


def _clamp_text(value: str) -> str:
    """Clamp a piece of text to the maximum allowed length."""

    return value[:MAX_TEXT_LENGTH]
