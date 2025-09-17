# Meeting Snap Development Guide

## Repository layout
- `t008_meeting_snap/app.py` — Flask entry point that wires HTTP routes, enforces rate limiting, and renders templates.
- `t008_meeting_snap/extractor.py` — Chooses between deterministic logic and provider-backed extraction, handling fallbacks.
- `t008_meeting_snap/logic.py` — Pure-Python heuristics that parse transcripts into snapshot structures without an LLM.
- `t008_meeting_snap/llm*.py` — Prompt/response helpers (`llm.py`) plus provider adapters such as `llm_fake.py` and `llm_openai.py`.
- `t008_meeting_snap/schema.py` — Snapshot validation, normalization, and empty-state helpers shared by the app and providers.
- `t008_meeting_snap/export.py` — Markdown exporter for cached snapshots.
- `t008_meeting_snap/metrics.py` — In-memory Prometheus counters surfaced at `/metrics`.
- `t008_meeting_snap/templates/` — HTML template rendered for both empty and populated snapshots.
- `tests/` — Pytest suite covering extraction logic, metrics, rate limiting, and template rendering.

## JSON contract
Snapshots must include:
- `decisions`: list of up to 10 non-empty strings (≤120 chars each).
- `actions`: list of dicts with `action` (required string) and optional `owner`/`due` strings or nulls.
- `questions`: list of non-empty strings.
- `risks`: list of non-empty strings describing blockers.
- `next_checkin`: string description or null when unknown.

Use `schema.validate_snapshot()` to normalize data before rendering or exporting. Empty views should use `schema.UI_EMPTY`/`schema.empty_snapshot()` for consistency.

## Run and test locally
1. Create and activate a virtual environment.
2. Install development dependencies (pytest for tests, plus `openai` if you plan to exercise the live provider):
   ```bash
   python -m pip install --upgrade pip
   python -m pip install pytest openai
   ```
3. Run the web UI with the built-in Flask stub:
   ```bash
   python -m t008_meeting_snap.app
   ```
4. Execute the test suite:
   ```bash
   python -m pytest
   ```

## Contribution constraints
- Stick to the Python standard library unless you are integrating an optional provider dependency (e.g., `openai`). Keep new runtime requirements documented.
- Keep individual modules and additions focused—split work if a file would grow beyond ~160 lines to preserve readability.
- Preserve existing public names (functions, classes, module-level constants) because tests and the Flask template rely on them.
- Add or update unit tests for any behavior change, especially around extraction, schema validation, and rate limiting.

## Adding a new provider
1. Create `t008_meeting_snap/llm_<provider>.py` that exposes an `extract(text: str, timeout_ms: int, ...) -> dict` function returning the snapshot JSON.
2. Update `_extract_with_provider` in `t008_meeting_snap/extractor.py` to route the provider ID to your new module. Keep the logic fallback in the surrounding `extract_snapshot()` untouched.
3. Extend `t008_meeting_snap/config.py` if you need additional configuration (e.g., API keys or model names) and document the env vars in `docs/OPERATIONS.md`.
4. Write provider-specific tests under `tests/` using fakes or fixtures so the suite remains deterministic.
5. Run `python -m pytest` and ensure `/metrics` reporting still reflects the new provider path via `snaps_total{path="<provider>"}`.
