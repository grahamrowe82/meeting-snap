"""Flask application for the Meeting Snap baseline slice."""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Mapping

from flask import Flask, Response, render_template, request

from . import config, export, extractor, metrics, schema
from .safety import RateLimiter, sanitize_for_log, truncate

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.setdefault(
    "RATE_LIMITER",
    RateLimiter(config.get_rate_limit(), config.get_rate_window_s()),
)

_SNAPSHOT_CACHE: dict[str, Mapping[str, object]] = {}


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
    download_ready: bool = False,
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
        download_ready=download_ready,
    )


def _get_rate_limiter() -> RateLimiter:
    limiter = app.config.get("RATE_LIMITER")
    if isinstance(limiter, RateLimiter):
        return limiter

    requests_limit = int(app.config.get("RATE_LIMIT_REQUESTS", config.get_rate_limit()))
    window_seconds = float(
        app.config.get("RATE_LIMIT_WINDOW_SECONDS", config.get_rate_window_s())
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


def _has_snapshot(identity: str) -> bool:
    return identity in _SNAPSHOT_CACHE


def _store_snapshot(identity: str, snapshot: Mapping[str, object]) -> Mapping[str, object]:
    stored = copy.deepcopy(snapshot)
    _SNAPSHOT_CACHE[identity] = stored
    return stored


def _get_snapshot(identity: str) -> Mapping[str, object] | None:
    return _SNAPSHOT_CACHE.get(identity)


@app.get("/")
def index() -> str:
    metrics.inc("requests_total")
    provider = config.get_provider()
    max_chars = config.get_max_chars()
    identity = _client_identity()
    download_ready = _has_snapshot(identity)
    return _render_page(
        transcript="",
        snapshot=schema.UI_EMPTY,
        error=None,
        provider=provider,
        max_chars=max_chars,
        download_ready=download_ready,
    )


@app.post("/snap")
def snap() -> Response | str:
    metrics.inc("requests_total")
    provider = config.get_provider()
    provider_id = (provider or "").strip().lower()
    max_chars = config.get_max_chars()
    limiter = _get_rate_limiter()
    identity = _client_identity()
    download_ready = _has_snapshot(identity)
    raw_transcript = request.form.get("transcript", "")
    input_chars = len(raw_transcript)
    truncated = bool(raw_transcript and len(raw_transcript) > max_chars)
    if truncated:
        metrics.inc("truncations_total")
    transcript = truncate(raw_transcript, max_chars)

    used_model_assist = False
    duration_ms = 0.0
    tokens: int | None = None
    fallback_reason: str | None = None

    if not limiter.allow(identity):
        metrics.inc("rate_limit_hits_total")
        logger.warning("Rate limit exceeded for %s", sanitize_for_log(identity))
        body = _render_page(
            transcript="",
            snapshot=schema.UI_EMPTY,
            error="Too many requests. Try again later.",
            provider=provider,
            max_chars=max_chars,
            download_ready=download_ready,
        )
        _log_snap_event(
            provider_id,
            used_model_assist,
            input_chars,
            truncated,
            duration_ms,
            fallback="rate_limit",
            tokens=tokens,
        )
        response = Response(body)
        response.status_code = 429
        return response

    if not transcript:
        body = _render_page(
            transcript="",
            snapshot=schema.UI_EMPTY,
            error=None,
            provider=provider,
            max_chars=max_chars,
            download_ready=download_ready,
        )
        _log_snap_event(
            provider_id,
            used_model_assist,
            input_chars,
            truncated,
            duration_ms,
            fallback="empty_input",
            tokens=tokens,
        )
        return body

    if truncated:
        body = _render_page(
            transcript=transcript,
            snapshot=schema.UI_EMPTY,
            error=f"Trim input to {max_chars:,} characters.",
            provider=provider,
            max_chars=max_chars,
            download_ready=download_ready,
        )
        _log_snap_event(
            provider_id,
            used_model_assist,
            input_chars,
            truncated,
            duration_ms,
            fallback="input_too_long",
            tokens=tokens,
        )
        return body

    timeout_ms = config.get_timeout_ms()
    start_time = time.perf_counter() if provider_id != "logic" else None
    snapshot, used_model_assist = extractor.extract_snapshot(transcript, provider, timeout_ms)
    if start_time is not None:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics.inc("llm_calls_total")
        metrics.inc("llm_latency_ms_sum", value=duration_ms)

    path_label = _snap_path_label(provider_id, used_model_assist)
    if path_label == "fallback" and provider_id != "logic":
        fallback_reason = "provider_error"
    metrics.inc("snaps_total", {"path": path_label})

    if used_model_assist and provider_id != "logic":
        tokens = _approximate_token_usage(transcript, snapshot)
        if tokens is not None:
            metrics.inc("llm_tokens_total", value=tokens)

    snapshot = _store_snapshot(identity, snapshot)
    download_ready = True

    body = _render_page(
        transcript=transcript,
        snapshot=snapshot,
        error=None,
        provider=provider,
        max_chars=max_chars,
        model_assist_used=used_model_assist,
        model_assist_attempted=provider_id != "logic",
        download_ready=download_ready,
    )
    _log_snap_event(
        provider_id,
        used_model_assist,
        input_chars,
        truncated,
        duration_ms,
        fallback=fallback_reason,
        tokens=tokens,
    )
    return body


@app.get("/download.md")
def download_markdown() -> Response:
    metrics.inc("requests_total")
    identity = _client_identity()
    snapshot = _get_snapshot(identity)
    if snapshot is None:
        response = Response(b"")
        response.status_code = 404
        return response

    payload = export.to_markdown(snapshot)
    response = Response(payload)
    response.content_type = "text/markdown; charset=utf-8"
    if hasattr(response, 'headers'):
        response.headers["Content-Disposition"] = "attachment; filename=\"meeting-snap.md\""
    return response


@app.get("/metrics")
def metrics_endpoint() -> Response:
    metrics.inc("requests_total")
    payload = metrics.to_prometheus()
    response = Response(payload)
    response.content_type = "text/plain; charset=utf-8"
    return response


def _snap_path_label(provider_id: str, used_model_assist: bool) -> str:
    provider_key = provider_id or "logic"
    if provider_key == "logic":
        return "logic"
    if used_model_assist:
        if provider_key in {"fake", "openai"}:
            return provider_key
        return provider_key
    return "fallback"


def _approximate_token_usage(transcript: str, snapshot: Mapping[str, object]) -> int | None:
    try:
        from . import llm
    except Exception:  # pragma: no cover - defensive import guard
        return None

    try:
        prompt = llm.build_prompt(transcript)
    except Exception:  # pragma: no cover - defensive fall back
        prompt = transcript or ""
    try:
        response = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        response = ""
    approx = int((len(prompt) + len(response)) / 4)
    return max(approx, 0)


def _log_snap_event(
    provider_id: str,
    used_model_assist: bool,
    input_chars: int,
    truncated: bool,
    duration_ms: float,
    *,
    fallback: str | None,
    tokens: int | None,
) -> None:
    provider_value = sanitize_for_log(provider_id) if provider_id else ""
    fallback_value = sanitize_for_log(fallback) if fallback else None
    payload = {
        "event": "snap",
        "provider": provider_value,
        "used_assist": used_model_assist,
        "input_chars": int(input_chars),
        "truncated": truncated,
        "duration_ms": round(duration_ms, 3),
        "fallback": fallback_value,
        "tokens": tokens,
    }
    logging.info(json.dumps(payload))


def _ensure_real_flask_runtime() -> None:
    """Validate that the runtime Flask import is not satisfied by a test stub."""

    module = sys.modules.get("flask")
    module_file = getattr(module, "__file__", None) if module else None
    if not module_file:
        # If Flask is not importable the normal ModuleNotFoundError will surface.
        return

    parts = Path(module_file).resolve().parts
    if "_stubs" in parts:
        raise RuntimeError(
            "Real Flask is required to run the Meeting Snap app; the test stub is on sys.path."
        )


if __name__ == "__main__":  # pragma: no cover
    _ensure_real_flask_runtime()
    if os.environ.get("MEETING_SNAP_SKIP_RUN"):
        logging.getLogger(__name__).info("MEETING_SNAP_SKIP_RUN set; skipping app.run().")
    else:
        app.run(debug=True)
