"""CRED-001 credential authority and historical binding compatibility, offline."""

import asyncio
import importlib
import json
import sys
from types import SimpleNamespace

import pytest

from configs.settings import Settings
from src.agent import provider
from src.agent.durable_models import AgentRunCreateRequest
from src.agent.evaluation import evaluate_durable_agent_run
from src.agent.provider_models import DecisionProviderIdentity
from src.generation.generator import Generator
from src.generation.provider_policy import configured_groq_keys, validate_explicit_keys
from tests.test_agent_provider import FakeSDK, durable, final, run, settings, wire
from tests.test_generator_key_rotation import _install_fake_groq


PRIMARY = "CRED_TEST_PRIMARY_synthetic_only"
FALLBACK = "CRED_TEST_FALLBACK_synthetic_only"
REMOVED = ("GROQ_API_KEY2", "GROQ_API_KEY3", "GROQ_API_KEY4",
           "GROQ_API_KEY5", "GROQ_API_KEY_FALL_BACK2")
HISTORICAL_BINDING = "groq_structured_d1fae7f776ea43c73856273d6c5024e9"


@pytest.mark.parametrize("primary,fallback,expected", [
    (PRIMARY, "", [PRIMARY]), (PRIMARY, FALLBACK, [PRIMARY, FALLBACK]),
    (PRIMARY, PRIMARY, [PRIMARY]), ("", FALLBACK, [FALLBACK]), ("", "", []),
])
def test_shared_selection_and_strict_primary(primary, fallback, expected):
    configured = settings(primary=primary, fallback=fallback, policy="pool")
    assert configured_groq_keys(configured) == expected
    if primary:
        assert configured_groq_keys(configured, policy="key5_only") == [primary]
        resolved = provider.resolve_decision_provider(settings(primary=primary, fallback=fallback))
        assert resolved.secrets[0] == primary
        assert resolved.identity.binding_id == HISTORICAL_BINDING
    else:
        with pytest.raises(ValueError, match="requires GROQ_API_KEY"):
            configured_groq_keys(configured, policy="key5_only")
        assert provider.resolve_decision_provider(settings(primary="", fallback=fallback)).identity is None


@pytest.mark.parametrize("legacy_name", REMOVED)
def test_removed_environment_slots_cannot_supply_credentials(monkeypatch, legacy_name):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_FALL_BACK", raising=False)
    monkeypatch.setenv("GROQ_KEY_POLICY", "pool")
    for name in REMOVED:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(legacy_name, "LEGACY_TEST_CREDENTIAL_synthetic_only")
    configured = Settings(_env_file=None)
    assert configured_groq_keys(configured) == []
    assert legacy_name.lower() not in Settings.model_fields
    assert provider.resolve_decision_provider(configured).identity is None


def test_current_environment_names_are_accepted(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", PRIMARY)
    monkeypatch.setenv("GROQ_API_KEY_FALL_BACK", FALLBACK)
    monkeypatch.setenv("GROQ_KEY_POLICY", "pool")
    assert configured_groq_keys(Settings(_env_file=None)) == [PRIMARY, FALLBACK]
    assert {name for name in Settings.model_fields if name.startswith("groq_api_key")} == {
        "groq_api_key", "groq_api_key_fall_back"}


@pytest.mark.parametrize("primary,fallback,policy,keys,aliases", [
    (PRIMARY, "", "pool", [PRIMARY], ["primary"]),
    (PRIMARY, FALLBACK, "pool", [PRIMARY, FALLBACK], ["primary", "fallback"]),
    (PRIMARY, PRIMARY, "pool", [PRIMARY], ["primary"]),
    ("", FALLBACK, "pool", [FALLBACK], ["fallback"]),
    (PRIMARY, FALLBACK, "key5_only", [PRIMARY], ["primary"]),
])
def test_generator_client_count_order_and_safe_aliases(monkeypatch, primary, fallback, policy, keys, aliases):
    import configs.settings as configuration
    monkeypatch.setattr(configuration, "settings", settings(primary=primary, fallback=fallback, policy=policy))
    constructions = []
    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(
        Groq=lambda **options: constructions.append(options) or object()))
    generator = Generator(client_max_retries=0)
    assert [options["api_key"] for options in constructions] == keys
    assert all(options["max_retries"] == 0 for options in constructions)
    assert len(generator.clients) == len(keys)
    assert generator.client_aliases == aliases
    assert all(secret not in json.dumps(generator.last_transport_metadata) for secret in keys)


