import json
from pathlib import Path

from scripts.diagnostics.answer_scope_offline import run as run_offline
from scripts.run_answer_scope_sentinel import SENTINEL_QUESTIONS

from tests.conftest import skip_without_data


def test_answer_scope_sentinel_has_ten_cases_and_known_controls() -> None:
    assert len(SENTINEL_QUESTIONS) == 10
    assert SENTINEL_QUESTIONS[0] == "What quality and manufacturing risks does Apple mention?"
    assert SENTINEL_QUESTIONS[1] == "What are all the major risk factors Microsoft discloses?"
    assert SENTINEL_QUESTIONS[-1] == "What was Amazon's consolidated net sales in 2024?"


@skip_without_data(
    "data/eval_artifacts/phase1_priority2.json",
)
def test_answer_scope_offline_gate_is_provider_free(tmp_path: Path) -> None:
    output = tmp_path / "answer_scope_offline.json"
    report = run_offline(output=output)

    assert report["passed"] is True
    assert report["gates"]["source_boundaries_valid"] is True
    assert report["microsoft_risk_role_counts"]["canonical"] > 0
    assert report["microsoft_risk_role_counts"]["supporting"] > 0
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True
