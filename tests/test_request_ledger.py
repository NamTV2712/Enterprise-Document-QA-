import json

import pytest

from src.evaluation.request_ledger import (
    CampaignIncomplete,
    ProviderOperationError,
    RequestLedger,
    append_record,
)


def test_completed_operation_resumes_without_request(tmp_path):
    path = tmp_path / "ledger.jsonl"
    calls = []
    ledger = RequestLedger(path, "campaign", 2)
    assert ledger.call("op", "run", "hash", lambda: calls.append(1) or {"content": "ok"}) == {"content": "ok"}
    resumed = RequestLedger(path, "campaign", 2)
    assert resumed.call("op", "run", "hash", lambda: pytest.fail("sent again")) == {"content": "ok"}
    assert resumed.used == 1 and calls == [1]
    with pytest.raises(CampaignIncomplete, match="inputs changed"):
        resumed.call("op", "run", "changed", lambda: {})


def test_retry_consumes_real_slot_and_budget_survives_resume(tmp_path):
    ledger = RequestLedger(tmp_path / "ledger.jsonl", "campaign", 2)
    calls = []

    def send():
        calls.append(1)
        if len(calls) == 1:
            raise TimeoutError()
        return {"content": "ok"}

    ledger.call("op", "run", "hash", send)
    assert ledger.used == 2
    with pytest.raises(CampaignIncomplete, match="budget exhausted"):
        RequestLedger(ledger.path, "campaign", 2).call("next", "run", "hash", lambda: pytest.fail("over budget"))


def test_unknown_reserved_result_never_reissued(tmp_path):
    ledger = RequestLedger(tmp_path / "ledger.jsonl", "campaign", 2)
    append_record(ledger.path, {"event": "reserved", "campaign_id": "campaign", "limit": 2,
                              "slot": 1, "operation": "op", "run_id": "run", "request_sha256": "hash", "attempt": 1})
    with pytest.raises(CampaignIncomplete, match="outcome is unknown"):
        ledger.call("op", "run", "hash", lambda: pytest.fail("uncertain retry"))
    assert ledger.used == 1


def test_nonretryable_error_and_lock_release(tmp_path):
    ledger = RequestLedger(tmp_path / "ledger.jsonl", "campaign")
    with pytest.raises(CampaignIncomplete, match="provider operation failed"):
        ledger.call("op", "run", "hash", lambda: (_ for _ in ()).throw(ValueError("secret must not be logged")))
    assert "secret" not in ledger.path.read_text()
    with pytest.raises(CampaignIncomplete, match="exhausted its retry"):
        ledger.call("op", "run", "hash", lambda: pytest.fail("invalid retry"))
    assert not ledger.path.with_suffix(".jsonl.lock").exists()


def test_request_sixty_one_is_forbidden(tmp_path):
    ledger = RequestLedger(tmp_path / "ledger.jsonl", "campaign")
    for index in range(60):
        ledger.call(str(index), "run", str(index), lambda: {"content": "ok"})
    with pytest.raises(CampaignIncomplete, match="budget exhausted"):
        ledger.call("61", "run", "hash", lambda: pytest.fail("request 61"))
    assert ledger.used == 60


def test_changed_budget_and_malformed_ledger_rejected(tmp_path):
    ledger = RequestLedger(tmp_path / "ledger.jsonl", "campaign", 2)
    ledger.call("op", "run", "hash", lambda: {})
    with pytest.raises(CampaignIncomplete):
        RequestLedger(ledger.path, "campaign", 60)
    with ledger.path.open("a") as file:
        file.write(json.dumps({"campaign_id": "other"}) + "\n")
    with pytest.raises(CampaignIncomplete):
        RequestLedger(ledger.path, "campaign", 2)


def test_provider_metadata_is_redacted_and_persisted_per_attempt(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = RequestLedger(path, "campaign", 3)
    attempts = []

    def send():
        attempts.append(1)
        if len(attempts) == 1:
            raise ProviderOperationError(
                "RateLimitError",
                429,
                {
                    "key_alias": "key-2",
                    "pool_size": 3,
                    "transport_attempt": 1,
                    "status": "error",
                    "retry_after": "2",
                    "secret": "must-not-be-written",
                },
            )
        return {"content": "ok", "provider": {"key_alias": "key-3"}}

    ledger.call("op", "run", "hash", send)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    error = next(row for row in rows if row["event"] == "error")
    assert error["error_type"] == "RateLimitError"
    assert error["status_code"] == 429
    assert error["provider"] == {
        "key_alias": "key-2",
        "pool_size": 3,
        "transport_attempt": 1,
        "status": "error",
        "retry_after": "2",
        "provider_error_type": "RateLimitError",
    }
    assert "must-not-be-written" not in path.read_text()
