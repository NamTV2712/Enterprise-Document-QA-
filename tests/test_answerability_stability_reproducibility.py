import copy
import json

from scripts.diagnostics.answerability_stability_v1_reproducibility import (
    CANDIDATE_STRATEGY,
    SENTINEL_QUESTIONS,
    validate_report,
)
from scripts.run_answerability_stability_sentinel import (
    ProviderCallBudget,
    ProviderCallBudgetExceeded,
)
from src.evaluation.generation_checkpoint import sha256_text
from src.evaluation.judge_checkpoint import compute_judge_binding
from src.evaluation.phase2_runtime import JUDGE_CONTEXT_BUILDER_FINGERPRINT
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
)


def _valid_report(tmp_path):
    generation_path = tmp_path / "generation.jsonl"
    judge_path = tmp_path / "judge.jsonl"
    generation_binding = "sha256:" + "a" * 64
    answers = {question: f"Answer for {question} [Source 1]" for question in SENTINEL_QUESTIONS}
    generation_records = [
        {
            "question": question,
            "binding": generation_binding,
            "status": "OK",
            "answer": answers[question],
            "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        }
        for question in SENTINEL_QUESTIONS
    ]
    judge_bindings = {
        question: compute_judge_binding(
            generation_binding=generation_binding,
            generation_answer_sha256s=sha256_text(json.dumps(
                [sha256_text(answers[question])],
                separators=(",", ":"),
            )),
            judge_model="test-model",
            judge_prompt_template_sha256="sha256:" + "b" * 64,
            judge_max_tokens=2048,
            judge_context_fingerprint=JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        )
        for question in SENTINEL_QUESTIONS
    }
    judge_records = [
        {
            "question": question,
            "binding": judge_bindings[question],
            "status": "OK",
            "model": "test-model",
            "judge_prompt_template_sha256": "sha256:" + "b" * 64,
            "judge_max_tokens": 2048,
            "judge_context_fingerprint": JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        }
        for question in SENTINEL_QUESTIONS
    ]
    generation_path.write_text(
        "".join(json.dumps(record) + "\n" for record in generation_records),
        encoding="utf-8",
    )
    judge_path.write_text(
        "".join(json.dumps(record) + "\n" for record in judge_records),
        encoding="utf-8",
    )
    return {
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "candidate_strategy": CANDIDATE_STRATEGY,
        "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "answerability_fingerprint": COMPARATIVE_ANSWERABILITY_FINGERPRINT,
        "binding": generation_binding,
        "cases": [
            {"question": question, "answer": answers[question]}
            for question in SENTINEL_QUESTIONS
        ],
        "context_rows": {
            question: {
                "context_sha256": "sha256:" + "c" * 64,
                "source_count": 1,
                "context_deterministic": True,
            }
            for question in SENTINEL_QUESTIONS
        },
        "checkpoint_provenance": {
            "generation_checkpoint": str(generation_path),
            "judge_checkpoint": str(judge_path),
            "generation_bindings": [generation_binding],
            "judge_context_fingerprints": [JUDGE_CONTEXT_BUILDER_FINGERPRINT],
            "judge_bindings": sorted(set(judge_bindings.values())),
        },
    }, generation_path, judge_path


def test_validate_report_accepts_complete_matching_checkpoints(tmp_path) -> None:
    report, _, _ = _valid_report(tmp_path)

    assert validate_report(report, tmp_path / "report.json") == ()


def test_validate_report_rejects_missing_context_rows(tmp_path) -> None:
    report, _, _ = _valid_report(tmp_path)
    malformed = copy.deepcopy(report)
    malformed.pop("context_rows")

    errors = validate_report(malformed, tmp_path / "report.json")

    assert any("context_rows" in error for error in errors)


def test_validate_report_rejects_fingerprint_mismatch(tmp_path) -> None:
    report, _, _ = _valid_report(tmp_path)
    malformed = copy.deepcopy(report)
    malformed["checkpoint_provenance"]["judge_context_fingerprints"] = [
        "sha256:" + "d" * 64
    ]

    errors = validate_report(malformed, tmp_path / "report.json")

    assert any("report judge context fingerprints" in error for error in errors)


def test_validate_report_rejects_judge_binding_mismatch(tmp_path) -> None:
    report, _, judge_path = _valid_report(tmp_path)
    records = [json.loads(line) for line in judge_path.read_text().splitlines()]
    records[0]["binding"] = "sha256:" + "e" * 64
    judge_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    errors = validate_report(report, tmp_path / "report.json")

    assert any("judge binding mismatch" in error for error in errors)


def test_provider_call_budget_fails_before_the_next_request() -> None:
    calls: list[str] = []
    bounded = ProviderCallBudget(1).wrap(lambda value: calls.append(value) or value)

    assert bounded("first") == "first"
    try:
        bounded("second")
    except ProviderCallBudgetExceeded:
        pass
    else:
        raise AssertionError("budget should reject the second request")

    assert calls == ["first"]