def test_strict_explicit_fallback_cannot_bypass_missing_primary():
    with pytest.raises(ValueError, match="requires GROQ_API_KEY"):
        validate_explicit_keys([FALLBACK], settings=settings(primary="", fallback=FALLBACK), policy="key5_only")
    with pytest.raises(ValueError, match="permits only GROQ_API_KEY"):
        validate_explicit_keys([FALLBACK], settings=settings(primary=PRIMARY, fallback=FALLBACK), policy="key5_only")
    with pytest.raises(ValueError, match="at most"):
        validate_explicit_keys([PRIMARY, FALLBACK, "THIRD_synthetic_only"], settings=settings(), policy="pool")


@pytest.mark.parametrize("rate_limit", [True, False])
def test_configured_generator_retries_only_rate_limits(monkeypatch, rate_limit):
    import configs.settings as configuration
    monkeypatch.setattr(configuration, "settings", settings(primary=PRIMARY, fallback=FALLBACK, policy="pool"))
    calls = []
    _install_fake_groq(monkeypatch, {PRIMARY: [RuntimeError("429 rate limit" if rate_limit else "ordinary failure")],
                                   FALLBACK: ["success"]}, calls)
    generator = Generator()
    if rate_limit:
        assert generator._create_groq_chat_completion() == "success"
        assert calls == [PRIMARY, FALLBACK]
        assert generator.last_transport_metadata["key_alias"] == "fallback"
    else:
        with pytest.raises(RuntimeError, match="ordinary failure"):
            generator._create_groq_chat_completion()
        assert calls == [PRIMARY]


def test_resolved_agent_primary_failure_is_one_attempt_without_fallback(monkeypatch):
    from tests import test_agent_provider as fixtures
    resolved = provider.resolve_decision_provider(settings(primary=PRIMARY, fallback=FALLBACK))
    sdk = FakeSDK(RuntimeError("429 rate limit"))
    monkeypatch.setattr(provider, "AsyncGroq", sdk)
    selected = provider.model_for_binding(resolved.model_id, lambda: resolved)
    monkeypatch.setattr(fixtures, "model", lambda _sdk: selected)
    result, calls = run(sdk, require_observation=False)
    assert result.failure.code == "decision_provider_failed"
    assert len(sdk.requests) == len(sdk.options) == 1 and not calls
    assert sdk.options[0]["api_key"] == PRIMARY
    assert sdk.options[0]["max_retries"] == 0
    assert sdk.options[0]["timeout"].read == provider.TIMEOUT_SECONDS == 60
    assert FALLBACK not in json.dumps(sdk.options, default=str)


def test_historical_terminal_identity_and_evaluation_survive_reopen(tmp_path):
    # The policy literal and binding were frozen before CRED-001; no row rewrite.
    identity = DecisionProviderIdentity.model_validate_json(
        '{"provider":"groq","model_id":"openai/gpt-oss-120b",'
        '"adapter_version":"groq_json_schema_v1","mechanism":"native_strict_json_schema",'
        '"credential_policy":"key5_only"}')
    assert identity.binding_id == HISTORICAL_BINDING
    sdk = FakeSDK(wire(final()))
    service, repo, _ = durable(tmp_path, sdk)
    created = service.create(AgentRunCreateRequest(goal="Read historical bounded evidence.",
        allow_decision_provider_execution=True, require_observation_for_final=False), idempotency_key="legacy")
    terminal = asyncio.run(service.run(created.run_id))
    assert terminal.state == "succeeded"
    before = repo.get_job("job_" + created.run_id[6:]).payload
    reopened, reopened_repo, _ = durable(tmp_path, FakeSDK())
    assert reopened.get(created.run_id).frozen.decision_provider == identity
    report = evaluate_durable_agent_run(reopened, created.run_id)
    assert report is not None
    assert reopened_repo.get_job("job_" + created.run_id[6:]).payload == before
    assert len(sdk.requests) == 1


