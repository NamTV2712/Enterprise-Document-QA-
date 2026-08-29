from __future__ import annotations

from scripts import run_comparative_packing_ab as ab


def _arm(*, candidate: bool) -> dict:
    cases = []
    for test_case in ab.comparative_cases():
        answer = "Grounded comparison [Source 1]."
        if test_case.question == ab.AWS_QUESTION:
            answer = (
                "AWS net sales increased from $107,556 to $128,725 "
                "[Source 1]."
            )
        cases.append(
            {
                "question": test_case.question,
                "answer": answer,
                "scores": {
                    "faithfulness": 0.9,
                    "answer_relevancy": 0.9,
                    "context_precision": 0.6 if candidate else 0.5,
                },
            }
        )
    return {
        "provider_complete": True,
        "num_selected": ab.EXPECTED_COMPARATIVE_CASES,
        "metrics": {
            "faithfulness": 0.9,
            "answer_relevancy": 0.9,
            "context_precision": 0.6 if candidate else 0.5,
            "overall_judge_average": 0.8 if candidate else 0.7667,
        },
        "deterministic": {
            "citation_correctness_avg": 1.0,
            "recall_proxy_avg": 1.0,
            "fallback_accuracy": 1.0,
        },
        "cases": cases,
    }


def test_comparative_slice_is_fixed_to_six_priority_two_cases() -> None:
    selected = ab.comparative_cases()

    assert len(selected) == 6
    assert all(case.category == "comparative" for case in selected)
    assert all(case.priority <= 2 for case in selected)


def test_paired_report_passes_all_preregistered_gates(monkeypatch) -> None:
    selected = ab.comparative_cases()
    contexts = {
        case.question: {
            ab.CONTEXT_STRATEGY_FULL_EVIDENCE: (
                "[Source 1] filing\nAWS values 107,556 and 128,725."
            ),
            ab.CONTEXT_STRATEGY_COMPARATIVE_V3: (
                "[Source 1] filing\nAWS values 107,556 and 128,725."
            ),
        }
        for case in selected
    }
    monkeypatch.setattr(
        ab,
        "_contexts_and_tokens",
        lambda _artifact, _selected: (
            contexts,
            {
                "baseline_tokens": 100,
                "candidate_tokens": 50,
                "reduction_pct": 50.0,
            },
        ),
    )

    report = ab.build_paired_report(
        artifact={"cases": []},
        selected=selected,
        baseline=_arm(candidate=False),
        candidate=_arm(candidate=True),
    )

    assert report["gate_passed"] is True
    assert report["metric_deltas"]["context_precision"] == 0.1
    assert all(report["aws_gate"].values())


def test_paired_report_rejects_aws_fallback(monkeypatch) -> None:
    selected = ab.comparative_cases()
    contexts = {
        case.question: {
            ab.CONTEXT_STRATEGY_FULL_EVIDENCE: "[Source 1] filing\nevidence",
            ab.CONTEXT_STRATEGY_COMPARATIVE_V3: "[Source 1] filing\nevidence",
        }
        for case in selected
    }
    monkeypatch.setattr(
        ab,
        "_contexts_and_tokens",
        lambda _artifact, _selected: (
            contexts,
            {
                "baseline_tokens": 100,
                "candidate_tokens": 50,
                "reduction_pct": 50.0,
            },
        ),
    )
    candidate = _arm(candidate=True)
    aws = next(
        case for case in candidate["cases"] if case["question"] == ab.AWS_QUESTION
    )
    aws["answer"] = (
        "I could not find sufficient information in the available documents "
        "to answer this question with confidence."
    )

    report = ab.build_paired_report(
        artifact={"cases": []},
        selected=selected,
        baseline=_arm(candidate=False),
        candidate=candidate,
    )

    assert report["gate_passed"] is False
    assert report["gates"]["aws_answer_integrity"] is False


def test_v5_candidate_paths_and_context_renderer_are_available() -> None:
    assert ab.CONTEXT_STRATEGY_COMPARATIVE_V5 in ab.CANDIDATE_PATHS
    selected = ab.comparative_cases()
    renderer = ab.context_renderer(
        ab.CONTEXT_STRATEGY_COMPARATIVE_V5,
        {case.question: case for case in selected},
    )
    payload = {
        "question": selected[0].question,
        "category": "comparative",
        "queries": [
            {
                "query": {
                    "effective_query": "Apple cloud revenue",
                    "ticker": "AAPL",
                },
                "chunks": [
                    {
                        "chunk_id": "AAPL_0",
                        "ticker": "AAPL",
                        "section": "mdna",
                        "filing_date": "2025-01-01",
                        "score": 1.0,
                        "text": "Apple cloud revenue evidence.",
                        "citation": "AAPL filing",
                    }
                ],
            },
            {
                "query": {
                    "effective_query": "Microsoft cloud revenue",
                    "ticker": "MSFT",
                },
                "chunks": [
                    {
                        "chunk_id": "MSFT_0",
                        "ticker": "MSFT",
                        "section": "mdna",
                        "filing_date": "2025-01-01",
                        "score": 1.0,
                        "text": "Microsoft cloud revenue evidence.",
                        "citation": "MSFT filing",
                    }
                ],
            },
        ],
    }

    rendered = renderer(payload)
    assert "AAPL filing" in rendered
    assert "MSFT filing" in rendered
