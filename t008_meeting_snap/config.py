"""Configuration helpers for the Meeting Snap application."""
from __future__ import annotations

import os

_DEFAULT_PROVIDER = "logic"
_DEFAULT_TIMEOUT_MS = 10_000
_DEFAULT_MAX_CHARS = 8000


def _read_int(name: str, default: int) -> int:
    """Return a positive integer configuration value from the environment."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def get_provider() -> str:
    """Return the configured extraction provider identifier."""

    provider = os.getenv("MEETING_SNAP_PROVIDER", "").strip().lower()
    return provider or _DEFAULT_PROVIDER


def get_timeout_ms() -> int:
    """Return the request timeout in milliseconds for model providers."""

    return _read_int("MEETING_SNAP_TIMEOUT_MS", _DEFAULT_TIMEOUT_MS)


def get_max_chars() -> int:
    """Return the maximum allowed transcript length in characters."""

    return _read_int("MEETING_SNAP_MAX_CHARS", _DEFAULT_MAX_CHARS)
