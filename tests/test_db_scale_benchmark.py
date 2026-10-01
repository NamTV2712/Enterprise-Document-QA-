"""The DB comparison driver retains workload and finite OBS populations."""
import asyncio
import json

import pytest

from scripts.benchmarks import db_scale_001 as db_scale
from scripts.benchmarks.obs_001 import ObservedScenario
from scripts.benchmarks.scale_002_stats import validate_report


@pytest.mark.integration
def test_comparison_counts_initialization_without_omitting_actual_http_work(tmp_path):
    result = asyncio.run(db_scale.measured_trial(
        ObservedScenario("read", concurrency=2, operations=4, trials=1, warmup=1), tmp_path, 1))
    validate_report(result)
    counts = result["initialization"]
    assert counts["scope"] == "whole_trial_including_startup_warmup_reopen"
    assert counts["expensive_initializations"] == counts["initialize_calls"] == 2
    assert counts["ensure_calls"] > counts["expensive_initializations"]
    assert result["request_count"] == 4 and result["successes"] == 4
    assert all(x == 0 for x in result["correctness"]["counts"].values())
    assert result["attribution"]["trace_count"] == 4


def test_failed_driver_campaign_stays_incomplete_with_safe_failure_category(tmp_path, monkeypatch):
    async def failed(*args, **kwargs):
        raise TimeoutError("PRIVATE_PROVIDER_CONTENT_synthetic")
    monkeypatch.setattr(db_scale, "measured_trial", failed)
    destination = tmp_path / "report.json"
    with pytest.raises(TimeoutError):
        asyncio.run(db_scale.campaign(destination, smoke=True, stage="diagnostic"))
    report = json.loads(destination.read_text())
    assert report["status"] == "incomplete"
    assert report["scenarios"][0]["failure_category"] == "timeout"
    assert "PRIVATE_PROVIDER_CONTENT" not in destination.read_text()
