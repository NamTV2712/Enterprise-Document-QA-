"""Hermetic tests for the official Phase 2 evaluation runner."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import pytest

from scripts.run_evaluation_phase2 import (
    EVAL_MODEL,
    compute_case_metrics,
    load_bound_artifact,
    run_phase2,
    select_questions,
)
from src.evaluation.evaluator import JudgeParseError
from src.evaluation.generation_checkpoint import (
    GenerationCheckpointStore,
    GenerationUpstream,
)
from src.evaluation.judge_checkpoint import (
    JudgeCheckpointStore,
    JudgeParseErrorStub,
)

PIN = "sha256:" + "0" * 64

APPLE_Q = "What was Apple's total net sales in fiscal year 2024?"
NETFLIX_Q = "What is Netflix's revenue in 2024?"

APPLE_ANSWER = (
    "Apple's total net sales in fiscal year 2024 were $391,035 million "
    "[Source 1]."
)
NETFLIX_FALLBACK = (
    "I could not find sufficient information in the available documents "
    "to answer this question with confidence. The most relevant sections "
    "I found were: [list sources]."
)


def _scores(faithfulness: float = 1.0) -> dict:
    return {
        "faithfulness": faithfulness,
        "faithfulness_reason": "r",
        "answer_relevancy": 1.0,
        "relevancy_reason": "r",
        "context_precision": 0.5,
        "precision_reason": "r",
    }


def _artifact_payload() -> dict:
    return {
        "schema_version": 1,
        "fingerprints": {"artifact": PIN},
        "cases": [
            {
                "question": APPLE_Q,
                "category": "fact_lookup",
                "route": "direct",
                "queries": [
                    {
                        "query": {
                            "effective_query": APPLE_Q,
                            "ticker": "AAPL",
                            "section": None,
                            "query_source": "original_question",
                        },
                        "chunks": [
                            {
                                "chunk_id": "AAPL_c0",
                                "citation": "AAPL 10-K",
                                "text": "Total net sales $391,035 million.",
                            }
                        ],
                    }
                ],
                "final_chunk_ids": ["AAPL_c0"],
            },
            {
                "question": NETFLIX_Q,
                "category": "out_of_corpus",
                "route": "direct",
                "queries": [
                    {
                        "query": {
                            "effective_query": NETFLIX_Q,
                            "ticker": None,
                            "section": None,
                            "query_source": "original_question",
                        },
                        "chunks": [
                            {
                                "chunk_id": "NFLX_MISS_c0",
                                "citation": "AMZN 10-K",
                                "text": "Consolidated net sales increased.",
                            }
                        ],
                    }
                ],
                "final_chunk_ids": ["NFLX_MISS_c0"],
            },
        ],
    }


def _selected_two():
    from src.evaluation.test_set import TEST_SET

    by_q = {tc.question: tc for tc in TEST_SET}
    return [by_q[APPLE_Q], by_q[NETFLIX_Q]]


def _upstream(tmp_path: Path) -> GenerationUpstream:
    return GenerationUpstream(
        artifact_path=tmp_path / "artifact.json",
        artifact_sha256="sha256:" + "1" * 64,
        artifact_schema_version=1,
        model="test-model",
    )


def _run(
    tmp_path: Path,
    answers: dict[str, str],
    judge_scores: list[dict | Exception],
    fail_generation_on_call: int | None = None,
):
    case_by_question = {
        case["question"]: case
        for case in _artifact_payload()["cases"]
    }
    answer_queue = deque(
        [answers[tc.question] for tc in _selected_two()]
    )
    judge_queue = deque(judge_scores)
    call_counter = {"generation": 0}

    def generate_fn(prompt: str) -> str:
        call_counter["generation"] += 1
        if (
            fail_generation_on_call is not None
            and call_counter["generation"] == fail_generation_on_call
        ):
            raise RuntimeError("Error code: 429 - Too Many Requests")
        return answer_queue.popleft()

    def judge_fn(prompt: str) -> dict:
        outcome = judge_queue.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    summary = run_phase2(
        selected=_selected_two(),
        case_by_question=case_by_question,
        upstream=_upstream(tmp_path),
        bound_fingerprint=PIN,
        generate_fn=generate_fn,
        judge_fn=judge_fn,
        generation_store=GenerationCheckpointStore(
            tmp_path / "gen.jsonl"
        ),
        judge_store=JudgeCheckpointStore(tmp_path / "judge.jsonl"),
        max_gen_retries=0,
        max_judge_retries=0,
        sleep_fn=lambda seconds: None,
    )
    return summary


def test_complete_run_is_official_with_metrics(tmp_path: Path) -> None:
    summary = _run(
        tmp_path,
        answers={APPLE_Q: APPLE_ANSWER, NETFLIX_Q: NETFLIX_FALLBACK},
        judge_scores=[_scores(1.0), _scores(1.0)],
    )

    assert summary["official"] is True
    assert summary["stopped_reason"] is None
    assert summary["num_generation_ok"] == 2
    assert summary["num_judged_ok"] == 2
    metrics = summary["metrics"]
    assert metrics["num_judged_ok"] == 2
    assert metrics["faithfulness"] == 1.0
    assert metrics["overall_judge_average"] == pytest.approx(
        (1.0 + 1.0 + 0.5) / 3, abs=1e-4
    )

    deterministic = summary["deterministic"]
    # Apple case has citations and its figure in evidence; Netflix fallback
    # has no citations (excluded) but its fallback behavior is correct.
    assert deterministic["recall_proxy_avg"] == 1.0
    assert deterministic["fallback_accuracy"] == 1.0
    assert deterministic["num_citation_scored"] == 1
    assert deterministic["citation_correctness_avg"] == 1.0

    apple_case = summary["cases"][0]
    assert apple_case["generation_status"] == "OK"
    assert apple_case["judge_status"] == "OK"
    assert apple_case["scores"]["context_precision"] == 0.5
    netflix_case = summary["cases"][1]
    assert netflix_case["deterministic"]["fallback_correct"] is True


def test_generation_quota_skip_blocks_official(tmp_path: Path) -> None:
    summary = _run(
        tmp_path,
        answers={APPLE_Q: APPLE_ANSWER, NETFLIX_Q: NETFLIX_FALLBACK},
        judge_scores=[_scores(1.0)],
        fail_generation_on_call=2,
    )

    assert summary["official"] is False
    assert "GEN_SKIPPED_QUOTA" in summary["stopped_reason"]
    assert summary["num_generation_ok"] == 1
    assert summary["cases"][0]["generation_status"] == "OK"
    assert summary["cases"][1]["generation_status"] == "GEN_SKIPPED_QUOTA"
    assert summary["cases"][1]["judge_status"] == "NOT_RUN"


def test_judge_parse_invalid_blocks_official(tmp_path: Path) -> None:
    summary = _run(
        tmp_path,
        answers={APPLE_Q: APPLE_ANSWER, NETFLIX_Q: NETFLIX_FALLBACK},
        judge_scores=[
            _scores(1.0),
            JudgeParseErrorStub(str(JudgeParseError("invalid schema"))),
        ],
    )

    assert summary["official"] is False
    assert "invalid schema" in summary["stopped_reason"]
    assert summary["num_judged_ok"] == 1


def test_resume_completes_without_new_provider_calls(tmp_path: Path) -> None:
    first = _run(
        tmp_path,
        answers={APPLE_Q: APPLE_ANSWER, NETFLIX_Q: NETFLIX_FALLBACK},
        judge_scores=[_scores(1.0), _scores(0.8)],
    )
    assert first["official"] is True

    # Second run over the same stores must hit the checkpoints only.
    def boom(prompt: str):
        raise AssertionError("provider must not be called on resume")

    case_by_question = {
        case["question"]: case
        for case in _artifact_payload()["cases"]
    }
    resumed = run_phase2(
        selected=_selected_two(),
        case_by_question=case_by_question,
        upstream=_upstream(tmp_path),
        bound_fingerprint=PIN,
        generate_fn=boom,
        judge_fn=boom,
        generation_store=GenerationCheckpointStore(
            tmp_path / "gen.jsonl"
        ),
        judge_store=JudgeCheckpointStore(tmp_path / "judge.jsonl"),
        max_gen_retries=0,
        max_judge_retries=0,
        sleep_fn=lambda seconds: None,
    )

    assert resumed["official"] is True
    assert resumed["num_judged_ok"] == 2


def test_load_bound_artifact_refuses_fingerprint_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "artifact.json"
    payload = _artifact_payload()
    path.write_text(json.dumps(payload), encoding="utf-8")

    artifact, upstream = load_bound_artifact(path, PIN)
    assert upstream.model == EVAL_MODEL
    assert upstream.artifact_sha256.startswith("sha256:")

    from scripts import run_evaluation_phase2 as runner_module

    monkeypatch.setattr(
        runner_module, "TEST_SET", list(_selected_two())
    )
    selected = runner_module.select_questions(artifact, priority=2)
    assert [tc.question for tc in selected] == [APPLE_Q, NETFLIX_Q]

    with pytest.raises(RuntimeError, match="fingerprint drift"):
        load_bound_artifact(path, "sha256:" + "f" * 64)


# The FY2026-corpus Phase 1 rebuild; both runners must bind to exactly this.
CURRENT_ARTIFACT_FINGERPRINT = (
    "sha256:acc61c6382d4f3e9c46470f602a108bb76037288b3a8d28f396638d14bcbc422"
)
SUPERSEDED_FINGERPRINTS = {
    # PEP-recovery corpus before the hard-group table rebuild.
    "sha256:4098095690678549357475558a5a5c98793e8979b023f5d7617ea3c8759f9c7f",
    # Pre-FY2024-contract corpus.
    "sha256:f1129d814274e95d3b2019aa58ef840fc28817c1d82b548a613e2de697986841",
    # FY2024 contract on the annual-report-rebuild corpus.
    "sha256:8848d68b4236afbb1df5cef1be6cf9980d104bd1291703506a98d7cccd67f2ad",
}


def test_both_phase_two_runners_pin_the_current_artifact() -> None:
    from scripts import run_evaluation_phase2 as runner
    from scripts import run_quota_probe as probe

    assert probe.EXPECTED_ARTIFACT_FINGERPRINT == CURRENT_ARTIFACT_FINGERPRINT
    assert runner.EXPECTED_ARTIFACT_FINGERPRINT == CURRENT_ARTIFACT_FINGERPRINT
    assert (
        probe.EXPECTED_ARTIFACT_FINGERPRINT not in SUPERSEDED_FINGERPRINTS
    )
    assert (
        probe.EXPECTED_ARTIFACT_FINGERPRINT
        == runner.EXPECTED_ARTIFACT_FINGERPRINT
    )


@pytest.mark.parametrize("superseded", sorted(SUPERSEDED_FINGERPRINTS))
def test_superseded_artifact_fingerprints_are_refused(
    tmp_path: Path, superseded: str
) -> None:
    path = tmp_path / "artifact.json"
    payload = _artifact_payload()
    payload["fingerprints"]["artifact"] = superseded
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="fingerprint drift"):
        load_bound_artifact(path, CURRENT_ARTIFACT_FINGERPRINT)


def test_phase_two_main_never_imports_retrieval_machinery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase 2 must consume only the frozen artifact; if any heavier
    retrieval module is loaded when main() runs its hermeticity gate,
    the run must fail instead of silently rerunning retrieval."""
    import sys

    from scripts import run_evaluation_phase2 as runner

    monkeypatch.setattr(
        sys, "modules",
        {**sys.modules, "src.retrieval.hybrid_retriever": object()},
    )
    with pytest.raises(RuntimeError, match="Retrieval machinery loaded"):
        runner.main([])

    monkeypatch.undo()
    # Without forbidden modules the gate itself passes (argparse exits).
    with pytest.raises(SystemExit):
        runner.main(["--help"])


def test_compute_case_metrics_handles_missing_citations() -> None:
    case_payload = _artifact_payload()["cases"][0]
    metrics = compute_case_metrics(
        case_payload,
        answer="No citations here at all.",
        required_keywords=["391,035"],
        expects_fallback=False,
    )

    assert metrics["citation_correctness"] is None
    assert metrics["recall_proxy"] == 1.0
    # No fallback phrase while fallback is not expected: correct behavior.
    assert metrics["fallback_correct"] is True
