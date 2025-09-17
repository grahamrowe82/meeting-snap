"""Integration tests for the Flask app routes."""
from __future__ import annotations

from t008_meeting_snap.app import app

app.config.update(TESTING=True)


def test_index_get_shows_badge_and_privacy_note(monkeypatch) -> None:
    """The home page renders with the status badge and privacy messaging."""

    monkeypatch.delenv("MEETING_SNAP_PROVIDER", raising=False)
    monkeypatch.delenv("MEETING_SNAP_MAX_CHARS", raising=False)

    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Model assist: OFF" in body
    assert "Don’t paste regulated/PII." in body
    assert "Privacy note:" in body
    assert 'maxlength="8000"' in body


def test_snap_post_uses_fake_provider(monkeypatch) -> None:
    """Posting a transcript with the fake provider returns fake LLM output."""

    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "fake")
    monkeypatch.delenv("MEETING_SNAP_MAX_CHARS", raising=False)

    with app.test_client() as client:
        response = client.post("/snap", data={"transcript": "Quarterly sync"})

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Model assist: ON" in body
    assert "Use the fake LLM output for validation" in body
    assert "Share meeting notes with the wider team" in body
    assert "Download .md" in body


def test_download_requires_snapshot(monkeypatch) -> None:
    """Downloading markdown without a snapshot returns 404."""

    monkeypatch.delenv("MEETING_SNAP_PROVIDER", raising=False)

    with app.test_client() as client:
        response = client.get("/download.md")

    assert response.status_code == 404


def test_download_after_snap_returns_markdown(monkeypatch) -> None:
    """After creating a snapshot the markdown download is available."""

    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "fake")

    with app.test_client() as client:
        post_response = client.post("/snap", data={"transcript": "Kickoff call"})
        assert post_response.status_code == 200
        download = client.get("/download.md")

    assert download.status_code == 200
    assert download.content_type == "text/markdown; charset=utf-8"
    assert download.headers["Content-Disposition"] == "attachment; filename=\"meeting-snap.md\""
    body = download.get_data(as_text=True)
    assert "# Meeting Snap" in body
    assert "- Use the fake LLM output for validation" in body
    assert "- Share meeting notes with the wider team (Alex — Next Monday)" in body
    assert "- Any blockers before launch?" in body
    assert "- Timeline depends on vendor availability." in body
    assert "- Next Tuesday" in body
