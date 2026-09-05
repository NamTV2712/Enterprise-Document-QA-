import sys
from types import SimpleNamespace

import src.generation.generator as generator_module
from src.generation.generator import Generator


class _FakeCompletions:
    def __init__(self, api_key: str, outcomes: dict[str, list[object]], calls: list[str]):
        self.api_key = api_key
        self.outcomes = outcomes
        self.calls = calls

    def create(self, **kwargs):
        self.calls.append(self.api_key)
        outcome = self.outcomes[self.api_key].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeGroq:
    def __init__(self, api_key: str, outcomes: dict[str, list[object]], calls: list[str]):
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(api_key, outcomes, calls)
        )


def _install_fake_groq(monkeypatch, outcomes, calls):
    def factory(*, api_key: str):
        return _FakeGroq(api_key, outcomes, calls)

    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(Groq=factory))


def test_generator_rotates_primary_keys_round_robin(monkeypatch) -> None:
    calls = []
    outcomes = {"primary-1": ["first"], "primary-2": ["second"]}
    _install_fake_groq(monkeypatch, outcomes, calls)
    generator = Generator(api_keys=["primary-1", "primary-2"])

    assert generator._create_groq_chat_completion() == "first"
    assert generator._create_groq_chat_completion() == "second"
    assert calls == ["primary-1", "primary-2"]


def test_rate_limited_key_immediately_fails_over_without_sleep(monkeypatch) -> None:
    calls = []
    fallback_response = object()
    outcomes = {
        "fallback-1": [RuntimeError("429 rate limit; try again in 20s")],
        "fallback-2": [fallback_response],
    }
    _install_fake_groq(monkeypatch, outcomes, calls)
    sleeps = []
    monkeypatch.setattr(generator_module.time, "sleep", sleeps.append)
    generator = Generator(api_keys=["fallback-1", "fallback-2"])

    assert generator._create_groq_chat_completion() is fallback_response
    assert calls == ["fallback-1", "fallback-2"]
    assert sleeps == []


def test_duplicate_and_blank_keys_are_removed(monkeypatch) -> None:
    calls = []
    outcomes = {"only-key": ["ok"]}
    _install_fake_groq(monkeypatch, outcomes, calls)

    generator = Generator(api_keys=["", "only-key", "only-key"])

    assert len(generator.clients) == 1
    assert generator._create_groq_chat_completion() == "ok"


def test_campaign_can_disable_provider_client_retries(monkeypatch) -> None:
    configured: list[int] = []

    class RetryAwareGroq:
        def __init__(self, *, api_key: str, max_retries: int):
            configured.append(max_retries)

    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(Groq=RetryAwareGroq))

    Generator(api_keys=["campaign-key"], client_max_retries=0)

    assert configured == [0]
