"""Metrics regression tests to ensure counters stay wired."""

from importlib import reload
from typing import Any

from t008_meeting_snap import app as app_module
from t008_meeting_snap import metrics as metrics_module

app_module.app.config.update(TESTING=True)


def _collect_metrics(client: Any) -> dict[str, float]:
    response = client.get("/metrics")
    assert response.status_code == 200
    payload: dict[str, float] = {}
    for line in response.get_data(as_text=True).splitlines():
        if not line.strip():
            continue
        name, value_text = line.split(" ", 1)
        payload[name] = float(value_text)
    return payload


def test_metrics_increment_after_snap(monkeypatch) -> None:
    """Fetching metrics around a snap should show counter increases."""

    reload(metrics_module)
    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "logic")

    with app_module.app.test_client() as client:
        post_response = client.post("/snap", data={"transcript": "Brief hello."})
        assert post_response.status_code == 200
        payload = _collect_metrics(client)

    assert payload["requests_total"] == 2
    assert payload['snaps_total{path="logic"}'] == 1
