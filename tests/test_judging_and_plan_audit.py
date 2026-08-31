"""Tests for gpt-oss judging hardening and decomposed-plan auditing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_quota_probe import (
    PROBE_CONTEXT_STRATEGY,
    PROBE_QUESTIONS,
    audit_probe_answer,
    build_probe_acceptance,
    build_probe_contexts,
)
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
from src.evaluation.frozen_plan_overrides import (
    OVERRIDE_QUESTION,
    RAW_PLANNER_OUTPUT,
    apply_frozen_plan_overrides,
    build_override_plan,
    canonical_sha256,
    compute_planner_provenance,
)
from src.evaluation.judge_checkpoint import (
    compute_judge_binding,
)
from src.evaluation.retrieval_plan import PlanQuery, RetrievalPlan
from src.evaluation.test_set import TestCase as EvalTestCase


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


def test_judge_binding_changes_with_context_builder() -> None:
    base = dict(
        generation_binding="sha256:g",
        generation_answer_sha256s="sha256:a",
        judge_model="openai/gpt-oss-120b",
        judge_prompt_template_sha256="sha256:t",
    )

    assert compute_judge_binding(
        **base, judge_context_fingerprint="sha256:old"
    ) != compute_judge_binding(
        **base, judge_context_fingerprint="sha256:new"
    )


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


def test_comparative_probe_acceptance_distinguishes_years() -> None:
    question = PROBE_QUESTIONS[1]

    latest_year = build_probe_acceptance(
        question,
        "Amazon is higher: Apple $416,161 and Amazon $716,924 [Source 1].",
        1.0,
    )
    fiscal_2024 = build_probe_acceptance(
        question,
        "Amazon is higher: Apple $391,035 and Amazon $637,959 [Source 1].",
        1.0,
    )

    assert latest_year is not None and latest_year["passed"] is False
    assert fiscal_2024 is not None and fiscal_2024["passed"] is True


def test_probe_uses_selective_v2_context_instead_of_full_evidence() -> None:
    question = PROBE_QUESTIONS[0]
    case = {
        "question": question,
        "category": "fact_lookup",
        "queries": [{
            "query": {"ticker": "AAPL"},
            "chunks": [
                {
                    "chunk_id": "AAPL_lead",
                    "citation": "lead",
                    "text": "General Apple context.",
                    "score": 3.0,
                },
                {
                    "chunk_id": "AAPL_table",
                    "citation": "table",
                    "text": "Total net sales were 391,035 in 2024.",
                    "score": 10.0,
                },
                {
                    "chunk_id": "AAPL_noise",
                    "citation": "noise",
                    "text": "Unrelated third source.",
                    "score": 2.0,
                },
            ],
        }],
    }

    context = build_probe_contexts({question: case}, [question])[question]

    assert PROBE_CONTEXT_STRATEGY == "selective_packed_v2"
    assert context.count("[Source ") == 2
    assert "391,035" in context
    assert "Unrelated third source" not in context


def test_probe_quality_gate_rejects_safe_fallback_for_answerable_case() -> None:
    context = "[Source 1] MSFT 10-K\nTotal assets were 619,003."

    audit = audit_probe_answer(
        "I could not find sufficient information in the available documents "
        "to answer this question with confidence.",
        context,
    )

    assert audit["answer_audit"]["fallback_answer"] is True
    assert audit["integrity"]["non_fallback"] is False
    assert audit["integrity_passed"] is False


# ---------------------------------------------------------------------------
# Frozen planner-snapshot plan overrides
# ---------------------------------------------------------------------------


def test_override_plan_matches_captured_planner_output() -> None:
    plan = build_override_plan()

    assert plan.question == OVERRIDE_QUESTION
    assert plan.route == "decomposed"
    assert [
        (q.effective_query, q.ticker, q.section)
        for q in plan.queries
    ] == [
        ("Apple total revenue fiscal year 2024", "AAPL", "financial_table"),
        ("Amazon total revenue fiscal year 2024", "AMZN", "financial_table"),
    ]
    assert all(q.query_source == "planner_snapshot" for q in plan.queries)


def test_apply_overrides_replaces_only_target_question() -> None:
    other = RetrievalPlan(
        question="Summarize Apple competition risks",
        category="summary",
        route="direct",
        queries=(
            PlanQuery(
                effective_query="Apple competition risks",
                ticker="AAPL",
                section="risk_factors",
                query_source="original_question",
            ),
        ),
    )
    plans = [other, build_override_plan()]  # target already present once

    replaced, provenance = apply_frozen_plan_overrides(
        plans, selected_questions={other.question, OVERRIDE_QUESTION}
    )

    assert len(replaced) == 2
    target = next(p for p in replaced if p.question == OVERRIDE_QUESTION)
    assert all(q.query_source == "planner_snapshot" for q in target.queries)
    untouched = next(p for p in replaced if p.question == other.question)
    assert untouched is other
    assert set(provenance["plan_overrides"]) == {OVERRIDE_QUESTION}


def test_apply_overrides_allows_category_subset_without_target() -> None:
    from src.evaluation.retrieval_plan import validate_plans_cover

    unrelated = RetrievalPlan(
        question="Unrelated question",
        category="summary",
        route="direct",
        queries=(
            PlanQuery(
                effective_query="q", ticker=None, section=None,
                query_source="original_question",
            ),
        ),
    )

    replaced, provenance = apply_frozen_plan_overrides(
        [unrelated], selected_questions={unrelated.question}
    )

    assert replaced == [unrelated]
    assert provenance == {"plan_overrides": {}}
    # Full-set coverage validation still rejects an incomplete selection.
    with pytest.raises(ValueError, match="Missing fixed retrieval plans"):
        validate_plans_cover(
            [unrelated],
            [EvalTestCase(question=OVERRIDE_QUESTION, category="comparative",
                          ticker=None, section=None, ground_truth="gt")],
        )


def test_apply_overrides_injects_selected_question_without_legacy_record() -> None:
    """After the FY2024 rename no official-artifact record exists under the
    new wording; the code-owned snapshot plan must be injected instead of
    failing Phase 1."""
    unrelated = RetrievalPlan(
        question="Unrelated question",
        category="summary",
        route="direct",
        queries=(
            PlanQuery(
                effective_query="q", ticker=None, section=None,
                query_source="original_question",
            ),
        ),
    )

    replaced, provenance = apply_frozen_plan_overrides(
        [unrelated],
        selected_questions={unrelated.question, OVERRIDE_QUESTION},
    )

    assert [p.question for p in replaced] == [
        unrelated.question, OVERRIDE_QUESTION
    ]
    injected = replaced[-1]
    assert injected is not unrelated
    assert all(q.query_source == "planner_snapshot" for q in injected.queries)
    assert set(provenance["plan_overrides"]) == {OVERRIDE_QUESTION}

    # Injected plan plus the other selected plan exactly cover a test set.
    from src.evaluation.retrieval_plan import validate_plans_cover

    validate_plans_cover(
        replaced,
        [
            EvalTestCase(question=unrelated.question, category="summary",
                         ticker=None, section=None, ground_truth="gt"),
            EvalTestCase(question=OVERRIDE_QUESTION, category="comparative",
                         ticker=None, section=None, ground_truth="gt"),
        ],
    )


def test_planner_provenance_records_model_prompt_and_raw_hashes() -> None:
    provenance = compute_planner_provenance()

    assert provenance["kind"] == "live_planner_snapshot"
    assert provenance["model"] == "openai/gpt-oss-120b"
    assert provenance["max_tokens"] == 700
    assert provenance["prompt_schema_sha256"].startswith("sha256:")
    assert provenance["raw_plan_sha256"].startswith("sha256:")
    # Raw hash is derived from the verbatim captured output.
    assert provenance["raw_plan_sha256"] == canonical_sha256(RAW_PLANNER_OUTPUT)


def test_provenance_snapshot_note_prevents_variance_claims() -> None:
    note = compute_planner_provenance()["variance_note"]

    assert "snapshot" in note
    assert "variance" in note


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


def test_extract_required_numbers_excludes_bare_calendar_years() -> None:
    """A calendar year is period metadata; financial-table chunk bodies
    frequently omit year headers, so requiring them would create false
    retrieval-miss classifications."""
    facts = extract_required_numbers(
        "In fiscal year 2024, Amazon's consolidated net sales ($637,959 "
        "million) were significantly higher than Apple's total net sales "
        "($391,035 million)."
    )

    assert facts == ["391,035", "637,959"]
    assert "2024" not in facts


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


def test_audit_uses_ticker_metadata_for_company_attribution() -> None:
    payload = _case_payload(
        queries=[
            {
                "effective_query": "Apple total revenue",
                "ticker": "AAPL",
                "section": "financial_table",
                "query_source": "planner_snapshot",
                "chunk_ids": ["AAPL_table"],
            },
            {
                "effective_query": "Amazon total revenue",
                "ticker": "AMZN",
                "section": "financial_table",
                "query_source": "planner_snapshot",
                "chunk_ids": ["AMZN_table"],
            },
        ],
        final_chunk_ids=["AAPL_table", "AMZN_table"],
        chunks_by_id={
            "AAPL_table": {
                "chunk_id": "AAPL_table",
                "ticker": "AAPL",
                "text": "Total net sales | 416,161 | 391,035 | 383,285",
            },
            "AMZN_table": {
                "chunk_id": "AMZN_table",
                "ticker": "AMZN",
                "text": "Total net sales | 716,924 | 637,959 | 574,785",
            },
        },
    )
    payload["question"] = OVERRIDE_QUESTION

    report = audit_decomposed_case(
        payload,
        ["Amazon"],
        "Amazon's consolidated net sales are higher than Apple's.",
    )

    assert report["status"] == STATUS_EVIDENCE_OK
    assert report["missing_keywords"] == []


def test_expected_fact_override_catches_vague_ground_truth() -> None:
    """Even with a qualitative ground truth, the override pins the FY2024
    totals so EPS-table noise on the AMZN branch cannot pass the audit."""
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
    payload["question"] = OVERRIDE_QUESTION
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
