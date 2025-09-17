# Meeting Snap Development Guide

## Repository map
- `t008_meeting_snap/app.py` – Flask entry point, route handlers, and rate limiting.
- `t008_meeting_snap/config.py` – Environment variable helpers.
- `t008_meeting_snap/extractor.py` – Dispatches between `logic`, `fake`, and `openai` providers with automatic fallback.
- `t008_meeting_snap/logic.py` – Deterministic transcript parser used for the baseline provider and fallbacks.
- `t008_meeting_snap/llm.py` / `llm_fake.py` / `llm_openai.py` – Prompt helpers and provider adapters.
- `t008_meeting_snap/schema.py` – Snapshot normalisation and validation helpers.
- `t008_meeting_snap/export.py` – Markdown exporter for cached snapshots.
- `t008_meeting_snap/metrics.py` – In-memory counters and Prometheus exposition.
- `t008_meeting_snap/templates/` – HTML templates rendered by the Flask app.
- `tests/` – Pytest suite covering the app, schema, metrics, and provider flows.
- `tests/_stubs/` – Test-only stand-ins for `flask` and `pydantic`. Runtime code must import the real packages.

## JSON contract
Snapshots emitted by providers and rendered in the UI must contain:

| Field | Type | Notes |
| --- | --- | --- |
| `decisions` | list[str] | Up to 10 non-empty strings (≤120 characters each). |
| `actions` | list[dict] | Each item requires `action`; optional `owner`/`due` strings or `None`. |
| `questions` | list[str] | Non-empty follow-up questions. |
| `risks` | list[str] | Non-empty risk descriptions. |
| `next_checkin` | str or None | Human-readable schedule for the next check-in. |

Use `schema.validate_snapshot()` to coerce provider output into a valid payload. Empty states should come from `schema.UI_EMPTY` or `schema.empty_snapshot()` so the UI and download export stay in sync.

## Local workflow
1. Follow the README “Run / Test / Env” section to create a virtual environment and install dependencies.
2. Launch the app with `MEETING_SNAP_PROVIDER=logic python -m t008_meeting_snap.app` and open `http://127.0.0.1:5000/`.
3. Run `python -m pytest` before sending changes—tests cover the contract, rate limiter, exporter, and HTML output.

## Test doubles
- The stub modules in `tests/_stubs/` keep the test environment isolated from real Flask and pydantic. Add to these stubs when new imports appear in tests.
- `t008_meeting_snap/app.py` guards against accidentally running with the stubs; keep that check intact when editing imports.

## Coding rules
- **Standard library first.** Runtime modules must stay within the Python standard library unless you are extending an optional provider integration (e.g. the `openai` dependency already declared in `requirements.txt`). Discuss any new runtime package additions before landing them.
- Keep modules focused—split large changes if a file would balloon past ~160 lines for readability.
- Maintain existing public names because the template and tests import them directly.
- Add or update unit tests when behaviour changes, especially around extraction, schema validation, or rate limiting.
