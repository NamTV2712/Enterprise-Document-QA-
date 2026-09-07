from __future__ import annotations

import pytest

from src.evaluation.provider_budget import ProviderBudgetLedger
from src.evaluation.request_ledger import CampaignIncomplete


def test_provider_round_counts_success_and_error_attempts(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "round.jsonl", "improvement", limit=2)
    assert ledger.call(
        campaign_id="c1",
        operation="generation:1",
        request_sha256="a",
        send=lambda: {"ok": True},
    ) == {"ok": True}
    with pytest.raises(RuntimeError):
        ledger.call(
            campaign_id="c1",
            operation="judge:1",
            request_sha256="b",
            send=lambda: (_ for _ in ()).throw(RuntimeError("provider")),
        )
    assert ledger.used == 2
    with pytest.raises(CampaignIncomplete, match="budget exhausted"):
        ledger.call(
            campaign_id="c2",
            operation="generation:2",
            request_sha256="c",
            send=lambda: pytest.fail("over budget"),
        )


def test_provider_round_unknown_reservation_is_not_reissued(tmp_path):
    ledger = ProviderBudgetLedger(tmp_path / "round.jsonl", "improvement", limit=2)
    slot = ledger.reserve(
        campaign_id="c1", operation="generation:1", request_sha256="a"
    )
    assert slot == 1
    with pytest.raises(CampaignIncomplete, match="unknown"):
        ledger.call(
            campaign_id="c1",
            operation="generation:1",
            request_sha256="a",
            send=lambda: pytest.fail("must not reissue"),
        )
