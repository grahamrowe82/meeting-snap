"""OpenAI provider integration for Meeting Snap."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from . import llm


def extract(text: str, timeout_ms: int, model: str) -> Dict[str, object]:
    """Call the OpenAI API and return the extracted snapshot payload."""

    prompt = llm.build_prompt(text)
    timeout_s = _coerce_timeout(timeout_ms)
    client = _create_client(timeout_s)

    response_text = _call_openai(client, model=model, prompt=prompt, timeout_s=timeout_s)
    return llm.parse_json_block(response_text)


def _coerce_timeout(timeout_ms: int | None) -> float | None:
    if not timeout_ms or timeout_ms <= 0:
        return None
    return timeout_ms / 1000.0


def _create_client(timeout_s: float | None):
    from openai import OpenAI  # Lazy import to avoid dependency when unused

    client = OpenAI()
    if timeout_s is not None:
        with_options = getattr(client, "with_options", None)
        if callable(with_options):
            client = with_options(timeout=timeout_s)
    return client


def _call_openai(client, *, model: str, prompt: str, timeout_s: float | None) -> str:
    try:
        return _call_responses_api(client, model=model, prompt=prompt, timeout_s=timeout_s)
    except AttributeError:
        return _call_chat_completions_api(client, model=model, prompt=prompt, timeout_s=timeout_s)


def _call_responses_api(client, *, model: str, prompt: str, timeout_s: float | None) -> str:
    responses = getattr(client, "responses")
    kwargs = {
        "model": model,
        "input": prompt,
        "response_format": {"type": "json_object"},
    }
    if timeout_s is not None:
        kwargs["timeout"] = timeout_s
    response = responses.create(**kwargs)

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = getattr(response, "output", None)
    if output:
        text_parts: List[str] = []
        for item in _ensure_iterable(output):
            content = getattr(item, "content", None) or (item.get("content") if isinstance(item, dict) else None)
            if not content:
                continue
            text = _normalise_message_content(content)
            if text:
                text_parts.append(text)
        if text_parts:
            return "".join(text_parts)

    raise ValueError("OpenAI Responses API did not return text output")


def _call_chat_completions_api(client, *, model: str, prompt: str, timeout_s: float | None) -> str:
    chat = getattr(client, "chat")
    completions = getattr(chat, "completions")

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if timeout_s is not None:
        kwargs["timeout"] = timeout_s
    kwargs["response_format"] = {"type": "json_object"}

    try:
        completion = completions.create(**kwargs)
    except TypeError:
        kwargs.pop("response_format", None)
        completion = completions.create(**kwargs)

    choices = getattr(completion, "choices", None)
    if not choices:
        choices = completion.get("choices") if isinstance(completion, dict) else None
    if not choices:
        raise ValueError("OpenAI Chat Completions API returned no choices")

    first = choices[0]
    message = getattr(first, "message", None)
    if message is None and isinstance(first, dict):
        message = first.get("message")
    if message is None:
        raise ValueError("OpenAI Chat Completions choice missing message content")

    content = _extract_message_content(message)
    if not content:
        raise ValueError("OpenAI Chat Completions message contained no text")
    return content


def _extract_message_content(message: Any) -> str:
    if isinstance(message, dict):
        content = message.get("content")
        if content is None and "text" in message:
            content = message.get("text")
    else:
        content = getattr(message, "content", None)
        if content is None:
            content = getattr(message, "text", None)
    text = _normalise_message_content(content)
    if not text:
        return ""
    return text


def _normalise_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: List[str] = []
        for part in content:
            if isinstance(part, str):
                pieces.append(part)
                continue
            if isinstance(part, dict):
                text = part.get("text") or part.get("value")
                if text:
                    pieces.append(text)
                continue
            text = getattr(part, "text", None)
            if isinstance(text, str):
                pieces.append(text)
        return "".join(pieces)
    text = getattr(content, "text", None)
    if isinstance(text, str):
        return text
    return ""


def _ensure_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return value
    return [value]
