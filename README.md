# meeting-snap

## Agent Quickstart
- [Operations guide](docs/OPERATIONS.md)
- [Development guide](docs/DEVELOPMENT.md)

## Run / Test / Env

### Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# Add development-only tools such as pytest
python -m pip install -r requirements-dev.txt
```

### Environment
| Variable | Default | Notes |
| --- | --- | --- |
| `MEETING_SNAP_PROVIDER` | `logic` | Extraction backend: `logic` (deterministic), `fake` (static sample), or `openai` (live API). |
| `MEETING_SNAP_TIMEOUT_MS` | `10000` | Request timeout for provider calls. |
| `MEETING_SNAP_MAX_CHARS` | `8000` | Maximum characters accepted from the transcript form. |
| `MEETING_SNAP_RATE_LIMIT` | `30` | Requests allowed per identity during the window. |
| `MEETING_SNAP_RATE_WINDOW_S` | `86400` | Sliding window size, in seconds, for rate limiting. |
| `OPENAI_API_KEY` | _required for OpenAI_ | Needed only when `MEETING_SNAP_PROVIDER=openai`; consumed by the `openai` SDK. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Overrides the OpenAI model used when the provider is `openai`. |

### Run
```bash
# Serve the UI locally at http://127.0.0.1:5000/
MEETING_SNAP_PROVIDER=logic python -m t008_meeting_snap.app

# Production-style entry point (matches Procfile)
gunicorn t008_meeting_snap.app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
```

### Test
```bash
python -m pytest
```
