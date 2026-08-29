from scripts.diagnostics.comparative_packing_v3 import (
    MIN_COMPARATIVE_TOKEN_REDUCTION_PCT,
    _branch_coverage,
    _source_boundaries_match,
)
from src.evaluation.context_packing import PackedContext, render_packed_blocks


def _entry(chunk_id: str, text: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "citation": f"citation {chunk_id}",
        "text": text,
    }


def test_source_boundary_gate_preserves_internal_blank_lines() -> None:
    kept = [
        _entry("A", "first paragraph\n\nsecond paragraph"),
        _entry("B", "other evidence"),
    ]
    rendered = render_packed_blocks(PackedContext(strategy="test", kept=kept))

    assert _source_boundaries_match(rendered, kept)


def test_source_boundary_gate_rejects_mutated_text() -> None:
    kept = [_entry("A", "exact evidence")]

    assert not _source_boundaries_match(
        "[Source 1] citation A\nmutated evidence", kept
    )


def test_branch_gate_requires_two_when_available() -> None:
    case = {
        "queries": [{
            "query": {"effective_query": "aws", "ticker": "AMZN"},
            "chunks": [_entry("A", "one"), _entry("B", "two"), _entry("C", "three")],
        }]
    }

    failed = _branch_coverage(case, {"A"})
    passed = _branch_coverage(case, {"A", "B"})

    assert not failed[0]["coverage_passed"]
    assert passed[0]["coverage_passed"]
    assert MIN_COMPARATIVE_TOKEN_REDUCTION_PCT == 25.0
