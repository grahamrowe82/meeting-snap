# Meeting Snap Operations

## Service overview
- Flask app that renders the meeting transcript form at `/` and processes submissions at `/snap`.
- Snapshot extraction runs through one provider at a time: `logic` (deterministic), `fake` (static sample), or `openai` (live API with logic fallback on failure).
- Prometheus-formatted counters are exposed at `/metrics` for request volume, provider mix, limiter activity, and model usage.

## Configuration quick reference
| Variable | Default | Purpose |
| --- | --- | --- |
| `MEETING_SNAP_PROVIDER` | `logic` | Controls which extractor runs when `/snap` receives input. |
| `MEETING_SNAP_TIMEOUT_MS` | `10000` | Deadline passed to external providers. Ignored by `logic`. |
| `MEETING_SNAP_MAX_CHARS` | `8000` | Maximum transcript length accepted from the form. |
| `MEETING_SNAP_RATE_LIMIT` | `30` | Requests allowed per identity during one window. |
| `MEETING_SNAP_RATE_WINDOW_S` | `86400` | Sliding window size, in seconds, for rate limiting. |
| `OPENAI_API_KEY` | _(none)_ | Required when the provider is `openai`; read directly by the `openai` SDK. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Overrides the OpenAI model used for extraction. |

## Runbook

### Rotate the OpenAI API key
1. Generate an OpenAI API key and store it in the deployment secret manager.
2. Update the environment variable `OPENAI_API_KEY` for the running service (container env, process manager config, or `.env` file).
3. Restart or redeploy the process so the `openai` client picks up the new key.
4. Submit a short transcript while `MEETING_SNAP_PROVIDER=openai` or inspect `/metrics` to confirm `snaps_total{path="openai"}` increments without errors.

### Force the logic provider
1. Set `MEETING_SNAP_PROVIDER=logic` in the runtime environment.
2. Restart the process (the provider is read during request handling, so a reload ensures the new value is active for every worker).
3. Verify by loading `/` and confirming the banner shows "Model assist: OFF", or check `/metrics` for `snaps_total{path="logic"}` growth only.

### Bump the rate limit
1. Decide on the new `MEETING_SNAP_RATE_LIMIT` (requests) and, if needed, `MEETING_SNAP_RATE_WINDOW_S` (window length in seconds).
2. Update those environment variables wherever the service is configured.
3. Restart the process so a fresh `RateLimiter` is created with the new values.
4. Monitor `/metrics` and watch `rate_limit_hits_total` to ensure the new ceiling alleviates throttling.

### Check `/metrics`
1. Issue `curl http://<host>:<port>/metrics` (or visit the URL in a browser) to retrieve the Prometheus text payload.
2. Key counters:
   - `requests_total` – all HTTP requests handled.
   - `snaps_total{path="logic"|"fake"|"openai"|"fallback"}` – provider usage and fallback volume.
   - `rate_limit_hits_total` – rejected submissions due to throttling.
   - `llm_calls_total`, `llm_latency_ms_sum`, `llm_tokens_total` – external model usage when `openai` is active.
