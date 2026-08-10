from types import SimpleNamespace

import pytest

from scripts.diagnostics.context_duplicate_metrics import classify_correlation_cohort
from scripts.diagnostics.replay_contract import (
    ReplayQueryFacts,
    ReplayQueryPlan,
    build_case_diagnostic_from_replay,
    build_replay_plan_from_evaluation_record,
    build_replay_record,
    execute_retrieval_replay,
)

class _FakeRetriever:
    def __init__(self, results_by_query: dict[str, list[SimpleNamespace]]):
        self.results_by_query = results_by_query
        self.calls: list[dict] = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        return self.results_by_query[kwargs["query"]]


def _chunk(
    chunk_id: str,
    text: str,
    *,
    ticker: str = "AAPL",
    section: str = "risk_factors",
    accession_number: str = "0000320193-25-000079",
    chunk_index: int = 0,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "ticker": ticker,
        "section": section,
        "accession_number": accession_number,
        "chunk_index": chunk_index,
        "text": text,
    }

def test_direct_replay_keeps_effective_query_and_chunk_ids_as_raw_facts() -> None:
    record = build_replay_record(
        original_question="What was Apple's revenue?",
        route="direct",
        corpus_source="cloud",
        top_k=5,
        executed_queries=(
            ReplayQueryFacts(
                effective_query="What was Apple's revenue?",
                query_source="original_question",
                ticker="AAPL",
                section="financial_table",
                retrieved_chunk_ids=("AAPL_1", "AAPL_2"),
            ),
        ),
        final_chunk_ids=("AAPL_1", "AAPL_2"),
    )

    assert record.facts.executed_queries[0].effective_query == (
        "What was Apple's revenue?"
    )
    assert record.facts.final_chunk_ids == ("AAPL_1", "AAPL_2")
    assert record.assessment.query_fidelity == "high"
    assert record.assessment.reasons == ("exact_original_query",)


def test_saved_subquery_replay_is_high_fidelity_after_final_deduplication() -> None:
    record = build_replay_record(
        original_question="Compare Apple and Microsoft revenue.",
        route="decomposed",
        corpus_source="local",
        top_k=5,
        executed_queries=(
            ReplayQueryFacts(
                effective_query="What was Apple's revenue?",
                query_source="saved_subquery",
                ticker="AAPL",
                section="financial_table",
                retrieved_chunk_ids=("AAPL_1", "SHARED"),
            ),
            ReplayQueryFacts(
                effective_query="What was Microsoft's revenue?",
                query_source="saved_subquery",
                ticker="MSFT",
                section="financial_table",
                retrieved_chunk_ids=("MSFT_1", "SHARED"),
            ),
        ),
        final_chunk_ids=("AAPL_1", "SHARED", "MSFT_1"),
    )

    assert record.assessment.query_fidelity == "high"
    assert record.assessment.reasons == ("saved_subqueries_reused",)
    assert record.facts.final_chunk_ids.count("SHARED") == 1


def test_regenerated_rewrite_stays_auditable_but_is_correlation_ineligible() -> None:
    record = build_replay_record(
        original_question="What was Amazon's revenue growth?",
        route="direct",
        corpus_source="cloud",
        top_k=5,
        executed_queries=(
            ReplayQueryFacts(
                effective_query=(
                    "Amazon total net sales revenue growth fiscal year table"
                ),
                query_source="regenerated_rewrite",
                ticker="AMZN",
                section=None,
                retrieved_chunk_ids=("AMZN_1",),
            ),
        ),
        final_chunk_ids=("AMZN_1",),
    )
    diagnostic = build_case_diagnostic_from_replay(
        replay_record=record,
        category="fact_lookup",
        official_context_precision=0.2,
        chunks=[_chunk("AMZN_1", "revenue evidence", ticker="AMZN")],
    )

    assert record.facts.executed_queries[0].effective_query.startswith("Amazon")
    assert record.assessment.query_fidelity == "low"
    assert record.assessment.reasons == (
        "regenerated_rewrite_not_historical",
    )
    assignment = classify_correlation_cohort(diagnostic)
    assert assignment.eligible is False
    assert assignment.exclusion_reason == "insufficient_replay_fidelity"


