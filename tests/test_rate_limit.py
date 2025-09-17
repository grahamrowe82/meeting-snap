"""Rate limiting behavior for the Meeting Snap app."""
from __future__ import annotations

from t008_meeting_snap.app import app
from t008_meeting_snap.safety import RateLimiter

app.config.update(TESTING=True)


def test_snap_post_rate_limited(monkeypatch) -> None:
    """Rapid submissions from the same IP yield a 429 response."""

    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "fake")
    limiter = RateLimiter(max_requests=2, window_seconds=60.0)
    monkeypatch.setitem(app.config, "RATE_LIMITER", limiter)

    with app.test_client() as client:
        first = client.post("/snap", data={"transcript": "Quarterly sync"})
        second = client.post("/snap", data={"transcript": "Quarterly sync"})
        third = client.post("/snap", data={"transcript": "Quarterly sync"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
