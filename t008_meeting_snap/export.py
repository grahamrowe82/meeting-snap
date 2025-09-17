"""Utilities for exporting Meeting Snap data to markdown."""
from __future__ import annotations

from typing import Mapping, Sequence

from . import schema

_PLACEHOLDER = "—"


def to_markdown(snapshot: Mapping[str, object]) -> bytes:
    """Return a UTF-8 encoded markdown export of ``snapshot``.

    Parameters
    ----------
    snapshot:
        A mapping representing the Meeting Snap summary structure.
    """

    normalized = _normalize_snapshot(snapshot)

    decisions = _format_string_section(normalized.get("decisions", ()))
    actions = _format_actions_section(normalized.get("actions", ()))
    questions = _format_string_section(normalized.get("questions", ()))
    risks = _format_string_section(normalized.get("risks", ()))
    next_checkin = _format_single_value(normalized.get("next_checkin"))

    lines = [
        "# Meeting Snap",
        "## Decisions",
        *decisions,
        "## Actions (owner — due)",
        *actions,
        "## Questions",
        *questions,
        "## Risks",
        *risks,
        "## Next check-in",
        next_checkin,
    ]

    markdown = "\n".join(lines) + "\n"
    return markdown.encode("utf-8")


def _normalize_snapshot(snapshot: Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(snapshot, Mapping):
        candidate: Mapping[str, object] = dict(snapshot)
    else:
        candidate = schema.empty_snapshot()
    try:
        return schema.validate_snapshot(candidate)
    except Exception:
        return schema.empty_snapshot()


def _sanitize(value: str) -> str:
    collapsed = " ".join(value.replace("\r", "\n").split())
    return collapsed.strip()


def _format_string_section(items: Sequence[str]) -> list[str]:
    formatted = []
    for raw in items:
        text = _sanitize(str(raw))
        if text:
            formatted.append(f"- {text}")
    if not formatted:
        formatted.append(f"- {_PLACEHOLDER}")
    return formatted


def _format_actions_section(actions: Sequence[Mapping[str, object]]) -> list[str]:
    formatted = []
    for item in actions:
        if not isinstance(item, Mapping):
            continue
        action_text = _sanitize(str(item.get("action", ""))) or _PLACEHOLDER
        owner = item.get("owner")
        due = item.get("due")
        owner_text = _sanitize(str(owner)) if isinstance(owner, str) else ""
        due_text = _sanitize(str(due)) if isinstance(due, str) else ""
        if not owner_text:
            owner_text = _PLACEHOLDER
        if not due_text:
            due_text = _PLACEHOLDER
        formatted.append(
            f"- {action_text} ({owner_text} — {due_text})"
        )
    if not formatted:
        formatted.append(f"- {_PLACEHOLDER}")
    return formatted


def _format_single_value(value: object) -> str:
    if isinstance(value, str):
        text = _sanitize(value)
        if text:
            return f"- {text}"
    return f"- {_PLACEHOLDER}"
