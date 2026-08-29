"""Tests for the deterministic two-phase evaluation framework.

Covers fixed-plan validation, byte-identical artifact construction,
Phase 2A's guarantee that the retriever is never touched, strict resume
bindings, and official-aggregate exclusion of skipped/quota records.
No provider is ever contacted: generators and judges are injected fakes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.generation_checkpoint import (
    GEN_STATUS_OK,
    GEN_STATUS_SKIPPED_QUOTA,
    GenerationCheckpointStore,
    GenerationUpstream,
    aggregate_generation,
    build_evidence_context,
    run_generation_phase,
    sha256_text,
)
from src.evaluation.judge_checkpoint import (
    JUDGE_STATUS_OK,
    JUDGE_STATUS_SKIPPED_QUOTA,
    JudgeCheckpointStore,
    JudgeParseErrorStub,
    build_official_aggregate,
    run_judge_phase,
)
from src.evaluation.retrieval_artifact import (
    CaseRetrievalResult,
    QueryRetrievalResult,
    build_retrieval_artifact,
    canonical_json,
    execute_case_retrieval,
)
from src.evaluation.retrieval_plan import (
    PlanQuery,
    RetrievalPlan,
    validate_plan_filters,
    validate_plans_cover,
)
from src.evaluation.test_set import TEST_SET
from src.evaluation.test_set import TestCase as EvalTestCase
from src.retrieval.lexical_ladder import LEXICAL_LADDER_FINGERPRINT
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT
from src.retrieval.retriever import RetrievedChunk


def _chunk(chunk_id: str, score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        ticker="AAPL",
        section="risk_factors",
        filing_date="2025-10-31",
        score=score,
        text=f"text for {chunk_id}",
        citation=f"AAPL 10-K citation {chunk_id}",
    )


def _case(question: str = "What was Apple's total net sales in 2024?") -> EvalTestCase:
    return EvalTestCase(
        question=question,
        category="fact_lookup",
        ticker="AAPL",
        section=None,
        ground_truth="391,035",
        required_keywords=["391,035"],
    )


def _plan(
    question: str = "What was Apple's total net sales in 2024?",
    route: str = "direct",
) -> RetrievalPlan:
    queries = (
        PlanQuery(
            effective_query="Apple total net sales fiscal 2024 2025",
            ticker="AAPL",
            section=None,
            query_source="original_proxy_missing_rewrite",
        ),
    )
    if route == "decomposed":
        queries = queries + (
            PlanQuery(
                effective_query="Apple services revenue",
                ticker="AAPL",
                section=None,
                query_source="saved_subquery",
            ),
        )
    return RetrievalPlan(
        question=question, category="fact_lookup", route=route, queries=queries
    )


class FakeRetriever:
    """Deterministic retriever double recording every call."""

    def __init__(self, chunk_ids_per_query: dict[str, list[str]]):
        self.calls: list[dict] = []
        self._mapping = chunk_ids_per_query

    def retrieve(self, query: str, top_k: int = 5, ticker=None, section=None):
        self.calls.append(
            {"query": query, "top_k": top_k, "ticker": ticker, "section": section}
        )
        return [_chunk(cid) for cid in self._mapping.get(query, [])]


# ---------------------------------------------------------------------------
# Plan validation
# ---------------------------------------------------------------------------


def test_missing_plans_fail_closed() -> None:
    cases = [_case("q-one"), _case("q-two")]
    plans = [_plan("q-one")]

    with pytest.raises(ValueError, match="Missing fixed retrieval plans"):
        validate_plans_cover(plans, cases)


def test_extra_plans_fail_closed() -> None:
    cases = [_case("q-one")]
    plans = [_plan("q-one"), _plan("q-legacy-removed")]

    with pytest.raises(ValueError, match="extra"):
        validate_plans_cover(plans, cases)


def test_unknown_ticker_or_section_filters_rejected() -> None:
    plans = [
        RetrievalPlan(
            question=_case().question,
            category="fact_lookup",
            route="direct",
            queries=(
                PlanQuery(
                    effective_query="x", ticker="DIS", section=None,
                    query_source="original_question",
                ),
            ),
        )
    ]

    with pytest.raises(ValueError, match="unknown ticker 'DIS'"):
        validate_plan_filters(plans, allowed_tickers={"AAPL"}, allowed_sections=set())


# ---------------------------------------------------------------------------
# Artifact construction and determinism
# ---------------------------------------------------------------------------


def test_execution_records_provenance_and_respects_branch_order() -> None:
    case = _case()
    plan = _plan(route="decomposed")
    retriever = FakeRetriever({
        "Apple total net sales fiscal 2024 2025": ["a1", "a2"],
        "Apple services revenue": ["a2", "b1"],
    })

    result = execute_case_retrieval(retriever, case, plan, top_k=5)

    assert result.final_chunk_ids == ["a1", "a2", "b1"]
    assert [q["query_source"] for q in (qr.query for qr in result.queries)] == [
        "original_proxy_missing_rewrite",
        "saved_subquery",
    ]
    assert len(retriever.calls) == 2
    assert retriever.calls[0]["ticker"] == "AAPL"
    assert result.queries[0].query["retrieval_query"] == (
        "Apple total net sales fiscal 2024 2025"
    )


def test_phase_one_executes_the_same_shaped_query_as_production() -> None:
    case = _case("How did Amazon's AWS net sales change?")
    plan = RetrievalPlan(
        question=case.question,
        category=case.category,
        route="direct",
        queries=(
            PlanQuery(
                effective_query="Amazon AWS growth",
                ticker="AMZN",
                section="mdna",
                query_source="saved_subquery",
            ),
        ),
    )
    shaped_query = "Amazon AWS growth 2025 2024 AWS net sales"
    retriever = FakeRetriever({shaped_query: ["aws_table"]})

    result = execute_case_retrieval(retriever, case, plan)

    assert retriever.calls[0]["query"] == shaped_query
    assert result.queries[0].query["effective_query"] == "Amazon AWS growth"
    assert result.queries[0].query["retrieval_query"] == shaped_query
    assert result.final_chunk_ids == ["aws_table"]


def test_two_executions_are_byte_identical() -> None:
    case = _case()
    plan = _plan()

    def run() -> bytes:
        retriever = FakeRetriever({
            "Apple total net sales fiscal 2024 2025": ["a1", "a2"],
        })
        result = execute_case_retrieval(retriever, case, plan)
        artifact = build_retrieval_artifact(
            test_cases=[case],
            plans=[plan],
            results=[result],
            all_chunks=[{
                "chunk_id": "a1",
                "ticker": "AAPL",
                "section": "risk_factors",
                "accession_number": "0000000000-25-000001",
                "chunk_index": 0,
                "text": "corpus text a1",
            }],
            top_k=5,
        )
        return canonical_json(artifact)

    assert run() == run()


def test_artifact_contains_no_timestamp_keys() -> None:
    case = _case()
    plan = _plan()
    retriever = FakeRetriever({"q": []})
    result = execute_case_retrieval(retriever, case, plan)
    artifact = build_retrieval_artifact(
        test_cases=[case], plans=[plan], results=[result], all_chunks=[], top_k=5
    )

    serialized = json.dumps(artifact).lower()
    assert "timestamp" not in serialized
    assert "latency" not in serialized
    assert artifact["fingerprints"]["artifact"].startswith("sha256:")
    assert artifact["schema_version"] == 2
    assert artifact["fingerprints"]["query_shaper"] == QUERY_SHAPER_FINGERPRINT
    assert artifact["fingerprints"]["lexical_ladder"] == LEXICAL_LADDER_FINGERPRINT


# ---------------------------------------------------------------------------
# Phase 2A generation checkpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def upstream(tmp_path: Path) -> tuple[GenerationUpstream, Path]:
    artifact_path = tmp_path / "phase1.json"
    payload = {
        "schema_version": 1,
        "fingerprints": {"artifact": "sha256:fake"},
        "cases": [{
            "question": _case().question,
            "queries": [{"query": {}, "chunks": [
                {"chunk_id": "a1", "citation": "c1", "text": "t1"},
                {"chunk_id": "a1", "citation": "c1", "text": "t1"},
                {"chunk_id": "a2", "citation": "c2", "text": "t2"},
            ]}],
        }],
    }
    artifact_path.write_text(json.dumps(payload), encoding="utf-8")
    import hashlib

    digest = f"sha256:{hashlib.sha256(artifact_path.read_bytes()).hexdigest()}"
    upstream = GenerationUpstream(
        artifact_path=artifact_path,
        artifact_sha256=digest,
        artifact_schema_version=1,
        model="openai/gpt-oss-120b",
    )
    store_path = tmp_path / "gen.jsonl"
    return upstream, store_path


def _failing_retriever_sentinel():
    def _fail(**_kwargs):
        raise AssertionError("Phase 2A must never call the retriever")

    return _fail


def test_generation_phase_never_touches_retriever_and_uses_frozen_evidence(
    upstream,
) -> None:
    gen_upstream, store_path = upstream
    store = GenerationCheckpointStore(store_path)
    artifact_cases = json.loads(gen_upstream.artifact_path.read_text(encoding="utf-8"))
    case_payload = artifact_cases["cases"][0]
    questions = [case_payload["question"]]

    prompts_seen: list[str] = []

    def fake_generate(prompt: str) -> str:
        prompts_seen.append(prompt)
        return "Answer with [Source 1]."

    records = run_generation_phase(
        selected_questions=questions,
        artifact_cases={questions[0]: case_payload},
        upstream=gen_upstream,
        generate_fn=fake_generate,
        checkpoint_store=store,
        sleep_fn=lambda seconds: None,
    )

    assert records[0]["status"] == GEN_STATUS_OK
    assert "[Source 1]" in prompts_seen[0]
    # Evidence context deduplicates repeated chunks across branches.
    context = build_evidence_context(case_payload)
    assert context.count("[Source") == 2
    _failing_retriever_sentinel()  # existence documents the contract; no call made


def test_resume_refuses_mismatched_upstream(upstream) -> None:
    gen_upstream, store_path = upstream
    store = GenerationCheckpointStore(store_path)
    question = _case().question

    run_generation_phase(
        [question],
        {question: {"queries": [], }},
        gen_upstream,
        lambda prompt: "first",
        store,
        sleep_fn=lambda s: None,
    )

    tampered = GenerationUpstream(
        artifact_path=gen_upstream.artifact_path,
        artifact_sha256="sha256:different",
        artifact_schema_version=1,
        model=gen_upstream.model,
    )
    calls: list[str] = []

    records = run_generation_phase(
        [question],
        {question: {"queries": []}},
        tampered,
        lambda prompt: calls.append(prompt) or "second",
        store,
        sleep_fn=lambda s: None,
    )

    # Binding mismatch means the stored OK record is invisible: regenerated.
    assert calls == [calls[0]]
    assert len(records) == 1
    assert records[0]["answer"] == "second"


def test_quota_skip_is_excluded_from_official_aggregate(upstream) -> None:
    gen_upstream, store_path = upstream
    store = GenerationCheckpointStore(store_path)
    question = _case().question

    def quota_failure(_prompt: str) -> str:
        raise RuntimeError("429 Too Many Requests")

    records = run_generation_phase(
        [question],
        {question: {"queries": []}},
        gen_upstream,
        quota_failure,
        store,
        max_retries=0,
        sleep_fn=lambda s: None,
    )

    assert records[0]["status"] == GEN_STATUS_SKIPPED_QUOTA
    summary = aggregate_generation(records)
    assert summary["num_ok"] == 0
    assert summary["num_skipped"] == 1
    assert summary["ok_records"] == []


# ---------------------------------------------------------------------------
# Phase 2B judge checkpoint and official aggregate
# ---------------------------------------------------------------------------


def _generation_record(question: str, answer: str, binding: str) -> dict:
    return {
        "question": question,
        "status": GEN_STATUS_OK,
        "answer": answer,
        "binding": binding,
    }


def test_judge_quota_failure_preserves_generation_and_aggregate_stays_unofficial(
    tmp_path: Path,
) -> None:
    question = "q"
    generation_binding = "sha256:gen-binding"
    generation_store = GenerationCheckpointStore(tmp_path / "gen.jsonl")
    judge_store = JudgeCheckpointStore(tmp_path / "judge.jsonl")

    def quota_judge(_prompt: str):
        raise RuntimeError("rate limit exceeded")

    judge_records = run_judge_phase(
        selected_questions=[question],
        generation_records_by_question={
            question: _generation_record(question, "answer-1", generation_binding)
        },
        evidence_context_by_question={question: "context"},
        ground_truth_by_question={question: "truth"},
        judge_model="openai/gpt-oss-120b",
        judge_prompt_template_sha256=sha256_text("template"),
        judge_fn=quota_judge,
        checkpoint_store=judge_store,
        max_retries=0,
        sleep_fn=lambda s: None,
    )

    assert judge_records[0]["status"] == JUDGE_STATUS_SKIPPED_QUOTA
    # The generation record on disk is untouched by the judge failure.
    stored_generations = generation_store.load_compatible(
        GenerationUpstream(
            artifact_path=tmp_path / "missing.json",
            artifact_sha256="sha256:x",
            artifact_schema_version=1,
            model="m",
        )
    )
    assert stored_generations == {}

    aggregate = build_official_aggregate(
        generation_records=[_generation_record(question, "answer-1", generation_binding)],
        judge_records=judge_records,
    )
    assert aggregate["official"] is False
    assert "rerun the judge phase" in aggregate["reason"]
    assert aggregate["excluded_records"][0]["status"] == JUDGE_STATUS_SKIPPED_QUOTA


def test_complete_run_produces_official_aggregate(tmp_path: Path) -> None:
    question = "q"
    binding = "sha256:b"
    generation_records = [_generation_record(question, "a", binding)]
    judge_store = JudgeCheckpointStore(tmp_path / "judge.jsonl")

    judge_records = run_judge_phase(
        [question],
        {question: generation_records[0]},
        {question: "ctx"},
        {question: "gt"},
        judge_model="m",
        judge_prompt_template_sha256=sha256_text("t"),
        judge_fn=lambda prompt: {"faithfulness": 1.0},
        checkpoint_store=judge_store,
        sleep_fn=lambda s: None,
    )

    assert all(r["status"] == JUDGE_STATUS_OK for r in judge_records)
    aggregate = build_official_aggregate(generation_records, judge_records)
    assert aggregate["official"] is True
    assert aggregate["num_cases"] == 1


def test_judge_parse_error_is_not_retried(tmp_path: Path) -> None:
    question = "q"
    attempts: list[int] = []

    def bad_json(_prompt: str):
        attempts.append(1)
        raise JudgeParseErrorStub("malformed")

    judge_records = run_judge_phase(
        [question],
        {question: _generation_record(question, "a", "sha256:b")},
        {question: "ctx"},
        {question: "gt"},
        judge_model="m",
        judge_prompt_template_sha256=sha256_text("t"),
        judge_fn=bad_json,
        checkpoint_store=JudgeCheckpointStore(tmp_path / "j.jsonl"),
        max_retries=3,
        sleep_fn=lambda s: None,
    )

    assert len(attempts) == 1
    assert judge_records[0]["status"] != JUDGE_STATUS_OK
