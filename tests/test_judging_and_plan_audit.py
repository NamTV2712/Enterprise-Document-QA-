"""Tests for gpt-oss judging hardening and decomposed-plan auditing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.diagnostics.audit_decomposed_plans import (
    STATUS_EVIDENCE_OK,
    STATUS_PLAN_GAP,
    STATUS_RETRIEVAL_MISS,
    audit_decomposed_case,
    extract_required_numbers,
    run_audit,
)
from src.evaluation.evaluator import (
    JUDGE_MAX_TOKENS,
    compute_citation_correctness,
)
from src.evaluation.judge_checkpoint import (
    compute_judge_binding,
)


# ---------------------------------------------------------------------------
# Judging hardening
# ---------------------------------------------------------------------------


def test_judge_max_tokens_raised_for_gpt_oss() -> None:
    assert JUDGE_MAX_TOKENS == 1024


def test_judge_binding_changes_with_completion_cap() -> None:
    base = dict(
        generation_binding="sha256:g",
        generation_answer_sha256s="sha256:a",
        judge_model="openai/gpt-oss-120b",
        judge_prompt_template_sha256="sha256:t",
    )
    with_default_cap = compute_judge_binding(**base)
    with_other_cap = compute_judge_binding(**base, judge_max_tokens=320)

    assert with_default_cap != with_other_cap


def test_citation_metric_accepts_cjk_brackets() -> None:
    ascii_answer = "Revenue was $100 [Source 1] and grew [Source 2]."
    cjk_answer = "Revenue was $100 【Source 1】 and grew 【Source 2】."

    assert (
        compute_citation_correctness(ascii_answer, num_sources=2)
        == compute_citation_correctness(cjk_answer, num_sources=2)
        == 1.0
    )


def test_citation_metric_still_flags_out_of_range_and_preserves_answer() -> None:
    answer = "See 【Source 5】."
    score = compute_citation_correctness(answer, num_sources=2)

    assert score == 0.0
    # The original answer text is never mutated.
    assert "【Source 5】" in answer


def test_citation_metric_returns_none_without_citations() -> None:
    assert compute_citation_correctness("no citations here", num_sources=3) is None


# ---------------------------------------------------------------------------
# Decomposed plan audit classification
# ---------------------------------------------------------------------------


def _case_payload(
    queries: list[dict],
    final_chunk_ids: list[str],
    chunks_by_id: dict[str, dict] | None = None,
) -> dict:
    default_chunks = {
        cid: {"chunk_id": cid, "text": f"text {cid}"} for cid in final_chunk_ids
    }
    merged = default_chunks | (chunks_by_id or {})
    return {
        "question": "Compare X and Y revenue",
        "category": "comparative",
        "route": "decomposed",
        "queries": [
            {"query": q, "chunks": [merged[cid] for cid in q.pop("chunk_ids", [])]}
            for q in queries
        ],
        "final_chunk_ids": final_chunk_ids,
    }


def test_extract_required_numbers_handles_currency_and_years() -> None:
    facts = extract_required_numbers(
        "grew from $512,163M in 2024 to $619,003M in 2025."
    )

    assert "512,163" in facts
    assert "619,003" in facts


def test_audit_flags_plan_gap_when_a_ticker_has_no_evidence() -> None:
    payload = _case_payload(
        queries=[
            {
                "effective_query": "Apple total revenue",
                "ticker": "AAPL",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": ["AAPL_c0"],
            },
            {
                "effective_query": "Amazon total revenue",
                "ticker": "AMZN",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": [],
            },
        ],
        final_chunk_ids=["AAPL_c0"],
    )
    report = audit_decomposed_case(payload, ["revenue"], "$391,035 vs $574,785")

    assert report["status"] == STATUS_PLAN_GAP
    assert "AMZN" in report["unbalanced_tickers"]
    assert any(r["empty"] for r in report["subqueries"])


def test_audit_flags_retrieval_miss_when_facts_absent() -> None:
    payload = _case_payload(
        queries=[
            {
                "effective_query": "Apple total revenue",
                "ticker": "AAPL",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": ["AAPL_c0"],
            },
            {
                "effective_query": "Amazon total revenue",
                "ticker": "AMZN",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": ["AMZN_c0"],
            },
        ],
        final_chunk_ids=["AAPL_c0", "AMZN_c0"],
        chunks_by_id={
            "AAPL_c0": {"chunk_id": "AAPL_c0", "text": "Apple sells iPhones."},
            "AMZN_c0": {"chunk_id": "AMZN_c0", "text": "Amazon operates retail."},
        },
    )
    report = audit_decomposed_case(
        payload, ["391,035"], "Apple $391,035 versus Amazon $574,785"
    )

    assert report["status"] == STATUS_RETRIEVAL_MISS
    assert "391,035" in report["missing_ground_truth_numbers"]


def test_audit_marks_balanced_complete_evidence_ok() -> None:
    payload = _case_payload(
        queries=[
            {
                "effective_query": "Apple total net sales",
                "ticker": "AAPL",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": ["AAPL_c0"],
            },
            {
                "effective_query": "Amazon consolidated net sales",
                "ticker": "AMZN",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": ["AMZN_c0"],
            },
        ],
        final_chunk_ids=["AAPL_c0", "AMZN_c0"],
        chunks_by_id={
            "AAPL_c0": {
                "chunk_id": "AAPL_c0",
                "text": "Total net sales were $391,035 million.",
            },
            "AMZN_c0": {
                "chunk_id": "AMZN_c0",
                "text": "Consolidated net sales were $574,785 million.",
            },
        },
    )
    report = audit_decomposed_case(
        payload, ["net sales"], "Apple $391,035M versus Amazon $574,785M"
    )

    assert report["status"] == STATUS_EVIDENCE_OK
    assert report["missing_keywords"] == []
    assert report["missing_ground_truth_numbers"] == []


def test_expected_fact_override_catches_vague_ground_truth() -> None:
    """The AAPL-vs-AMZN revenue GT is qualitative; the override pins totals."""
    payload = _case_payload(
        queries=[
            {
                "effective_query": "Apple total revenue",
                "ticker": "AAPL",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": ["AAPL_rev"],
            },
            {
                "effective_query": "Amazon total revenue",
                "ticker": "AMZN",
                "section": None,
                "query_source": "saved_subquery",
                "chunk_ids": ["AMZN_eps"],
            },
        ],
        final_chunk_ids=["AAPL_rev", "AMZN_eps"],
        chunks_by_id={
            # Real probe finding: the AMZN branch retrieved an EPS table.
            "AAPL_rev": {
                "chunk_id": "AAPL_rev",
                "text": "Total net sales $ 416,161 $ 391,035 $ 383,285",
            },
            "AMZN_eps": {
                "chunk_id": "AMZN_eps",
                "text": "Shares used in computation of basic earnings per share 10,304",
            },
        },
    )
    payload["question"] = (
        "Which company, Apple or Amazon, has higher total revenue?"
    )
    report = audit_decomposed_case(
        payload,
        ["Amazon"],
        "Amazon's consolidated net sales are significantly higher than Apple's.",
    )

    assert report["status"] == STATUS_RETRIEVAL_MISS
    assert "637,959" in report["missing_ground_truth_numbers"]


def test_run_audit_reads_artifact_and_reports_counts(tmp_path: Path) -> None:
    artifact = {
        "fingerprints": {"artifact": "sha256:test"},
        "cases": [
            {
                "question": "Compare Apple and Microsoft risk factors",
                "category": "comparative",
                "route": "decomposed",
                "queries": [
                    {
                        "query": {
                            "effective_query": "Apple risks",
                            "ticker": "AAPL",
                            "section": None,
                            "query_source": "saved_subquery",
                        },
                        "chunks": [{
                            "chunk_id": "AAPL_r0",
                            "text": "competition risk",
                        }],
                    },
                    {
                        "query": {
                            "effective_query": "Microsoft risks",
                            "ticker": "MSFT",
                            "section": None,
                            "query_source": "saved_subquery",
                        },
                        "chunks": [],
                    },
                ],
                "final_chunk_ids": ["AAPL_r0"],
            }
        ],
    }
    path = tmp_path / "phase1.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    report = run_audit(path, tmp_path / "missing_official.json")

    assert report["num_decomposed_cases"] == 1
    case = report["cases"][0]
    assert case["status"] == STATUS_PLAN_GAP
