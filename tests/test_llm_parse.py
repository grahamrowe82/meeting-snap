"""Focused tests for the JSON parsing helpers."""

import pytest

from t008_meeting_snap.llm import parse_json_block


def test_parse_json_block_embedded_object() -> None:
    """A plain JSON object embedded in prose is extracted."""

    snippet = "Here it is {\"result\": 42, \"status\": \"ok\"} end"

    payload = parse_json_block(snippet)

    assert payload == {"result": 42, "status": "ok"}


def test_parse_json_block_with_dirty_wrapping_text() -> None:
    """Leading and trailing narration does not confuse the parser."""

    text = (
        "Model output follows.\n"
        "```json\n"
        "{\n  \"success\": true,\n  \"items\": [1, 2, 3]\n}\n"
        "```\n"
        "Thanks!"
    )

    payload = parse_json_block(text)

    assert payload == {"success": True, "items": [1, 2, 3]}


def test_parse_json_block_raises_without_json() -> None:
    """If no JSON object is present a ``ValueError`` is raised."""

    with pytest.raises(ValueError):
        parse_json_block("No structured data here.")
