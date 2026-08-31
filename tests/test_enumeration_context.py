from dataclasses import dataclass

from src.generation.enumeration_context import (
    EnumerationBranch,
    enumeration_consensus_profile,
    select_enumeration_chunks,
)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    score: float


def _branch(name: str, *chunks: Chunk) -> EnumerationBranch:
    return EnumerationBranch(name, "TEST", chunks)


def test_strong_consensus_keeps_dominant_and_early_repeated_support() -> None:
    dominant = Chunk("dominant", 3.0)
    support = Chunk("support", 2.0)
    branches = [
        _branch("one", dominant),
        _branch("two", dominant),
        _branch("three", dominant),
        _branch("four", dominant, support),
        _branch("five", dominant, support, Chunk("tail", 1.0)),
    ]

    profile = enumeration_consensus_profile(branches)
    selected = select_enumeration_chunks(branches)

    assert profile.eligible
    assert profile.dominant_chunk_id == "dominant"
    assert profile.dominant_rank_one_share == 1.0
    assert [chunk.chunk_id for chunk in selected] == ["dominant", "support"]


def test_rank_two_consensus_keeps_dissenting_branch_leader() -> None:
    dominant = Chunk("dominant", 3.0)
    dissent = Chunk("dissent", 4.0)
    branches = [
        _branch("one", dominant),
        _branch("two", dominant),
        _branch("three", dominant),
        _branch("four", dominant),
        _branch("five", dissent, dominant, Chunk("tail", 1.0)),
    ]

    profile = enumeration_consensus_profile(branches)
    selected = select_enumeration_chunks(branches)

    assert profile.eligible
    assert profile.dominant_rank_one_share == 0.8
    assert profile.dominant_max_rank == 2
    assert [chunk.chunk_id for chunk in selected] == ["dominant", "dissent"]


def test_no_consensus_returns_full_deduplicated_evidence() -> None:
    chunks = [Chunk(f"c{index}", float(index)) for index in range(5)]
    branches = [
        _branch(str(index), chunk) for index, chunk in enumerate(chunks)
    ]

    profile = enumeration_consensus_profile(branches)
    selected = select_enumeration_chunks(branches)

    assert not profile.eligible
    assert selected == chunks


def test_structured_hit_is_never_removed() -> None:
    dominant = Chunk("dominant", 3.0)
    structured = Chunk("structured", 10.0)
    branches = [
        _branch("one", dominant, structured),
        _branch("two", dominant),
        _branch("three", dominant),
        _branch("four", dominant),
    ]

    selected = select_enumeration_chunks(branches)

    assert [chunk.chunk_id for chunk in selected] == ["dominant", "structured"]
