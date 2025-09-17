"""Tests for the markdown export helper."""
from __future__ import annotations

from t008_meeting_snap import export


def test_to_markdown_formats_sections() -> None:
    """Markdown export includes every section with fallbacks."""

    snapshot = {
        "decisions": ["Ship release\nthis week"],
        "actions": [
            {"action": "Draft FAQ", "owner": "Taylor", "due": "Friday"},
            {"action": "Notify customers", "owner": None, "due": None},
        ],
        "questions": ["What about billing?"],
        "risks": [],
        "next_checkin": "Next Thursday",
    }

    result = export.to_markdown(snapshot)
    markdown = result.decode("utf-8")

    expected = """# Meeting Snap\n"""
    expected += """## Decisions\n"""
    expected += """- Ship release this week\n"""
    expected += """## Actions (owner — due)\n"""
    expected += """- Draft FAQ (Taylor — Friday)\n"""
    expected += """- Notify customers (— — —)\n"""
    expected += """## Questions\n"""
    expected += """- What about billing?\n"""
    expected += """## Risks\n"""
    expected += """- —\n"""
    expected += """## Next check-in\n"""
    expected += """- Next Thursday\n"""

    assert markdown == expected
