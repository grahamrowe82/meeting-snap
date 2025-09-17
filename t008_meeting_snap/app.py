"""Flask application for the Meeting Snap baseline slice."""

from __future__ import annotations

from flask import Flask, render_template, request

from .logic import assemble
from .schema import empty_snapshot


MAX_INPUT_CHARS = 8000

app = Flask(__name__)


@app.get("/")
def index() -> str:
    return render_template(
        "index.html",
        transcript="",
        snapshot=empty_snapshot(),
        error=None,
    )


@app.post("/snap")
def snap() -> str:
    transcript = request.form.get("transcript", "")
    if not transcript:
        return render_template(
            "index.html",
            transcript="",
            snapshot=empty_snapshot(),
            error=None,
        )

    if len(transcript) > MAX_INPUT_CHARS:
        return render_template(
            "index.html",
            transcript=transcript,
            snapshot=empty_snapshot(),
            error="Trim input to 8,000 characters.",
        )

    snapshot = assemble(transcript)
    return render_template(
        "index.html",
        transcript=transcript,
        snapshot=snapshot,
        error=None,
    )


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