def test_replay_record_rejects_final_chunk_not_returned_by_any_query() -> None:
    with pytest.raises(ValueError, match="not returned by an executed query"):
        build_replay_record(
            original_question="Question",
            route="direct",
            corpus_source="local",
            top_k=5,
            executed_queries=(
                ReplayQueryFacts(
                    effective_query="Question",
                    query_source="original_question",
                    ticker=None,
                    section=None,
                    retrieved_chunk_ids=("A",),
                ),
            ),
            final_chunk_ids=("A", "UNKNOWN"),
        )


def test_original_proxy_for_missing_historical_rewrite_is_low_fidelity() -> None:
    record = build_replay_record(
        original_question="What was Amazon's revenue growth?",
        route="direct",
        corpus_source="cloud",
        top_k=5,
        executed_queries=(
            ReplayQueryFacts(
                effective_query="What was Amazon's revenue growth?",
                query_source="original_proxy_missing_rewrite",
                ticker="AMZN",
                section=None,
                retrieved_chunk_ids=(),
            ),
        ),
        final_chunk_ids=(),
    )

    assert record.assessment.query_fidelity == "low"
    assert record.assessment.reasons == (
        "historical_effective_query_unavailable",
    )


def test_case_diagnostic_rejects_chunks_from_a_different_replay_context() -> None:
    record = build_replay_record(
        original_question="Question",
        route="direct",
        corpus_source="local",
        top_k=5,
        executed_queries=(
            ReplayQueryFacts(
                effective_query="Question",
                query_source="original_question",
                ticker=None,
                section=None,
                retrieved_chunk_ids=("A", "B"),
            ),
        ),
        final_chunk_ids=("A", "B"),
    )

    with pytest.raises(ValueError, match="preserve replay final_chunk_ids"):
        build_case_diagnostic_from_replay(
            replay_record=record,
            category="fact_lookup",
            official_context_precision=0.4,
            chunks=[
                _chunk("A", "first"),
                _chunk("C", "wrong second chunk"),
            ],
        )


def test_direct_replay_adapter_executes_route_and_hydrates_canonical_chunks() -> None:
    retriever = _FakeRetriever(
        {
            "effective direct query": [
                SimpleNamespace(chunk_id="A", score=0.9),
                SimpleNamespace(chunk_id="B", score=0.8),
            ]
        }
    )
    chunk_catalog = {
        "A": {
            "chunk_id": "A",
            "ticker": "AAPL",
            "section": "risk_factors",
            "accession_number": "filing",
            "chunk_index": 1,
            "text": "first",
            "embedding": [0.1],
        },
        "B": {
            "chunk_id": "B",
            "ticker": "AAPL",
            "section": "risk_factors",
            "accession_number": "filing",
            "chunk_index": 2,
            "text": "second",
            "embedding": [0.2],
        },
    }

    execution = execute_retrieval_replay(
        retriever=retriever,
        original_question="Original question",
        route="direct",
        corpus_source="cloud",
        corpus_fingerprint="corpus-v1",
        retrieval_fingerprint="retrieval-v2",
        top_k=5,
        query_plans=(
            ReplayQueryPlan(
                effective_query="effective direct query",
                query_source="regenerated_rewrite",
                ticker="AAPL",
                section="risk_factors",
            ),
        ),
        chunks_by_id=chunk_catalog,
    )

    assert retriever.calls == [
        {
            "query": "effective direct query",
            "top_k": 5,
            "ticker": "AAPL",
            "section": "risk_factors",
        }
    ]
    assert execution.record.facts.corpus_source == "cloud"
    assert execution.record.facts.corpus_fingerprint == "corpus-v1"
    assert execution.record.facts.retrieval_fingerprint == "retrieval-v2"
    assert execution.record.facts.final_chunk_ids == ("A", "B")
    assert [chunk["chunk_id"] for chunk in execution.chunks] == ["A", "B"]
    assert execution.chunks[0]["chunk_index"] == 1
    assert all("embedding" not in chunk for chunk in execution.chunks)


