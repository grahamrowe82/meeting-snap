# Meeting Snap Operations

## What it does
- Provides a lightweight web UI for turning a meeting transcript into a structured "snapshot" that lists decisions, actions, questions, risks, and the next check-in.
- Serves summaries generated either by deterministic heuristics (`logic` provider) or an external LLM provider (`fake`, `openai`, or future integrations) with automatic fallback to the logic baseline if model assist fails.
- Caches the most recent snapshot per client IP so that users can immediately download the rendered Markdown export.
- Exposes Prometheus-formatted counters to track request volume, provider mix, rate limiting, and LLM usage.

## Endpoints
| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Render the transcript form and the current snapshot preview. |
| POST | `/snap` | Accept a transcript submission, enforce rate limits, call the configured provider, and render the updated snapshot. |
| GET | `/download.md` | Download the last snapshot for the caller as Markdown, returning 404 when nothing is cached. |
| GET | `/metrics` | Prometheus metrics for `requests_total`, `snaps_total{path=...}`, rate-limit hits, and LLM latency/token counters. |

## Environment variables
| Name | Default | Purpose |
| --- | --- | --- |
| `MEETING_SNAP_PROVIDER` | `logic` | Provider ID (`logic`, `fake`, `openai`, or another custom provider) used when `/snap` receives input. |
| `MEETING_SNAP_TIMEOUT_MS` | `10000` | Deadline in milliseconds passed to remote providers. Ignored by the `logic` baseline. |
| `MEETING_SNAP_MAX_CHARS` | `8000` | Maximum characters accepted from the transcript form. Submissions beyond the limit render an error. |
| `MEETING_SNAP_RATE_LIMIT` | `30` | Number of `/snap` requests allowed per identity during the configured window. Set to `0` to block all writes. |
| `MEETING_SNAP_RATE_WINDOW_S` | `86400` | Size of the sliding rate-limit window in seconds. |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name when `MEETING_SNAP_PROVIDER=openai`.

## Starting the service
- **Local development:** `python -m t008_meeting_snap.app` (uses the built-in Flask development server with debug logging enabled).
- **Hosted / production:** `gunicorn t008_meeting_snap.app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4` (matches the `Procfile` used by platforms that support process definitions).

## Runbook
### LLM provider degraded or unavailable
1. Confirm alerts by checking `/metrics` for a spike in `snaps_total{path="fallback"}` or drops in `llm_calls_total`/`llm_latency_ms_sum`.
2. Review application logs for `fallback` reasons or provider-specific errors.
3. The service already falls back to the `logic` baseline for each affected request. If the provider outage is prolonged, temporarily force logic-only mode (see below) to stop generating failing LLM traffic.
4. Once the provider is healthy, revert to the original configuration and monitor that `snaps_total{path="fallback"}` returns to baseline.

### Temporary rate-limit increase
1. Evaluate `/metrics` to confirm rate-limit saturation (`rate_limit_hits_total`).
2. Pick a new limit/window pair that preserves downstream capacity.
3. Update `MEETING_SNAP_RATE_LIMIT` and/or `MEETING_SNAP_RATE_WINDOW_S` in the deployment environment. Reloading the process is enough for changes to take effect—the limiter instance is rebuilt from the new config when `/snap` handles the next request.
4. Monitor `rate_limit_hits_total` to ensure the new ceiling unblocks legitimate traffic.
5. Remember to roll back the change when demand normalizes.

### Force logic-only mode
1. Set `MEETING_SNAP_PROVIDER=logic` in the runtime environment. This disables LLM calls and ensures every `/snap` request uses deterministic extraction.
2. Optionally drop any cached snapshots if you need to avoid stale mixed-provider content.
3. Notify stakeholders that the UI banner will show "Model assist: OFF" until the provider setting is restored.
4. When the upstream model is healthy again, revert the provider setting and spot-check `/snap` responses for model-assisted output.

## SLOs
- **Availability:** 99% of `/snap` requests per day should return HTTP 200. Track this by comparing total requests to 4xx/5xx counts in logs; unexpected spikes in `snaps_total{path="fallback"}` can hint at hidden errors.
- **Model-assist success:** Maintain at least 95% of snapshots served via LLM providers (`snaps_total{path="openai"}` or other providers) over fallback during a rolling 1-hour window.
- **Rate limiting:** Keep `rate_limit_hits_total / requests_total` under 1% per hour. Adjust limits or investigate abusive clients when the ratio grows.
- **Latency:** Average LLM latency (`llm_latency_ms_sum / llm_calls_total`) should stay below the configured timeout. Investigate if the value approaches the `MEETING_SNAP_TIMEOUT_MS` ceiling for prolonged periods.
