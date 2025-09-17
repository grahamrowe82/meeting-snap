"""Unit tests covering the OpenAI adapter response shape handling."""

from __future__ import annotations

import json
import types

import pytest

from t008_meeting_snap import llm, llm_openai, schema

GOOD_JSON = json.dumps(
    {
        "decisions": ["Ship pilot"],
        "actions": [
            {"action": "Email ACME", "owner": "Graham", "due": "tomorrow"}
        ],
        "questions": ["What about GDPR?"],
        "risks": ["Scope creep"],
        "next_checkin": "Tue 4pm",
    }
)


@pytest.fixture(autouse=True)
def stub_prompt(monkeypatch):
    monkeypatch.setattr(llm, "build_prompt", lambda transcript: transcript)


def fake_client_responses_output_text():
    client = types.SimpleNamespace()

    class Responses:
        def create(self, **kwargs):  # noqa: D401 - simple stub
            return types.SimpleNamespace(output_text=GOOD_JSON)

    client.responses = Responses()
    return client


def fake_client_responses_output_list():
    client = types.SimpleNamespace()

    class Responses:
        def create(self, **kwargs):  # noqa: D401 - simple stub
            content = [{"text": GOOD_JSON}]
            item = types.SimpleNamespace(content=content)
            return types.SimpleNamespace(output=[item])

    client.responses = Responses()
    return client


def fake_client_chat_completions():
    client = types.SimpleNamespace()

    class ChatCompletions:
        def create(self, **kwargs):  # noqa: D401 - simple stub
            return {"choices": [{"message": {"content": GOOD_JSON}}]}

    class Chat:
        def __init__(self):
            self.completions = ChatCompletions()

    client.chat = Chat()
    return client


@pytest.mark.parametrize(
    "client_factory",
    [fake_client_responses_output_text, fake_client_responses_output_list],
)
def test_responses_api_shapes(monkeypatch, client_factory):
    monkeypatch.setattr(
        llm_openai, "_create_client", lambda timeout_s: client_factory()
    )
    data = llm_openai.extract("transcript", timeout_ms=3000, model="gpt-4o-mini")
    snap = schema.validate_snapshot(data)
    assert set(snap.keys()) == {
        "decisions",
        "actions",
        "questions",
        "risks",
        "next_checkin",
    }
    assert snap["decisions"] and snap["actions"]


def test_fallback_to_chat_when_responses_raises(monkeypatch):
    def bad_client(_timeout):
        client = fake_client_chat_completions()

        class BadResponses:
            def create(self, **kwargs):  # noqa: D401 - simple stub
                raise RuntimeError("responses unavailable")

        client.responses = BadResponses()
        return client

    monkeypatch.setattr(llm_openai, "_create_client", bad_client)
    data = llm_openai.extract("t", timeout_ms=3000, model="gpt-4o-mini")
    snap = schema.validate_snapshot(data)
    assert snap["decisions"]


def test_json_wrapped_text_parses(monkeypatch):
    client = fake_client_responses_output_text()

    class Responses:
        def create(self, **kwargs):  # noqa: D401 - simple stub
            return types.SimpleNamespace(output_text=f"Here you go:\n{GOOD_JSON}\nThanks!")

    client.responses = Responses()
    monkeypatch.setattr(llm_openai, "_create_client", lambda _: client)
    data = llm_openai.extract("t", timeout_ms=3000, model="gpt-4o-mini")
    assert schema.validate_snapshot(data)["decisions"]


def test_adapter_raises_when_both_apis_fail(monkeypatch):
    class BadClient:
        class Responses:
            def create(self, **kwargs):  # noqa: D401 - simple stub
                raise RuntimeError("no responses")

        class Chat:
            class Completions:
                def create(self, **kwargs):  # noqa: D401 - simple stub
                    raise RuntimeError("no chat")

            def __init__(self):
                self.completions = self.Completions()

        def __init__(self):
            self.responses = self.Responses()
            self.chat = self.Chat()

    monkeypatch.setattr(llm_openai, "_create_client", lambda _: BadClient())
    with pytest.raises(Exception):
        llm_openai.extract("t", timeout_ms=3000, model="gpt-4o-mini")