def test_decomposed_replay_adapter_preserves_plan_order_and_deduplicates_ids() -> None:
    retriever = _FakeRetriever(
        {
            "apple query": [
                SimpleNamespace(chunk_id="A", score=0.8),
                SimpleNamespace(chunk_id="SHARED", score=0.4),
            ],
            "microsoft query": [
                SimpleNamespace(chunk_id="SHARED", score=0.9),
                SimpleNamespace(chunk_id="B", score=0.7),
            ],
        }
    )
    chunk_catalog = {
        chunk_id: {
            "chunk_id": chunk_id,
            "ticker": "AAPL" if chunk_id == "A" else "MSFT",
            "section": "financial_table",
            "accession_number": "filing",
            "chunk_index": index,
            "text": f"evidence {chunk_id}",
        }
        for index, chunk_id in enumerate(("A", "SHARED", "B"))
    }

    execution = execute_retrieval_replay(
        retriever=retriever,
        original_question="Compare revenue.",
        route="decomposed",
        corpus_source="local",
        top_k=5,
        query_plans=(
            ReplayQueryPlan(
                effective_query="apple query",
                query_source="saved_subquery",
                ticker="AAPL",
                section="financial_table",
            ),
            ReplayQueryPlan(
                effective_query="microsoft query",
                query_source="saved_subquery",
                ticker="MSFT",
                section="financial_table",
            ),
        ),
        chunks_by_id=chunk_catalog,
    )

    assert [call["query"] for call in retriever.calls] == [
        "apple query",
        "microsoft query",
    ]
    assert execution.record.facts.executed_queries[0].retrieved_chunk_ids == (
        "A",
        "SHARED",
    )
    assert execution.record.facts.executed_queries[1].retrieved_chunk_ids == (
        "SHARED",
        "B",
    )
    assert execution.record.facts.final_chunk_ids == ("A", "SHARED", "B")
    assert execution.record.assessment.query_fidelity == "high"


def test_replay_adapter_rejects_retrieval_id_missing_from_corpus_catalog() -> None:
    retriever = _FakeRetriever(
        {"Question": [SimpleNamespace(chunk_id="UNKNOWN", score=0.9)]}
    )

    with pytest.raises(ValueError, match="missing from the corpus catalog"):
        execute_retrieval_replay(
            retriever=retriever,
            original_question="Question",
            route="direct",
            corpus_source="cloud",
            top_k=5,
            query_plans=(
                ReplayQueryPlan(
                    effective_query="Question",
                    query_source="original_question",
                    ticker=None,
                    section=None,
                ),
            ),
            chunks_by_id={},
        )


def test_replay_adapter_rejects_invalid_route_plan_before_retrieval() -> None:
    retriever = _FakeRetriever({"Question": []})

    with pytest.raises(ValueError, match="invalid for route"):
        execute_retrieval_replay(
            retriever=retriever,
            original_question="Question",
            route="decomposed",
            corpus_source="local",
            top_k=5,
            query_plans=(
                ReplayQueryPlan(
                    effective_query="Question",
                    query_source="original_question",
                    ticker=None,
                    section=None,
                ),
            ),
            chunks_by_id={},
        )

    assert retriever.calls == []


