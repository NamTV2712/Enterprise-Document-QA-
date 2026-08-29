from scripts.diagnostics.comparative_packing_v4 import (
    AWS_QUESTION,
    CYBER_QUESTION,
    INTERNATIONAL_QUESTION,
    MIN_COMPARATIVE_TOKEN_REDUCTION_PCT,
    REQUIRED_DROPPED_CHUNKS,
    REQUIRED_KEPT_CHUNKS,
    _branch_rows,
    _known_finding_gate,
)


def _chunk(chunk_id: str, text: str) -> dict:
    return {"chunk_id": chunk_id, "text": text}


def test_branch_contract_is_scoped_to_the_matching_ticker() -> None:
    case = {
        "question": AWS_QUESTION,
        "queries": [
            {
                "query": {"effective_query": "Amazon AWS growth", "ticker": "AMZN"},
                "chunks": [_chunk("A", "AWS 107,556 128,725")],
            },
            {
                "query": {
                    "effective_query": "Microsoft cloud business growth",
                    "ticker": "MSFT",
                },
                "chunks": [
                    _chunk(
                        "M",
                        "Microsoft Cloud revenue increased 23% to $168.9 billion.",
                    )
                ],
            },
        ],
    }

    rows = _branch_rows(case, {"A", "M"})

    assert all(row["contract_passed"] for row in rows)
    assert rows[0]["required_terms"] == ["107,556", "128,725"]
    assert rows[1]["required_terms"] == [
        "Microsoft Cloud revenue increased",
        "168.9 billion",
    ]


def test_known_finding_gate_requires_pins_and_exclusions() -> None:
    cyber_required = REQUIRED_KEPT_CHUNKS[CYBER_QUESTION]
    international_dropped = REQUIRED_DROPPED_CHUNKS[INTERNATIONAL_QUESTION]

    assert _known_finding_gate(CYBER_QUESTION, set())["kept_passed"] is False
    assert _known_finding_gate(CYBER_QUESTION, cyber_required)["kept_passed"]
    assert _known_finding_gate(
        INTERNATIONAL_QUESTION, set()
    )["dropped_passed"]
    assert not _known_finding_gate(
        INTERNATIONAL_QUESTION, international_dropped
    )["dropped_passed"]


def test_v4_token_gate_is_preregistered_at_45_percent() -> None:
    assert MIN_COMPARATIVE_TOKEN_REDUCTION_PCT == 45.0
