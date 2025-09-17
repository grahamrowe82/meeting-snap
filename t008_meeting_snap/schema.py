"""Pydantic schema definitions for Meeting Snap snapshots."""
from __future__ import annotations

"""Pydantic schema definitions for Meeting Snap snapshots."""

from typing import List, Optional

from pydantic import BaseModel, Field, validator


MAX_ITEMS = 10
MAX_TEXT_LENGTH = 120


class Action(BaseModel):
    """Schema describing a single action item in the snapshot."""

    action: str
    owner: Optional[str] = None
    due: Optional[str] = None

    @validator("action", pre=True)
    def _ensure_action_present(cls, value: object) -> str:
        if value is None:
            raise ValueError("action text is required")
        if not isinstance(value, str):
            raise TypeError("action must be a string")
        value = value.strip()
        if not value:
            raise ValueError("action text cannot be empty")
        return _clamp_text(value)

    @validator("owner", "due", pre=True)
    def _normalize_optional_fields(cls, value: object) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("optional fields must be strings or null")
        value = value.strip()
        if not value:
            return None
        return _clamp_text(value)


class Snapshot(BaseModel):
    """Schema for the full meeting snapshot consumed by the UI."""

    decisions: List[str] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    next_checkin: Optional[str] = None

    @validator("decisions", "questions", "risks", pre=True)
    def _default_list(cls, value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        raise TypeError("expected a list")

    @validator("actions", pre=True)
    def _default_actions(cls, value: object) -> List[Action]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        raise TypeError("actions must be a list")

    @validator("decisions", "questions", "risks", each_item=True)
    def _normalize_strings(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("entries must be strings")
        value = value.strip()
        if not value:
            raise ValueError("entries cannot be empty")
        return _clamp_text(value)

    @validator("decisions", "questions", "risks", "actions")
    def _limit_collection_size(cls, value: List[object]) -> List[object]:
        if len(value) > MAX_ITEMS:
            raise ValueError("too many items supplied")
        return value

    @validator("next_checkin", pre=True)
    def _normalize_next_checkin(cls, value: object) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("next_checkin must be a string or null")
        value = value.strip()
        if not value:
            return None
        return _clamp_text(value)


def empty_snapshot() -> dict:
    """Return the canonical empty snapshot structure expected by the UI."""

    return {
        "decisions": [],
        "actions": [],
        "questions": [],
        "risks": [],
        "next_checkin": None,
    }


def _clamp_text(value: str) -> str:
    """Clamp a piece of text to the maximum allowed length."""

    return value[:MAX_TEXT_LENGTH]
