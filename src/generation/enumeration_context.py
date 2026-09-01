"""Oracle-free branch-consensus selection for enumeration synthesis.

Enumeration decomposition can produce several focused queries that repeatedly
retrieve the same broad, self-contained filing chunk.  This selector collapses
such a plan only when one chunk is present in the top two of every branch and
is ranked first by at least 80% of branches.  Plans without that strong
consensus keep their complete deduplicated evidence.

The implementation consumes only ranked branches and chunk metadata.  It has
no access to evaluation labels, expected answers, or required keywords.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


ENUMERATION_CONSENSUS_FINGERPRINT = (
    "sha256:"
    "a8f540b80de0db5e9a2c8838c947337c68145dc19fa55bcd0cf86cc8f2d7c0f2"
)
MIN_BRANCHES = 4
CONSENSUS_RANK_WINDOW = 2
MIN_RANK_ONE_SHARE = 0.8
SUPPORT_MIN_BRANCHES = 2
STRUCTURED_PROMOTION_SCORE = 10.0


@dataclass(frozen=True)
class EnumerationBranch:
    """One focused enumeration query and its already-ranked chunks."""

    query: str
    ticker: str | None
    chunks: Sequence[Any]


@dataclass(frozen=True)
class EnumerationConsensusProfile:
    """Deterministic explanation of a branch-consensus decision."""

    eligible: bool
    branch_count: int
    dominant_chunk_id: str | None
    dominant_rank_one_branches: int
    dominant_rank_one_share: float
    dominant_max_rank: int | None
    support_chunk_ids: tuple[str, ...]


def _field(entry: Any, name: str, default: Any = None) -> Any:
    if isinstance(entry, dict):
        return entry.get(name, default)
    return getattr(entry, name, default)


def _chunk_id(entry: Any) -> str | None:
    value = _field(entry, "chunk_id")
    return value if isinstance(value, str) and value else None


def _unique_branch(branch: EnumerationBranch) -> list[Any]:
    selected: list[Any] = []
    seen: set[str] = set()
    for entry in branch.chunks:
        chunk_id = _chunk_id(entry)
        if chunk_id is None or chunk_id in seen:
            continue
        seen.add(chunk_id)
        selected.append(entry)
    return selected


def _all_entries(branches: Sequence[EnumerationBranch]) -> list[Any]:
    selected: list[Any] = []
    seen: set[str] = set()
    for branch in branches:
        for entry in _unique_branch(branch):
            chunk_id = _chunk_id(entry)
            if chunk_id is None or chunk_id in seen:
                continue
            seen.add(chunk_id)
            selected.append(entry)
    return selected


def enumeration_consensus_profile(
    branches: Sequence[EnumerationBranch],
) -> EnumerationConsensusProfile:
    """Return the label-free consensus profile for ranked branches."""
    ranked = [_unique_branch(branch) for branch in branches]
    branch_count = len(ranked)
    if branch_count < MIN_BRANCHES or any(not branch for branch in ranked):
        return EnumerationConsensusProfile(
            eligible=False,
            branch_count=branch_count,
            dominant_chunk_id=None,
            dominant_rank_one_branches=0,
            dominant_rank_one_share=0.0,
            dominant_max_rank=None,
            support_chunk_ids=(),
        )

    ranks: dict[str, dict[int, int]] = {}
    first_seen: dict[str, int] = {}
    encounter = 0
    for branch_index, branch in enumerate(ranked):
        for rank, entry in enumerate(branch, start=1):
            chunk_id = _chunk_id(entry)
            if chunk_id is None:
                continue
            first_seen.setdefault(chunk_id, encounter)
            encounter += 1
            ranks.setdefault(chunk_id, {})[branch_index] = rank

    candidates: list[tuple[int, int, int, str]] = []
    for chunk_id, observed in ranks.items():
        rank_values = list(observed.values())
        rank_one_count = sum(rank == 1 for rank in rank_values)
        if (
            len(observed) == branch_count
            and max(rank_values) <= CONSENSUS_RANK_WINDOW
            and rank_one_count / branch_count >= MIN_RANK_ONE_SHARE
        ):
            candidates.append(
                (rank_one_count, -sum(rank_values), -first_seen[chunk_id], chunk_id)
            )

    if not candidates:
        return EnumerationConsensusProfile(
            eligible=False,
            branch_count=branch_count,
            dominant_chunk_id=None,
            dominant_rank_one_branches=0,
            dominant_rank_one_share=0.0,
            dominant_max_rank=None,
            support_chunk_ids=(),
        )

    _, _, _, dominant = max(candidates)
    dominant_ranks = ranks[dominant]
    support_ids = {dominant}

    # Preserve a branch's dissenting leader only when the other branches do
    # not independently demote that same chunk.  A branch-specific leader
    # that also appears deep in another branch is usually retrieval noise, not
    # corroborating evidence; keeping it would lower context precision while
    # adding no coverage guarantee.
    for branch in ranked:
        leader_id = _chunk_id(branch[0])
        observed_ranks = ranks.get(leader_id, {}) if leader_id else {}
        if (
            leader_id
            and leader_id != dominant
            and max(observed_ranks.values(), default=1)
            <= CONSENSUS_RANK_WINDOW
        ):
            support_ids.add(leader_id)

    # Keep early corroborating evidence only when at least two independent
    # branches retrieved it near the top.  Counting only the minimum rank
    # would admit a chunk that is rank 1 in one branch but rank 5 elsewhere.
    for chunk_id, observed in ranks.items():
        if (
            sum(
                rank <= CONSENSUS_RANK_WINDOW
                for rank in observed.values()
            )
            >= SUPPORT_MIN_BRANCHES
        ):
            support_ids.add(chunk_id)

    # Exact structured promotions remain mandatory regardless of consensus.
    for entry in _all_entries(branches):
        score = _field(entry, "score")
        chunk_id = _chunk_id(entry)
        if (
            chunk_id
            and isinstance(score, (int, float))
            and score >= STRUCTURED_PROMOTION_SCORE
        ):
            support_ids.add(chunk_id)

    ordered_support = tuple(
        chunk_id
        for entry in _all_entries(branches)
        if (chunk_id := _chunk_id(entry)) in support_ids
    )
    rank_one_count = sum(rank == 1 for rank in dominant_ranks.values())
    return EnumerationConsensusProfile(
        eligible=True,
        branch_count=branch_count,
        dominant_chunk_id=dominant,
        dominant_rank_one_branches=rank_one_count,
        dominant_rank_one_share=round(rank_one_count / branch_count, 4),
        dominant_max_rank=max(dominant_ranks.values()),
        support_chunk_ids=ordered_support,
    )


def select_enumeration_chunks(
    branches: Sequence[EnumerationBranch],
) -> list[Any]:
    """Select consensus evidence or return full deduplicated evidence."""
    entries = _all_entries(branches)
    profile = enumeration_consensus_profile(branches)
    if not profile.eligible:
        return entries
    kept = set(profile.support_chunk_ids)
    return [entry for entry in entries if _chunk_id(entry) in kept]
