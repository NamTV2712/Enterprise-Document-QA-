from types import SimpleNamespace

import pytest

from scripts.diagnostics.diagnostic_runner import run_context_duplicate_diagnostic

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

def test_diagnostic_orchestration_reports_descriptive_and_primary_cohorts() -> None:
    records = [
        {
            "question": "high precision",
            "category": "fact_lookup",
            "ticker": "AAPL",
            "section": None,
            "status": "OK",
            "context_precision": 0.8,
            "was_decomposed": False,
            "sub_queries": [],
        },
        {
            "question": "boundary precision",
            "category": "fact_lookup",
            "ticker": "AAPL",
            "section": None,
            "status": "OK",
            "context_precision": 0.5,
            "was_decomposed": False,
            "sub_queries": [],
        },
        {
            "question": "low precision decomposed",
            "category": "comparative",
            "ticker": None,
            "section": None,
            "status": "OK",
            "context_precision": 0.2,
            "was_decomposed": True,
            "sub_queries": [
                {
                    "query": "saved low precision query",
                    "ticker": "MSFT",
                    "section": None,
                    "num_chunks": 2,
                }
            ],
        },
        {
            "question": "needs rewrite",
            "category": "fact_lookup",
            "ticker": "MSFT",
            "section": None,
            "status": "OK",
            "context_precision": 0.1,
            "was_decomposed": False,
            "sub_queries": [],
        },
        {
            "question": "out of corpus",
            "category": "out_of_corpus",
            "ticker": "NFLX",
            "section": None,
            "status": "OK",
            "context_precision": 0.0,
            "was_decomposed": False,
            "sub_queries": [],
        },
    ]
    retriever = _FakeRetriever(
        {
            "high precision": [
                SimpleNamespace(chunk_id="A", score=0.9),
                SimpleNamespace(chunk_id="B", score=0.8),
            ],
            "boundary precision": [
                SimpleNamespace(chunk_id="C", score=0.9),
                SimpleNamespace(chunk_id="D", score=0.8),
                SimpleNamespace(chunk_id="E", score=0.7),
            ],
            "saved low precision query": [
                SimpleNamespace(chunk_id="F", score=0.9),
                SimpleNamespace(chunk_id="G", score=0.8),
            ],
            "needs rewrite": [SimpleNamespace(chunk_id="H", score=0.9)],
            "out of corpus": [],
        }
    )
    texts = {
        "A": "unique first",
        "B": "unique second",
        "C": "one repeated fact",
        "D": " ONE  REPEATED FACT ",
        "E": "unique third",
        "F": "fully duplicated evidence",
        "G": "FULLY DUPLICATED EVIDENCE",
        "H": "proxy result",
    }
    chunks = [
        _chunk(chunk_id, text, chunk_index=index * 3)
        for index, (chunk_id, text) in enumerate(texts.items())
    ]

    report = run_context_duplicate_diagnostic(
        records=records,
        retriever=retriever,
        chunks=chunks,
        corpus_source="local",
        corpus_fingerprint="corpus-v1",
        retrieval_fingerprint="retrieval-v1",
        top_k=5,
        requires_rewrite=lambda question: question == "needs rewrite",
        missing_rewrite_policy="original_proxy",
        semantic_similarity_provider=lambda replayed_chunks: {},
        semantic_thresholds=(0.95,),
    )

    assert report.metadata.missing_rewrite_policy == "original_proxy"
    assert report.planned_cases == 5
    assert report.planned_primary_eligible_cases == 3
    assert report.successful_replays == 5
    assert report.primary_eligible_cases == 3
    assert len(report.cases) == 5
    assert report.failures == ()
    proxy_case = next(
        case
        for case in report.cases
        if case.diagnostic.question == "needs rewrite"
    )
    assert proxy_case.replay_record.facts.missing_rewrite_policy == (
        "original_proxy"
    )
    assert proxy_case.diagnostic.replay_fidelity == "low"

    associations = {
        association.metric_name: association
        for association in report.associations
    }
    exact = associations["exact_duplicate_pair_rate"]
    assert exact.eligible_cases == 3
    assert exact.exclusion_counts == {
        "insufficient_replay_fidelity": 1,
        "out_of_corpus": 1,
    }
    assert exact.spearman.coefficient == pytest.approx(-1.0)
    assert set(report.group_diagnostics) == {"category", "ticker", "section"}


def test_diagnostic_orchestration_records_replay_failure_without_empty_context() -> None:
    record = {
        "question": "missing result",
        "category": "fact_lookup",
        "ticker": "AAPL",
        "section": None,
        "status": "OK",
        "context_precision": 0.4,
        "was_decomposed": False,
        "sub_queries": [],
    }
    retriever = _FakeRetriever(
        {"missing result": [SimpleNamespace(chunk_id="UNKNOWN", score=0.9)]}
    )

    report = run_context_duplicate_diagnostic(
        records=[record],
        retriever=retriever,
        chunks=[],
        corpus_source="cloud",
        top_k=5,
        requires_rewrite=lambda question: False,
        missing_rewrite_policy="original_proxy",
        semantic_similarity_provider=lambda replayed_chunks: {},
    )

    assert report.planned_primary_eligible_cases == 1
    assert report.successful_replays == 0
    assert report.primary_eligible_cases == 0
    assert report.cases == ()
    assert len(report.failures) == 1
    assert report.failures[0].question == "missing result"
    assert report.failures[0].error_type == "ValueError"
    assert "missing from the corpus catalog" in report.failures[0].message

