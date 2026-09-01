from scripts.diagnostics.phase2_admission import (
    AWS_QUESTION,
    ENUMERATION_QUESTIONS,
    _aggregate_metric_gates,
    _baseline_metrics,
    _completion_gate,
    _metric_thresholds,
    _expected_admission_binding,
    _structural_gates,
)


def test_aggregate_admission_gates_require_baseline_non_regression() -> None:
    thresholds = {
        "faithfulness": 0.9883,
        "answer_relevancy": 0.9833,
        "context_precision": 0.7413,
        "overall_judge_average": 0.9076,
    }
    candidate = {
        "metrics": {
            "faithfulness": 0.9883,
            "answer_relevancy": 0.9833,
            "context_precision": 0.7413,
            "overall_judge_average": 0.9076,
        }
    }

    assert all(_aggregate_metric_gates(candidate, thresholds).values())

    candidate["metrics"]["overall_judge_average"] = 0.9075
    assert not _aggregate_metric_gates(candidate, thresholds)["overall"]


def test_metric_thresholds_follow_current_baseline() -> None:
    baseline = {
        "metrics": {
            "faithfulness": 0.9983,
            "answer_relevancy": 0.9833,
            "context_precision": 0.7413,
            "overall_judge_average": 0.9076,
            "categories": {},
        }
    }

    metrics = _baseline_metrics(baseline)

    assert _metric_thresholds(metrics) == {
        "faithfulness": 0.9883,
        "answer_relevancy": 0.9833,
        "context_precision": 0.7413,
        "overall_judge_average": 0.9076,
    }


def test_completion_gate_requires_only_aws_to_be_applicable() -> None:
    questions = ["apple", AWS_QUESTION, "microsoft"]
    rows = {
        question: {
            "applicable": question == AWS_QUESTION,
            "correction_attempted": question == AWS_QUESTION,
            "correction_accepted": question == AWS_QUESTION,
            "final_passed": True,
        }
        for question in questions
    }
    candidate = {"period_value_corrections": rows}

    passed, detail = _completion_gate(candidate, questions)

    assert passed
    assert detail["applicable_questions"] == [AWS_QUESTION]
    assert detail["max_one_correction"]


def test_completion_gate_rejects_second_correction() -> None:
    questions = [AWS_QUESTION, "other"]
    candidate = {
        "period_value_corrections": {
            question: {
                "applicable": True,
                "correction_attempted": True,
                "correction_accepted": True,
                "final_passed": True,
            }
            for question in questions
        }
    }

    passed, detail = _completion_gate(candidate, questions)

    assert not passed
    assert not detail["max_one_correction"]


def test_completion_gate_allows_grounding_false_for_safe_fallback_rows() -> None:
    questions = [AWS_QUESTION, *sorted(ENUMERATION_QUESTIONS), "out-of-corpus"]
    rows = {
        question: {
            "applicable": question != "out-of-corpus",
            "period_value_applicable": question == AWS_QUESTION,
            "enumeration_applicable": question in ENUMERATION_QUESTIONS,
            "correction_attempted": False,
            "correction_accepted": False,
            "final_passed": True,
            "final_grounding_passed": question != "out-of-corpus",
            "correction_attempts": 0,
        }
        for question in questions
    }
    passed, detail = _completion_gate(
        {"period_value_corrections": rows}, questions
    )

    assert passed
    assert detail["final_grounding_scope"] == "applicable_answers_only"


def test_structural_gate_accepts_complete_non_official_candidate() -> None:
    candidate = {
        "official": False,
        "provider_complete": True,
        "stopped_reason": None,
        "num_selected": 1,
        "num_generation_ok": 1,
        "num_judged_ok": 1,
        "cases": [{
            "question": "q",
            "generation_status": "OK",
            "judge_status": "OK",
        }],
        "binding": "binding",
        "bound_artifact_fingerprint": "artifact",
        "model": "model",
        "judge_model": "model",
        "context_strategy": "strategy",
    }

    gates = _structural_gates(candidate, ["q"], "binding")

    assert gates["candidate_complete"]


def test_structural_gate_binds_candidate_strategy() -> None:
    candidate = {
        "provider_complete": True,
        "stopped_reason": None,
        "num_selected": 1,
        "num_generation_ok": 1,
        "num_judged_ok": 1,
        "cases": [{
            "question": "q",
            "generation_status": "OK",
            "judge_status": "OK",
        }],
        "binding": "v4-binding",
        "bound_artifact_fingerprint": "artifact",
        "model": "model",
        "judge_model": "model",
        "context_strategy": "selective_packed_v4_candidate",
    }

    gates = _structural_gates(
        candidate,
        ["q"],
        "v4-binding",
        "selective_packed_v4_candidate",
    )

    assert gates["single_binding"]
    assert gates["strategy_bound"]


def test_official_self_check_can_use_its_recorded_historical_binding(
    tmp_path,
) -> None:
    baseline = tmp_path / "official.json"
    candidate = {
        "official": True,
        "binding": "historical-binding",
    }
    assert _expected_admission_binding(
        baseline, baseline, candidate, "current-binding"
    ) == "historical-binding"
    assert _expected_admission_binding(
        tmp_path / "candidate.json", baseline, candidate, "current-binding"
    ) == "current-binding"