def test_artifact_builder_uses_original_query_when_no_rewrite_was_required() -> None:
    plan = build_replay_plan_from_evaluation_record(
        {
            "question": "What risks does Apple describe?",
            "category": "summary",
            "ticker": "AAPL",
            "section": "risk_factors",
            "status": "OK",
            "context_precision": 0.8,
            "fingerprint": "case-v1",
            "was_decomposed": False,
            "sub_queries": [],
        },
        requires_rewrite=lambda question: False,
        missing_rewrite_strategy="original_proxy",
    )

    assert plan.original_question == "What risks does Apple describe?"
    assert plan.route == "direct"
    assert plan.category == "summary"
    assert plan.official_context_precision == 0.8
    assert plan.evaluation_case_fingerprint == "case-v1"
    assert plan.query_plans == (
        ReplayQueryPlan(
            effective_query="What risks does Apple describe?",
            query_source="original_question",
            ticker="AAPL",
            section="risk_factors",
        ),
    )


def test_artifact_builder_marks_original_proxy_for_missing_historical_rewrite() -> None:
    plan = build_replay_plan_from_evaluation_record(
        {
            "question": "What was Microsoft's total assets?",
            "category": "fact_lookup",
            "ticker": "MSFT",
            "section": None,
            "status": "OK",
            "context_precision": 0.2,
            "was_decomposed": False,
            "sub_queries": [],
        },
        requires_rewrite=lambda question: True,
        missing_rewrite_strategy="original_proxy",
    )

    assert plan.query_plans[0].effective_query == (
        "What was Microsoft's total assets?"
    )
    assert plan.query_plans[0].query_source == (
        "original_proxy_missing_rewrite"
    )


def test_artifact_builder_can_regenerate_missing_rewrite_explicitly() -> None:
    plan = build_replay_plan_from_evaluation_record(
        {
            "question": "What was Microsoft's total assets?",
            "category": "fact_lookup",
            "ticker": "MSFT",
            "section": None,
            "status": "OK",
            "context_precision": 0.2,
            "was_decomposed": False,
            "sub_queries": [],
        },
        requires_rewrite=lambda question: True,
        missing_rewrite_strategy="regenerate",
        regenerate_query=lambda question: "balance sheet total assets query",
    )

    assert plan.query_plans[0].effective_query == (
        "balance sheet total assets query"
    )
    assert plan.query_plans[0].query_source == "regenerated_rewrite"


def test_artifact_builder_reuses_saved_subqueries_without_rewrite_inference() -> None:
    def unexpected_rewrite_check(question: str) -> bool:
        raise AssertionError("Saved subqueries must bypass direct rewrite inference")

    plan = build_replay_plan_from_evaluation_record(
        {
            "question": "Compare Apple and Microsoft revenue.",
            "category": "comparative",
            "ticker": None,
            "section": "financial_table",
            "status": "OK",
            "context_precision": 0.4,
            "was_decomposed": True,
            "sub_queries": [
                {
                    "query": "Apple revenue query",
                    "ticker": "AAPL",
                    "section": "financial_table",
                    "num_chunks": 3,
                },
                {
                    "query": "Microsoft revenue query",
                    "ticker": "MSFT",
                    "section": "financial_table",
                    "num_chunks": 2,
                },
            ],
        },
        requires_rewrite=unexpected_rewrite_check,
        missing_rewrite_strategy="original_proxy",
    )

    assert plan.route == "decomposed"
    assert [query.effective_query for query in plan.query_plans] == [
        "Apple revenue query",
        "Microsoft revenue query",
    ]
    assert [query.historical_num_chunks for query in plan.query_plans] == [3, 2]
    assert all(
        query.query_source == "saved_subquery"
        for query in plan.query_plans
    )


def test_artifact_builder_rejects_decomposed_record_without_subqueries() -> None:
    with pytest.raises(ValueError, match="no saved subqueries"):
        build_replay_plan_from_evaluation_record(
            {
                "question": "Compare companies.",
                "category": "comparative",
                "ticker": None,
                "section": None,
                "status": "OK",
                "context_precision": 0.4,
                "was_decomposed": True,
                "sub_queries": [],
            },
            requires_rewrite=lambda question: False,
            missing_rewrite_strategy="original_proxy",
        )

