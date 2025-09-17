"""Minimal in-memory counters and Prometheus exposition helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Mapping, Tuple

requests_total: float = 0.0
rate_limit_hits_total: float = 0.0
truncations_total: float = 0.0
llm_calls_total: float = 0.0
llm_latency_ms_sum: float = 0.0
llm_tokens_total: float = 0.0

snaps_total: Dict[str, float] = {name: 0.0 for name in ("logic", "fake", "openai", "fallback")}

_other_counters: Dict[str, float] = defaultdict(float)
_labelled_counters: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = defaultdict(
    lambda: defaultdict(float)
)


def inc(name: str, labels: Mapping[str, str] | None = None, value: float = 1.0) -> None:
    """Increment the named counter in-memory."""

    global requests_total, rate_limit_hits_total, truncations_total
    global llm_calls_total, llm_latency_ms_sum, llm_tokens_total

    if labels:
        if name == "snaps_total":
            path = labels.get("path", "fallback")
            snaps_total[path] = snaps_total.get(path, 0.0) + value
            return
        label_key = tuple(sorted((str(k), str(v)) for k, v in labels.items()))
        _labelled_counters[name][label_key] += value
        return

    if name == "requests_total":
        requests_total += value
    elif name == "rate_limit_hits_total":
        rate_limit_hits_total += value
    elif name == "truncations_total":
        truncations_total += value
    elif name == "llm_calls_total":
        llm_calls_total += value
    elif name == "llm_latency_ms_sum":
        llm_latency_ms_sum += value
    elif name == "llm_tokens_total":
        llm_tokens_total += value
    else:
        _other_counters[name] += value


def to_prometheus() -> str:
    """Return a Prometheus text exposition payload for the recorded metrics."""

    lines = []

    def add_metric(name: str, metric_value: float, labels: Mapping[str, str] | None = None) -> None:
        formatted_value = _format_value(metric_value)
        if labels:
            label_parts = ",".join(
                f"{key}=\"{_escape_label_value(value)}\"" for key, value in sorted(labels.items())
            )
            lines.append(f"{name}{{{label_parts}}} {formatted_value}")
        else:
            lines.append(f"{name} {formatted_value}")

    add_metric("requests_total", requests_total)
    add_metric("rate_limit_hits_total", rate_limit_hits_total)
    add_metric("truncations_total", truncations_total)
    add_metric("llm_calls_total", llm_calls_total)
    add_metric("llm_latency_ms_sum", llm_latency_ms_sum)
    add_metric("llm_tokens_total", llm_tokens_total)

    for path, count in sorted(snaps_total.items()):
        add_metric("snaps_total", count, {"path": path})

    for name, value in sorted(_other_counters.items()):
        add_metric(name, value)

    for name, entries in sorted(_labelled_counters.items()):
        for label_key, value in sorted(entries.items()):
            labels = {key: str(val) for key, val in label_key}
            add_metric(name, value, labels)

    return "\n".join(lines) + "\n"


def _format_value(value: float) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _escape_label_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("\n", "\\n")
    return escaped.replace('"', '\\"')