@pytest.mark.parametrize("policy", ["pool", "key5_only"])
def test_legacy_evaluation_builds_separate_clients_from_shared_authority(monkeypatch, policy):
    from scripts import run_evaluation as legacy
    monkeypatch.setattr(legacy, "settings", settings(primary=PRIMARY, fallback=FALLBACK, policy=policy))
    calls = []
    monkeypatch.setattr(legacy, "Generator", lambda **options: calls.append(options) or object())
    generation, judge = legacy.evaluation_generators()
    assert generation is not judge
    assert len(calls) == 2
    assert all(call["api_keys"] == ([PRIMARY, FALLBACK] if policy == "pool" else [PRIMARY]) for call in calls)
    assert all(call["key_policy"] == policy for call in calls)


def test_legacy_evaluation_cli_runs_with_mock_services(monkeypatch, tmp_path):
    from contextlib import nullcontext
    from scripts import run_evaluation as legacy
    import configs.settings as configuration
    monkeypatch.setattr(legacy, "settings", configuration.settings.model_copy(update={
        "groq_api_key": PRIMARY, "groq_api_key_fall_back": FALLBACK, "groq_key_policy": "pool"}))
    monkeypatch.setattr(legacy, "CHECKPOINT_PATH", tmp_path / "checkpoint.jsonl")
    monkeypatch.setattr(legacy, "TEST_SET", [])
    monkeypatch.setattr(sys, "argv", ["run_evaluation", "--limit", "0"])
    constructions = []
    monkeypatch.setattr(legacy, "Generator", lambda **options: constructions.append(options) or object())
    for name in ("Embedder", "RAGEvaluator", "HybridRetriever", "RAGPipeline", "QueryDecomposer"):
        monkeypatch.setattr(legacy, name, lambda **_options: object())
    monkeypatch.setattr(legacy, "VectorStore", lambda **_options: nullcontext(object()))
    monkeypatch.setattr(legacy, "load_retrieval_chunks", lambda *_args: [])
    summaries = []
    monkeypatch.setattr(legacy, "_print_summary", lambda *args: summaries.append(args))
    legacy.main()
    assert len(constructions) == 2 and len(summaries) == 1
    assert all(call["api_keys"] == [PRIMARY, FALLBACK] for call in constructions)


@pytest.mark.parametrize("module", ["src.workspace.jobs", "src.workspace.repository",
                                    "src.workspace.telemetry", "src.workspace.transfer"])
def test_private_storage_secret_guards_include_both_credentials(monkeypatch, module):
    import configs.settings as configuration
    monkeypatch.setattr(configuration.settings, "groq_api_key", PRIMARY)
    monkeypatch.setattr(configuration.settings, "groq_api_key_fall_back", FALLBACK)
    guard = importlib.import_module(module)._configured_secret_values
    protected = guard(configuration.settings) if module == "src.workspace.telemetry" else guard()
    assert PRIMARY in protected and FALLBACK in protected


@pytest.mark.parametrize("module", ["scripts.run_evaluation", "scripts.run_evaluation_phase1",
    "scripts.run_evaluation_phase2", "scripts.diagnostics.planner_wording_check",
    "scripts.run_bilingual_evaluation_campaign"])
def test_evaluation_modules_import_without_provider_execution(module):
    assert importlib.import_module(module) is not None
