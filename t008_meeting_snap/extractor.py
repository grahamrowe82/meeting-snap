"""Snapshot extraction orchestrator for Meeting Snap."""
from __future__ import annotations

import logging

from typing import Dict, Tuple

from . import config, llm_fake, llm_openai, logic, schema


def extract_snapshot(
    text: str, provider: str, timeout_ms: int
) -> Tuple[Dict[str, object], bool]:
    """Return a schema-valid snapshot and whether model assist was used."""

    provider_id = (provider or "").strip().lower()
    try:
        if provider_id == "fake":
            candidate = llm_fake.extract(text)
            snapshot = schema.validate_snapshot(candidate)
            return snapshot, True
        elif provider_id == "logic":
            candidate = logic.assemble(text)
            snapshot = schema.validate_snapshot(candidate)
            return snapshot, False
        else:
            candidate = _extract_with_provider(text, provider_id, timeout_ms)
            snapshot = schema.validate_snapshot(candidate)
            return snapshot, True
    except Exception:
        logging.exception("Provider '%s' failed; falling back to logic baseline", provider_id or "")
        fallback = logic.assemble(text)
        snapshot = schema.validate_snapshot(fallback)
        return snapshot, False


def _extract_with_provider(text: str, provider_id: str, timeout_ms: int) -> Dict[str, object]:
    """Placeholder for future model provider integrations."""

    if provider_id == "openai":
        return llm_openai.extract(text, timeout_ms, config.get_openai_model())
    raise RuntimeError(f"Provider '{provider_id}' not implemented (timeout {timeout_ms} ms)")
