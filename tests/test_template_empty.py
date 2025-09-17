"""Validate the UI placeholders for empty baseline snapshots."""

from t008_meeting_snap.app import app

app.config.update(TESTING=True)


def test_empty_sections_render_placeholders(monkeypatch) -> None:
    """Posting minimal text renders all sections with the empty marker."""

    monkeypatch.setenv("MEETING_SNAP_PROVIDER", "logic")

    with app.test_client() as client:
        response = client.post("/snap", data={"transcript": "Hello team."})

    assert response.status_code == 200
    body = response.get_data(as_text=True)

    headings = [
        "Decisions",
        "Actions",
        "Open Questions",
        "Risks / Blockers",
        "Next Check-in",
    ]

    for heading in headings:
        assert f"<h2>{heading}</h2>" in body

    assert body.count('class="empty">—') == 5
