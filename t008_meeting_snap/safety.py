"""Safety helpers for truncation, logging, and rate limiting."""
from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque, Dict


def truncate(value: str, limit: int) -> str:
    """Return ``value`` limited to ``limit`` characters."""

    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return value[:limit]


def sanitize_for_log(value: str, *, limit: int = 256) -> str:
    """Return a printable, length-limited string safe for logging."""

    sanitized = value.replace("\r", " ").replace("\n", " ")
    sanitized = " ".join(sanitized.split())
    sanitized = "".join(ch for ch in sanitized if ch.isprintable())
    return truncate(sanitized, limit)


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests < 0:
            raise ValueError("max_requests must be non-negative")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: Dict[str, Deque[float]] = {}
        self._lock = Lock()

    def allow(self, identity: str, *, now: float | None = None) -> bool:
        """Return True if the request identified by ``identity`` is allowed."""

        if self.max_requests == 0:
            return False
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            events = self._events.setdefault(identity, deque())
            cutoff = timestamp - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.max_requests:
                return False
            events.append(timestamp)
            return True
