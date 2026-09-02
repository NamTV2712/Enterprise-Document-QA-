from scripts.diagnostics.fact_candidate_variance import build_variance_report


def _case(question: str, category: str, answer: str, relevancy: float) -> dict:
    return {
        "question": question,
        "category": category,
        "answer": answer,
        "scores": {
            "faithfulness": 1.0,
            "answer_relevancy": relevancy,
            "context_precision": 1.0,
        },
    }


def test_variance_report_classifies_unchanged_context_answer_drift(tmp_path) -> None:
    questions = [
        "What quality and manufacturing risks does Apple mention?",
        "How does Microsoft describe its Azure and cloud services growth?",
        "What are the main sources of revenue for Microsoft?",
    ]
    # The helper contract is exercised with a full synthetic priority-2 set;
    # the repository test set supplies the remaining rows and artifact fields.
    from src.evaluation.test_set import TEST_SET

    official_cases = []
    candidate_cases = []
    artifact_cases = []
    for test_case in TEST_SET:
        if test_case.priority > 2:
            continue
        question = test_case.question
        answer = "stable answer"
        relevancy = 1.0
        if question in questions:
            answer = f"candidate answer for {question}"
            relevancy = 0.9
        official_cases.append(_case(question, test_case.category, "stable answer", 1.0))
        candidate_cases.append(_case(question, test_case.category, answer, relevancy))
        artifact_cases.append({
            "question": question,
            "chunks": [],
            "retrieval": {},
        })

    # Use the real frozen artifact shape for rendering; this test only checks
    # the report contract and does not make any provider call.
    import json
    from pathlib import Path

    artifact_path = Path("data/eval_artifacts/phase1_priority2.json")
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    official = {"cases": official_cases}
    candidate = {"cases": candidate_cases}
    # Replace synthetic artifact rows with real rows while preserving the
    # synthetic answer/score comparison above.
    report = build_variance_report(
        official,
        candidate,
        artifact,
        official_path=Path("data/eval_artifacts/phase2_results_packed_selective_v2.json"),
        candidate_path=Path("data/eval_artifacts/phase2_results_fact_evidence_v1_candidate.json"),
    )

    assert report["num_cases"] == 30
    assert report["gates"]["case_set_complete"]
    assert report["gates"]["non_fact_contexts_byte_identical"]
    assert report["gates"]["regressions_have_unchanged_context"]
