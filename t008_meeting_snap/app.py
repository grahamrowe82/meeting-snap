"""Flask application for the Meeting Snap baseline slice."""

from __future__ import annotations

from typing import Mapping

from flask import Flask, render_template, request

from . import config, extractor, schema

app = Flask(__name__)


def _model_assist_enabled(provider: str) -> bool:
    return (provider or "").strip().lower() != "logic"


def _render_page(
    transcript: str,
    snapshot: Mapping[str, object],
    error: str | None,
    provider: str,
    max_chars: int,
) -> str:
    return render_template(
        "index.html",
        transcript=transcript,
        snapshot=snapshot,
        error=error,
        model_assist=_model_assist_enabled(provider),
        max_chars=max_chars,
    )


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
    transcript = request.form.get("transcript", "")

    if not transcript:
        return _render_page(
            transcript="",
            snapshot=schema.UI_EMPTY,
            error=None,
            provider=provider,
            max_chars=max_chars,
        )

    if len(transcript) > max_chars:
        return _render_page(
            transcript=transcript,
            snapshot=schema.UI_EMPTY,
            error=f"Trim input to {max_chars:,} characters.",
            provider=provider,
            max_chars=max_chars,
        )

    timeout_ms = config.get_timeout_ms()
    snapshot = extractor.extract_snapshot(transcript, provider, timeout_ms)
    return _render_page(
        transcript=transcript,
        snapshot=snapshot,
        error=None,
        provider=provider,
        max_chars=max_chars,
    )


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
