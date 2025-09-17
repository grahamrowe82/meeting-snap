"""Regression tests for extractor behaviour across provider paths."""

from __future__ import annotations

import logging

from t008_meeting_snap import extractor, llm_openai, schema


def test_extractor_success_sets_used_true(monkeypatch, caplog):
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

    with caplog.at_level(logging.INFO):
        snapshot, used = extractor.extract_snapshot("t", "openai", 3000)

    assert used is True
    assert schema.validate_snapshot(snapshot)["decisions"] == ["A"]


def test_extractor_failure_logs_and_falls_back(monkeypatch, caplog):
    def boom(*_):
        raise RuntimeError("fake provider error")

    monkeypatch.setattr(llm_openai, "extract", boom)

    with caplog.at_level(logging.ERROR):
        snapshot, used = extractor.extract_snapshot("t", "openai", 3000)

    assert used is False
    assert any(
        "Provider 'openai' failed" in record.getMessage() for record in caplog.records
    )
    validated = schema.validate_snapshot(snapshot)
    assert set(validated.keys()) == {
        "decisions",
        "actions",
        "questions",
        "risks",
        "next_checkin",
    }
