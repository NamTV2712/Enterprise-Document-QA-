from __future__ import annotations

import json

from scripts.diagnostics.period_value_parity import (
    AWS_QUESTION,
    EXPECTED_ARTIFACT_FINGERPRINT,
    build_report,
    run,
)
from src.evaluation.test_set import TEST_SET


def _artifact() -> dict:
    cases = []
    for test_case in TEST_SET:
        chunks = []
        if test_case.question == AWS_QUESTION:
            chunks = [
                {
                    "chunk_id": "AMZN_growth_0",
                    "citation": "AMZN 10-K, MD&A",
                    "text": (
                        "Year Ended December 31,\n\n2024\n2025\n"
                        "Net Sales:\nAWS\n107,556\n128,725\n"
                    ),
                }
            ]
        cases.append(
            {
                "question": test_case.question,
                "category": test_case.category,
                "queries": [{"query": {}, "chunks": chunks}],
            }
        )
    return {
        "fingerprints": {"artifact": EXPECTED_ARTIFACT_FINGERPRINT},
        "cases": cases,
    }


def test_period_value_parity_report_passes_frozen_30_case_contract() -> None:
    report = build_report(_artifact(), artifact_file_sha256="sha256:test")

    assert report["passed"] is True
    assert report["num_cases"] == 30
    assert report["num_applicable_cases"] == 1
    assert report["num_full_evidence_applicable_cases"] == 1
    assert report["applicable_questions"] == [AWS_QUESTION]
    assert report["full_evidence_applicable_questions"] == [AWS_QUESTION]
    assert report["aws_pairs"] == [
        {"period": "2024", "value": "107,556", "source_number": 1},
        {"period": "2025", "value": "128,725", "source_number": 1},
    ]
    assert report["full_evidence_aws_pairs"] == report["aws_pairs"]
    assert report["all_case_parity"] is True


def test_period_value_parity_run_is_deterministic_and_does_not_mutate_input(
    tmp_path,
) -> None:
    path = tmp_path / "phase1.json"
    path.write_text(
        json.dumps(_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )
    before = path.read_bytes()

    first = run(path)
    second = run(path)

    assert first == second
    assert path.read_bytes() == before
