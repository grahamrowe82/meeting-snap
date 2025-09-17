"""LLM integration helpers for Meeting Snap."""
from __future__ import annotations

import json
import re
import textwrap
from typing import Any, Dict

_PROMPT_TEMPLATE = textwrap.dedent(
    """
    You are Meeting Snap, an assistant that extracts meeting outcomes for busy
    teams. Read the transcript and respond with a JSON object that matches the
    following schema:
    {
      "decisions": ["short summary", ... up to 10 items],
      "actions": [
        {"action": "task", "owner": "Name or null", "due": "Due date or null"}
      ],
      "questions": ["open question"],
      "risks": ["issue or blocker"],
      "next_checkin": "describe the next meeting or null"
    }

    Rules:
    - Trim whitespace from every string you return and keep them concise.
    - If a field has no content, use an empty list or null for "next_checkin".
    - The JSON must be valid and parsable without additional commentary.

    Transcript:
    ---
    {transcript}
    ---
    """
)


_DEFENSIVE_DECODER = json.JSONDecoder()
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def build_prompt(transcript: str) -> str:
    """Return the LLM prompt for a given transcript snippet."""

    clean_transcript = transcript.strip() if transcript else ""
    if not clean_transcript:
        clean_transcript = "(No transcript content provided.)"
    return _PROMPT_TEMPLATE.format(transcript=clean_transcript)


def _decode_candidate(snippet: str) -> Dict[str, Any] | None:
    try:
        payload = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def parse_json_block(text: str) -> Dict[str, Any]:
    """Extract and parse the first JSON object embedded in ``text``."""

    direct = _decode_candidate(text.strip())
    if direct is not None:
        return direct

    for match in _CODE_FENCE_RE.finditer(text):
        candidate = _decode_candidate(match.group(1).strip())
        if candidate is not None:
            return candidate

    start = 0
    while True:
        brace = text.find("{", start)
        if brace == -1:
            break
        try:
            payload, offset = _DEFENSIVE_DECODER.raw_decode(text[brace:])
        except json.JSONDecodeError:
            start = brace + 1
            continue
        if isinstance(payload, dict):
            return payload
        start = brace + offset

    raise ValueError("No JSON object found in text")
