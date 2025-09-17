"""Ensure the app falls back to baseline extraction on provider errors."""

from t008_meeting_snap import extractor
from t008_meeting_snap.app import app

app.config.update(TESTING=True)


def test_snap_falls_back_when_provider_errors(monkeypatch) -> None:
    """A provider failure returns a baseline snapshot with the assist note."""

    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "openai")

    def boom(text: str, provider_id: str, timeout_ms: int) -> dict[str, object]:
        raise RuntimeError("provider failure")

    monkeypatch.setattr(extractor, "_extract_with_provider", boom)

    with app.test_client() as client:
        response = client.post("/snap", data={"transcript": "Daily sync summary."})

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Model assist: OFF" in body
    assert "Model assist unavailable—using baseline." in body
