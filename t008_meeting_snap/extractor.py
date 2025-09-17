"""Snapshot extraction orchestrator for Meeting Snap."""
from __future__ import annotations

from typing import Dict

from . import llm_fake, logic, schema


def extract_snapshot(text: str, provider: str, timeout_ms: int) -> Dict[str, object]:
    """Return a schema-valid snapshot using the configured provider."""

    provider_id = (provider or "").strip().lower()
    try:
        if provider_id == "fake":
            candidate = llm_fake.extract(text)
        elif provider_id == "logic":
            candidate = logic.assemble(text)
        else:
            candidate = _extract_with_provider(text, provider_id, timeout_ms)
        return schema.validate_snapshot(candidate)
    except Exception:
        fallback = logic.assemble(text)
        return schema.validate_snapshot(fallback)


def _extract_with_provider(text: str, provider_id: str, timeout_ms: int) -> Dict[str, object]:
    """Placeholder for future model provider integrations."""

    raise RuntimeError(f"Provider '{provider_id}' not implemented (timeout {timeout_ms} ms)")
