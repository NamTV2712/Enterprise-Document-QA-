import json

from scripts.diagnostics.answer_integrity_audit import run
from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V2


QUESTION = "What was Apple's total net sales in fiscal year 2024?"


def _write_inputs(tmp_path):
    artifact = {
        "cases": [
            {
                "question": QUESTION,
                "category": "fact_lookup",
                "queries": [
                    {
                        "query": {"ticker": "AAPL"},
                        "chunks": [
                            {
                                "chunk_id": "AAPL_irrelevant_1",
                                "score": 4.0,
                                "citation": "irrelevant",
                                "text": "Apple discusses its business.",
                            },
                            {
                                "chunk_id": "AAPL_irrelevant_2",
                                "score": 3.0,
                                "citation": "irrelevant",
                                "text": "Apple discusses services.",
                            },
                            {
                                "chunk_id": "AAPL_target_3",
                                "score": 10.0,
                                "citation": "financial table",
                                "text": "Total net sales were 391,035 in 2024.",
                            },
                        ],
                    }
                ],
            }
        ]
    }
    results = {
        "cases": [
            {
                "question": QUESTION,
                "answer": "Apple's total net sales were $391,035 in 2024 [Source 2].",
            }
        ]
    }
    artifact_path = tmp_path / "artifact.json"
    results_path = tmp_path / "results.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    results_path.write_text(json.dumps(results), encoding="utf-8")
    return results_path, artifact_path


def test_packed_audit_uses_packed_source_numbering(tmp_path) -> None:
    results_path, artifact_path = _write_inputs(tmp_path)

    full = run(results_path, artifact_path)
    packed = run(
        results_path,
        artifact_path,
        CONTEXT_STRATEGY_SELECTIVE_V2,
    )

    assert full["context_strategy"] == "full_evidence_v1"
    assert full["num_numeric_review_cases"] == 1
    assert packed["context_strategy"] == CONTEXT_STRATEGY_SELECTIVE_V2
    assert packed["num_numeric_review_cases"] == 0
    assert packed["cases"][0]["canonical_citations"] == (2,)
