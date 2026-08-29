from types import SimpleNamespace

from src.generation.comparative_context import (
    ComparativeBranch,
    select_comparative_chunks,
)


def _chunk(chunk_id: str, text: str, score: float) -> dict:
    return {"chunk_id": chunk_id, "text": text, "score": score}


def test_exact_filing_hint_keeps_aggregate_microsoft_cloud_donor() -> None:
    chunks = [
        _chunk(
            "MSFT_0",
            "Microsoft Cloud gross margin and Microsoft 365 cloud growth metrics.",
            6.8,
        ),
        _chunk(
            "MSFT_1",
            "Productivity and Business Processes revenue increased.",
            6.0,
        ),
        _chunk(
            "MSFT_2",
            "Microsoft Cloud revenue increased 23% to $168.9 billion.",
            5.5,
        ),
    ]

    selected = select_comparative_chunks([
        ComparativeBranch("Microsoft cloud business growth", "MSFT", chunks)
    ])

    assert [chunk["chunk_id"] for chunk in selected] == ["MSFT_0", "MSFT_2"]


def test_missing_cybersecurity_intent_keeps_one_intent_donor() -> None:
    chunks = [
        _chunk("AMZN_0", "Consumer protection and regulatory risk.", 3.0),
        _chunk(
            "AMZN_1",
            "Data Loss and Other Security Incidents are cybersecurity risks.",
            1.0,
        ),
        _chunk("AMZN_2", "General international operations risk.", 0.5),
    ]

    selected = select_comparative_chunks([
        ComparativeBranch("Amazon cybersecurity risk disclosures", "AMZN", chunks)
    ])

    assert [chunk["chunk_id"] for chunk in selected] == ["AMZN_0", "AMZN_1"]


def test_complete_intent_does_not_keep_blind_second_chunk() -> None:
    chunks = [
        _chunk(
            "AAPL_0",
            "International operations expose Apple to regulatory risk.",
            3.0,
        ),
        _chunk("AAPL_1", "General product competition.", 2.0),
    ]

    selected = select_comparative_chunks([
        ComparativeBranch("Apple international operations risk", "AAPL", chunks)
    ])

    assert [chunk["chunk_id"] for chunk in selected] == ["AAPL_0"]


def test_aws_leader_is_not_replaced_or_augmented_by_an_oracle_fact() -> None:
    chunks = [
        _chunk(
            "AMZN_0",
            "AWS net sales were $107,556 in 2024 and $128,725 in 2025.",
            6.8,
        ),
        _chunk("AMZN_1", "AWS operating income increased.", 5.0),
    ]

    selected = select_comparative_chunks([
        ComparativeBranch("Amazon AWS growth", "AMZN", chunks)
    ])

    assert [chunk["chunk_id"] for chunk in selected] == ["AMZN_0"]


def test_runtime_object_adapter_matches_dict_adapter_and_preserves_order() -> None:
    dict_chunks = [
        _chunk("A_0", "Cloud services growth.", 3.0),
        _chunk("A_1", "Cloud services revenue increased.", 2.0),
    ]
    dict_selected = select_comparative_chunks([
        ComparativeBranch(
            "Apple cloud services revenue growth", "AAPL", dict_chunks
        )
    ])
    object_chunks = [SimpleNamespace(**chunk) for chunk in dict_chunks]
    object_selected = select_comparative_chunks([
        ComparativeBranch(
            "Apple cloud services revenue growth", "AAPL", object_chunks
        )
    ])

    assert [chunk["chunk_id"] for chunk in dict_selected] == ["A_0", "A_1"]
    assert [chunk.chunk_id for chunk in object_selected] == ["A_0", "A_1"]
    assert [chunk["chunk_id"] for chunk in dict_chunks] == ["A_0", "A_1"]
