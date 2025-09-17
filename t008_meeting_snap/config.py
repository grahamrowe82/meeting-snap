"""Configuration helpers for the Meeting Snap application."""
from __future__ import annotations

import os

_DEFAULT_PROVIDER = "logic"
_DEFAULT_TIMEOUT_MS = 10_000
_DEFAULT_MAX_CHARS = 8000
_DEFAULT_MAX_ITEMS = 100
_DEFAULT_MAX_TEXT_LEN = 240
_DEFAULT_RATE_LIMIT = 30
_DEFAULT_RATE_WINDOW_S = 86_400
_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


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


def get_max_items() -> int:
    """Return the maximum number of list items allowed in snapshots."""

    return _read_int("MEETING_SNAP_MAX_ITEMS", _DEFAULT_MAX_ITEMS)


def get_max_text_len() -> int:
    """Return the maximum length for individual snapshot text fields."""

    return _read_int("MEETING_SNAP_MAX_TEXT_LEN", _DEFAULT_MAX_TEXT_LEN)


def get_rate_limit() -> int:
    """Return the maximum number of requests allowed per rate window."""

    return _read_int("MEETING_SNAP_RATE_LIMIT", _DEFAULT_RATE_LIMIT)


def get_rate_window_s() -> int:
    """Return the rate limiting window duration in seconds."""

    return _read_int("MEETING_SNAP_RATE_WINDOW_S", _DEFAULT_RATE_WINDOW_S)


def get_openai_model() -> str:
    """Return the configured OpenAI model identifier."""

    model = os.getenv("OPENAI_MODEL", "").strip()
    return model or _DEFAULT_OPENAI_MODEL
