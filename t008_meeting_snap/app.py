"""Flask application for the Meeting Snap baseline slice."""

from __future__ import annotations

import logging
from typing import Mapping

from flask import Flask, Response, render_template, request

from . import config, extractor, schema
from .safety import RateLimiter, sanitize_for_log, truncate

logger = logging.getLogger(__name__)

app = Flask(__name__)

_DEFAULT_RATE_LIMIT_REQUESTS = 60
_DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60.0
app.config.setdefault(
    "RATE_LIMITER",
    RateLimiter(_DEFAULT_RATE_LIMIT_REQUESTS, _DEFAULT_RATE_LIMIT_WINDOW_SECONDS),
)


def _model_assist_enabled(provider: str) -> bool:
    return (provider or "").strip().lower() != "logic"


def _render_page(
    transcript: str,
    snapshot: Mapping[str, object],
    error: str | None,
    provider: str,
    max_chars: int,
    *,
    model_assist_used: bool = False,
    model_assist_attempted: bool = False,
) -> str:
    assist_requested = _model_assist_enabled(provider)
    assist_note = None
    if model_assist_attempted and assist_requested and not model_assist_used:
        assist_note = "Model assist unavailable—using baseline."

    return render_template(
        "index.html",
        transcript=transcript,
        snapshot=snapshot,
        error=error,
        model_assist=model_assist_used,
        model_assist_note=assist_note,
        max_chars=max_chars,
    )


def _get_rate_limiter() -> RateLimiter:
    limiter = app.config.get("RATE_LIMITER")
    if isinstance(limiter, RateLimiter):
        return limiter

    requests_limit = int(app.config.get("RATE_LIMIT_REQUESTS", _DEFAULT_RATE_LIMIT_REQUESTS))
    window_seconds = float(
        app.config.get("RATE_LIMIT_WINDOW_SECONDS", _DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
    )
    limiter = RateLimiter(requests_limit, window_seconds)
    app.config["RATE_LIMITER"] = limiter
    return limiter


def _client_identity() -> str:
    headers = getattr(request, "headers", None)
    if headers is not None:
        forwarded_for = headers.get("X-Forwarded-For", "")  # type: ignore[arg-type]
        if forwarded_for:
            first = forwarded_for.split(",", 1)[0].strip()
            if first:
                return first
    remote_addr = getattr(request, "remote_addr", None)
    if remote_addr:
        return remote_addr
    return "global"


@app.get("/")
def index() -> str:
    provider = config.get_provider()
    max_chars = config.get_max_chars()
    return _render_page(
        transcript="",
        snapshot=schema.UI_EMPTY,
        error=None,
        provider=provider,
        max_chars=max_chars,
    )


@app.post("/snap")
def snap() -> str:
    provider = config.get_provider()
    max_chars = config.get_max_chars()
    limiter = _get_rate_limiter()
    identity = _client_identity()
    if not limiter.allow(identity):
        logger.warning("Rate limit exceeded for %s", sanitize_for_log(identity))
        body = _render_page(
            transcript="",
            snapshot=schema.UI_EMPTY,
            error="Too many requests. Try again later.",
            provider=provider,
            max_chars=max_chars,
        )
        return Response(body, status_code=429)

    raw_transcript = request.form.get("transcript", "")
    transcript = truncate(raw_transcript, max_chars)

    if not transcript:
        return _render_page(
            transcript="",
            snapshot=schema.UI_EMPTY,
            error=None,
            provider=provider,
            max_chars=max_chars,
        )

    if raw_transcript and len(raw_transcript) > max_chars:
        return _render_page(
            transcript=transcript,
            snapshot=schema.UI_EMPTY,
            error=f"Trim input to {max_chars:,} characters.",
            provider=provider,
            max_chars=max_chars,
        )

    timeout_ms = config.get_timeout_ms()
    snapshot, used_model_assist = extractor.extract_snapshot(transcript, provider, timeout_ms)
    return _render_page(
        transcript=transcript,
        snapshot=snapshot,
        error=None,
        provider=provider,
        max_chars=max_chars,
        model_assist_used=used_model_assist,
        model_assist_attempted=True,
    )


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
