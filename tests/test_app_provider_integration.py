"""Integration checks for provider success and failure flows in the Flask app."""

from __future__ import annotations

from importlib import reload

from t008_meeting_snap import llm_openai
from t008_meeting_snap import app as app_module
from t008_meeting_snap import metrics as metrics_module

app_module.app.config.update(TESTING=True)


def _reset_metrics():
    metrics = reload(metrics_module)
    app_module.metrics = metrics
    return metrics


def _client():
    app_module.app.config["TESTING"] = True
    if hasattr(app_module, "_SNAPSHOT_CACHE"):
        app_module._SNAPSHOT_CACHE.clear()
    return app_module.app.test_client()


def test_openai_success_shows_badge_and_metrics(monkeypatch):
    metrics = _reset_metrics()
    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "openai")
    monkeypatch.setattr(
        llm_openai,
        "extract",
        lambda *_: {
            "decisions": ["A"],
            "actions": [],
            "questions": [],
            "risks": [],
            "next_checkin": None,
        },
    )

    client = _client()
    before = dict(metrics.snaps_total)
    response = client.post("/snap", data={"transcript": "x"})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Model assist: ON" in html
    after = dict(metrics.snaps_total)
    assert after.get("openai", 0) == before.get("openai", 0) + 1


def test_openai_failure_shows_banner_and_fallback(monkeypatch):
    metrics = _reset_metrics()
    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "openai")
    monkeypatch.setattr(
        llm_openai,
        "extract",
        lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    client = _client()
    before = dict(metrics.snaps_total)
    response = client.post("/snap", data={"transcript": "x"})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Model assist: OFF" in html
    assert "Model assist unavailable" in html
    after = dict(metrics.snaps_total)
    assert after.get("fallback", 0) == before.get("fallback", 0) + 1
