"""Route-aware context packing over frozen Phase 1 evidence.

The official N=30 run showed perfect recall with low context precision:
correct evidence is retrieved alongside extra chunks the judge considers
irrelevant. This module selects a SUBSET of each case's frozen evidence
before generation instead of changing retrieval.

Packing is deterministic and coverage-preserving. Mandatory selections:

M1. The globally first evidence chunk (primary context).
M2. Every structured-lookup promotion (score >= 10.0).
M3. For comparative plans, the top-scored chunk per expected ticker so
    no company loses its evidence.
M4. Enough additional chunks that every required keyword occurs in some
    kept text; if no chunk contains a keyword, nothing can restore it
    (retrieval-level miss) and packing stays honest about that.

Comparative v4 replaces blind two-chunk branch breadth with one leading chunk
plus only branch-scoped fact donors and query-intent donors that add missing
evidence. Comparative v5 moves that decision into the generic selector shared
with production, removing evaluation-only fact labels from the selection path.
Historical strategy behavior remains unchanged.

Summary/enumeration cases additionally fill up to a small fixed target
by descending score because their answers synthesize broad topic
coverage rather than isolated facts. Out-of-corpus cases keep only M1;
their correct behavior is abstention and their context precision is
zero by design either way.

Selection NEVER changes source order, citations, or chunk text, and it
never adds evidence that full evidence would not contain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.evaluation.generation_checkpoint import build_evidence_context
from src.generation.period_value_completeness import render_chunk_evidence
from src.generation.enumeration_context import (
    EnumerationBranch,
    select_enumeration_chunks,
)
from src.generation.fact_context import (
    FACT_CONTEXT_STRATEGY,
    selected_fact_entries,
)
from src.generation.comparative_context import (
    ComparativeBranch,
    select_comparative_chunks_intent_first,
    select_comparative_chunks,
)
from src.evaluation.evidence_contracts import (
    branch_evidence_terms,
    evidence_terms,
)

CONTEXT_STRATEGY_FULL_EVIDENCE = "full_evidence_v1"
CONTEXT_STRATEGY_ROUTE_AWARE = "route_aware_v2"
# Packs only the categories whose A/B paired evidence showed faithfulness-
# neutral, precision-positive behavior (fact_lookup, multi_hop, summary).
# Enumeration/comparative-topical/out-of-corpus stay full-evidence because
# packed-all regressed their faithfulness in the measured arms.
CONTEXT_STRATEGY_SELECTIVE = "selective_packed_v1"
CONTEXT_STRATEGY_COMPARATIVE_V3 = "comparative_packed_v3"
CONTEXT_STRATEGY_COMPARATIVE_V4 = "comparative_intent_packed_v4"
CONTEXT_STRATEGY_COMPARATIVE_V5 = "comparative_oracle_free_v5"
CONTEXT_STRATEGY_COMPARATIVE_V6 = "comparative_intent_first_v6"
# Provider-free summary counterfactual.  It is intentionally not part of the
# admitted default until a provider-backed sentinel validates the changed
# context shape.
CONTEXT_STRATEGY_ROUTE_AWARE_V3 = "route_aware_v3_intent"
# Provider-free summary successor. It retains direct, early query anchors
# after intent-first packing has selected the broadest coverage. This remains
# a candidate policy until its bounded provider sentinel is complete.
CONTEXT_STRATEGY_ROUTE_AWARE_V4 = "route_aware_v4_anchor"
# Composite successor to selective_packed_v1. It preserves the already
# admitted category policy while replacing only comparative contexts with v5.
CONTEXT_STRATEGY_SELECTIVE_V2 = "selective_packed_v2"
CONTEXT_STRATEGY_SELECTIVE_V3 = "selective_packed_v3_candidate"
CONTEXT_STRATEGY_SELECTIVE_V4 = "selective_packed_v4_candidate"
CONTEXT_STRATEGY_ENUMERATION_V1 = "enumeration_consensus_v1"
CONTEXT_STRATEGY_SELECTIVE_V5 = "selective_packed_v5_enumeration_candidate"
CONTEXT_STRATEGY_SELECTIVE_V6 = "selective_packed_v6_fact_candidate"
SELECTIVE_PACKED_CATEGORIES = {"fact_lookup", "multi_hop", "summary"}
COMPARATIVE_BRANCH_TARGET = 2

_INTENT_STOPWORDS = {
    "amazon",
    "apple",
    "approach",
    "business",
    "company",
    "compare",
    "depends",
    "disclosures",
    "fiscal",
    "from",
    "higher",
    "microsoft",
    "more",
    "segment",
    "terms",
    "their",
    "total",
    "which",
    "with",
    "year",
}
_INTENT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "cloud": ("cloud", "azure", "aws"),
    "cybersecurity": (
        "cybersecurity",
        "cyber",
        "security incident",
        "data loss",
        "unauthorized access",
    ),
    "growth": ("growth", "increase", "increased", "grew", "year-over-year"),
    "international": ("international", "foreign", "global"),
    "operations": ("operations", "operational"),
    "revenue": ("revenue", "sales", "net sales"),
    "risk": ("risk", "risks", "threat"),
    "services": ("services", "service"),
    "subscription": ("subscription", "subscriptions"),
}

_SUMMARY_INTENT_STOPWORDS = _INTENT_STOPWORDS | {
    "about",
    "and",
    "does",
    "face",
    "factors",
    "from",
    "how",
    "in",
    "its",
    "key",
    "mention",
    "of",
    "related",
    "risks",
    "say",
    "summarize",
    "the",
    "to",
    "what",
}

# Structured lookup promotes exact table rows/auditor signatures to
# exactly 10.0 before hybrid scoring; anything at that ceiling is an
# exact canonical-row hit.
STRUCTURED_PROMOTION_SCORE = 10.0

# Post-mandatory fill targets by category (total kept chunks).
_FILL_TARGETS = {
    "summary": 4,
    "enumeration": 4,
}


def _compact(text: str) -> str:
    return "".join(text.split()).lower()


def _chunk_ticker(entry: dict) -> str:
    ticker = entry.get("ticker")
    if ticker:
        return ticker
    return (entry.get("chunk_id") or "").split("_", 1)[0]


def _branch_entries(query_entry: dict) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()
    for entry in query_entry.get("chunks", []):
        chunk_id = entry.get("chunk_id")
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        entries.append(entry)
    return entries


def _intent_groups(query_entry: dict) -> tuple[tuple[str, ...], ...]:
    query = query_entry.get("query", {})
    text = query.get("effective_query") or query.get("retrieval_query") or ""
    tokens = re.findall(r"[a-z0-9]+", text.casefold())
    groups: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for token in tokens:
        if len(token) < 4 or token in _INTENT_STOPWORDS:
            continue
        group = _INTENT_SYNONYMS.get(token, (token,))
        if group in seen:
            continue
        seen.add(group)
        groups.append(group)
    return tuple(groups)


def _matched_intent_groups(
    entry: dict, groups: tuple[tuple[str, ...], ...]
) -> frozenset[int]:
    text = _compact(entry.get("text", ""))
    return frozenset(
        index
        for index, alternatives in enumerate(groups)
        if any(_compact(term) in text for term in alternatives)
    )


def _best_intent_donor(
    branch: list[dict],
    groups: tuple[tuple[str, ...], ...],
    covered: frozenset[int],
) -> dict | None:
    missing = set(range(len(groups))) - set(covered)
    if not missing:
        return None
    ranked: list[tuple[int, int, float, int, dict]] = []
    for index, entry in enumerate(branch):
        matched = _matched_intent_groups(entry, groups) & missing
        if not matched:
            continue
        text = _compact(entry.get("text", ""))
        occurrences = sum(
            max(text.count(_compact(term)) for term in groups[group_index])
            for group_index in matched
        )
        score = entry.get("score")
        ranked.append(
            (
                len(matched),
                occurrences,
                float(score) if isinstance(score, (int, float)) else float("-inf"),
                -index,
                entry,
            )
        )
    if not ranked:
        return None
    return max(ranked, key=lambda item: item[:-1])[-1]


def _summary_intent_groups(case_payload: dict) -> tuple[tuple[str, ...], ...]:
    """Return meaningful intent groups across all summary subqueries."""
    groups: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for query_entry in case_payload.get("queries", []):
        query = query_entry.get("query", {})
        text = (
            query.get("effective_query")
            or query.get("retrieval_query")
            or ""
        )
        for token in re.findall(r"[a-z0-9]+", text.casefold()):
            if len(token) < 4 or token in _SUMMARY_INTENT_STOPWORDS:
                continue
            group = _INTENT_SYNONYMS.get(token, (token,))
            if group in seen:
                continue
            seen.add(group)
            groups.append(group)
    return tuple(groups)


def _summary_intent_matches(
    entry: dict, groups: tuple[tuple[str, ...], ...]
) -> frozenset[int]:
    text = _compact(entry.get("text", ""))
    return frozenset(
        index
        for index, alternatives in enumerate(groups)
        if any(_compact(term) in text for term in alternatives)
    )


def _pack_summary_intent_first(
    case_payload: dict,
    required_keywords: list[str] | None,
) -> PackedContext:
    """Pack summary evidence by marginal query-intent coverage.

    This is a bounded counterfactual for decomposed summaries.  It selects
    from the frozen retrieved set only, preserves structured hits and required
    keyword donors, and avoids score-only filler once a relevant candidate is
    available.  The fixed target remains four chunks to keep the context
    budget comparable with route_aware_v2.
    """
    entries = collect_entries(case_payload)
    result = PackedContext(strategy=CONTEXT_STRATEGY_ROUTE_AWARE_V3)
    if not entries:
        return result

    kept: list[dict] = []
    kept_ids: set[str] = set()

    def add(entry: dict | None) -> bool:
        if entry is None:
            return False
        chunk_id = entry.get("chunk_id")
        if chunk_id in kept_ids:
            return False
        kept.append(entry)
        kept_ids.add(chunk_id)
        return True

    # Structured rows remain mandatory, independent of lexical intent.
    for entry in entries:
        score = entry.get("score")
        if isinstance(score, (int, float)) and score >= STRUCTURED_PROMOTION_SCORE:
            add(entry)

    groups = _summary_intent_groups(case_payload)
    covered_groups: set[int] = set()
    if groups:
        ranked = list(enumerate(entries))
        while len(kept) < _FILL_TARGETS["summary"]:
            candidates: list[tuple[int, int, float, int, dict]] = []
            for index, entry in ranked:
                if entry.get("chunk_id") in kept_ids:
                    continue
                matched = _summary_intent_matches(entry, groups)
                new_groups = matched - covered_groups
                if not matched:
                    continue
                score = entry.get("score")
                numeric_score = (
                    float(score) if isinstance(score, (int, float))
                    else float("-inf")
                )
                candidates.append(
                    (
                        len(new_groups),
                        len(matched),
                        numeric_score,
                        -index,
                        entry,
                    )
                )
            if not candidates:
                break
            selected = max(candidates, key=lambda item: item[:-1])[-1]
            add(selected)
            covered_groups.update(_summary_intent_matches(selected, groups))

    # If the query has no usable intent signal, retain the historical primary
    # rather than inventing a new selection rule.
    if not kept:
        add(entries[0])

    # Required-keyword coverage is still a hard packing contract.
    for keyword in tuple(required_keywords or ()):
        needle = _compact(keyword)
        if not needle or any(needle in _compact(e.get("text", "")) for e in kept):
            continue
        donor = next(
            (entry for entry in entries if needle in _compact(entry.get("text", ""))),
            None,
        )
        if donor is None:
            result.uncovered_keywords.append(keyword)
        else:
            add(donor)

    result.kept = [
        entry for entry in entries if entry.get("chunk_id") in kept_ids
    ]
    result.dropped = [
        entry for entry in entries if entry.get("chunk_id") not in kept_ids
    ]
    return result


_SUMMARY_ANCHOR_VARIANTS: dict[str, tuple[str, ...]] = {
    "component": ("component", "components"),
    "compliance": ("compliance", "comply", "compliant"),
    "control": ("control", "controls"),
    "currency": ("currency", "currencies", "exchange"),
    "geopolitical": ("geopolitical", "geopolitics"),
    "growth": ("growth", "grew", "increase", "increased"),
    "international": ("international", "internationally", "foreign", "global"),
    "manufacturing": ("manufacturing", "manufacture", "manufactured"),
    "operations": ("operations", "operational"),
    "quality": ("quality", "defect", "defects"),
    "regulatory": ("regulatory", "regulation", "regulations"),
    "services": ("services", "service"),
    "sourcing": ("sourcing", "source", "sources", "supplier", "suppliers"),
    "tariff": ("tariff", "tariffs", "trade"),
}

_SUMMARY_ANCHOR_PREFIX_CHARS = 750
_SUMMARY_ANCHOR_CORE_PREFIX_CHARS = 250


def _summary_anchor_groups(query: str) -> tuple[tuple[str, ...], ...]:
    """Return query signals suitable for identifying a direct evidence anchor."""
    groups: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for token in re.findall(r"[a-z0-9]+", query.casefold()):
        if len(token) < 4 or token in _SUMMARY_INTENT_STOPWORDS:
            continue
        alternatives = _SUMMARY_ANCHOR_VARIANTS.get(token, (token,))
        group = tuple(dict.fromkeys(alternatives))
        if group in seen:
            continue
        seen.add(group)
        groups.append(group)
    return tuple(groups)


def _summary_anchor_profile(
    entry: dict,
    query: str,
) -> tuple[int, int, int, int, float, int]:
    """Score how directly a chunk answers one summary subquery.

    The profile rewards distinct query signals appearing near the beginning
    of the chunk. Retrieval score is only a late tie-breaker; this prevents a
    high-scoring generic passage from displacing a lower-scoring passage that
    opens with the requested fact.
    """
    text = " ".join(str(entry.get("text", "")).casefold().split())
    groups = _summary_anchor_groups(query)
    positions: list[int] = []
    for alternatives in groups:
        hits = [text.find(term.casefold()) for term in alternatives]
        hits = [position for position in hits if position >= 0]
        if hits:
            positions.append(min(hits))
    early = sum(position < _SUMMARY_ANCHOR_PREFIX_CHARS for position in positions)
    core = sum(
        position < _SUMMARY_ANCHOR_CORE_PREFIX_CHARS for position in positions
    )
    very_early = sum(position < 150 for position in positions)
    earliest = min(positions) if positions else 10**9
    score = entry.get("score")
    numeric_score = float(score) if isinstance(score, (int, float)) else float("-inf")
    return (core, early, len(positions), very_early, numeric_score, -earliest)


def _summary_anchor_strength(
    entry: dict,
    query: str,
) -> tuple[int, int, int, int, float, int]:
    """Return the sortable profile used for anchor admission."""
    profile = _summary_anchor_profile(entry, query)
    return profile


def _pack_summary_with_direct_anchors(
    case_payload: dict,
    required_keywords: list[str] | None,
) -> PackedContext:
    """Keep early direct anchors while retaining v3 intent coverage.

    The v3 selector can prefer a broad, high-scoring passage even when a
    lower-ranked passage starts with the exact fact requested by one of the
    decomposed summary queries. A strong direct anchor may replace only a
    non-mandatory chunk whose removal does not reduce the union of meaningful
    intent coverage. The globally first chunk, structured hits, and required
    keyword donors remain protected.
    """
    base = _pack_summary_intent_first(case_payload, required_keywords)
    entries = collect_entries(case_payload)
    result = PackedContext(strategy=CONTEXT_STRATEGY_ROUTE_AWARE_V4)
    if not entries:
        return result

    target = _FILL_TARGETS["summary"]
    kept_ids = set(base.kept_ids)
    entry_by_id = {entry.get("chunk_id"): entry for entry in entries}

    protected_ids: set[str] = {entries[0].get("chunk_id")}
    for entry in entries:
        score = entry.get("score")
        if isinstance(score, (int, float)) and score >= STRUCTURED_PROMOTION_SCORE:
            protected_ids.add(entry.get("chunk_id"))
    for keyword in tuple(required_keywords or ()):
        needle = _compact(keyword)
        if not needle:
            continue
        donors = [
            entry
            for entry in entries
            if needle in _compact(entry.get("text", ""))
        ]
        donor = max(
            enumerate(donors),
            key=lambda pair: (
                -_compact(pair[1].get("text", "")).find(needle),
                float(pair[1].get("score"))
                if isinstance(pair[1].get("score"), (int, float))
                else float("-inf"),
                -pair[0],
            ),
        )[1] if donors else None
        if donor is not None:
            protected_ids.add(donor.get("chunk_id"))

    anchors: dict[str, tuple[int, int, int, int, float, int]] = {}
    for query_entry in case_payload.get("queries", []):
        query = query_entry.get("query", {})
        query_text = (
            query.get("effective_query")
            or query.get("retrieval_query")
            or ""
        )
        groups = _summary_anchor_groups(query_text)
        if not groups:
            continue
        ranked: list[tuple[tuple[int, int, int, int, float, int], int, dict]] = []
        for index, entry in enumerate(query_entry.get("chunks", [])):
            profile = _summary_anchor_profile(entry, query_text)
            # A direct anchor needs either two early signals or one very early
            # signal plus another signal somewhere in the chunk. This avoids
            # reintroducing score-only filler.
            if not (
                (profile[0] >= 2)
                or (profile[3] >= 1 and profile[2] >= 2)
            ):
                continue
            ranked.append((profile, -index, entry))
        if not ranked:
            continue
        profile, _, anchor = max(ranked, key=lambda item: (item[0], item[1]))
        chunk_id = anchor.get("chunk_id")
        if chunk_id is not None:
            previous = anchors.get(chunk_id)
            if previous is None or _summary_anchor_strength(anchor, query_text) > previous:
                anchors[chunk_id] = _summary_anchor_strength(anchor, query_text)

    # A currently kept chunk with a genuinely direct opening is itself a
    # mandatory anchor. Generic passages that happen to contain a query word
    # deep in the chunk remain replaceable.
    for chunk_id, strength in anchors.items():
        if chunk_id in kept_ids and strength[0] >= 1:
            protected_ids.add(chunk_id)

    def coverage(ids: set[str]) -> set[int]:
        groups = _summary_intent_groups(case_payload)
        covered: set[int] = set()
        for chunk_id in ids:
            entry = entry_by_id.get(chunk_id)
            if entry is not None:
                covered.update(_summary_intent_matches(entry, groups))
        return covered

    for anchor_id, _ in sorted(
        anchors.items(), key=lambda item: item[1], reverse=True
    ):
        if anchor_id in kept_ids or anchor_id not in entry_by_id:
            continue
        anchor_entry = entry_by_id[anchor_id]
        if len(kept_ids) < target:
            kept_ids.add(anchor_id)
            continue

        removable = [
            chunk_id
            for chunk_id in kept_ids
            if chunk_id not in protected_ids
        ]
        if not removable:
            continue
        victim = min(
            removable,
            key=lambda chunk_id: (
                len(
                    coverage(kept_ids)
                    - coverage((kept_ids - {chunk_id}) | {anchor_id})
                ),
                float(entry_by_id[chunk_id].get("score"))
                if isinstance(entry_by_id[chunk_id].get("score"), (int, float))
                else float("-inf"),
                -entries.index(entry_by_id[chunk_id]),
            ),
        )
        kept_ids.remove(victim)
        kept_ids.add(anchor_id)

    result.kept = [entry for entry in entries if entry.get("chunk_id") in kept_ids]
    result.dropped = [
        entry for entry in entries if entry.get("chunk_id") not in kept_ids
    ]
    result.uncovered_keywords = list(base.uncovered_keywords)
    return result


def collect_entries(case_payload: dict) -> list[dict]:
    """Deduplicated evidence entries in deterministic source order."""
    entries: list[dict] = []
    seen: set[str] = set()
    for query_entry in case_payload.get("queries", []):
        for chunk in query_entry.get("chunks", []):
            chunk_id = chunk.get("chunk_id")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            entries.append(chunk)
    return entries


def effective_case_context_strategy(strategy: str, category: str) -> str:
    """Resolve a named Phase 2 policy to one concrete per-case strategy."""
    if strategy == CONTEXT_STRATEGY_SELECTIVE:
        if category in SELECTIVE_PACKED_CATEGORIES:
            return CONTEXT_STRATEGY_ROUTE_AWARE
        return CONTEXT_STRATEGY_FULL_EVIDENCE
    if strategy == CONTEXT_STRATEGY_SELECTIVE_V2:
        if category in SELECTIVE_PACKED_CATEGORIES:
            return CONTEXT_STRATEGY_ROUTE_AWARE
        if category == "comparative":
            return CONTEXT_STRATEGY_COMPARATIVE_V5
        return CONTEXT_STRATEGY_FULL_EVIDENCE
    if strategy == CONTEXT_STRATEGY_SELECTIVE_V3:
        if category in {"fact_lookup", "multi_hop"}:
            return CONTEXT_STRATEGY_ROUTE_AWARE
        if category == "summary":
            return CONTEXT_STRATEGY_ROUTE_AWARE_V3
        if category == "comparative":
            return CONTEXT_STRATEGY_COMPARATIVE_V6
        return CONTEXT_STRATEGY_FULL_EVIDENCE
    if strategy == CONTEXT_STRATEGY_SELECTIVE_V4:
        if category in {"fact_lookup", "multi_hop"}:
            return CONTEXT_STRATEGY_ROUTE_AWARE
        if category == "summary":
            return CONTEXT_STRATEGY_ROUTE_AWARE_V4
        if category == "comparative":
            return CONTEXT_STRATEGY_COMPARATIVE_V6
        return CONTEXT_STRATEGY_FULL_EVIDENCE
    if strategy == CONTEXT_STRATEGY_SELECTIVE_V5:
        if category in SELECTIVE_PACKED_CATEGORIES:
            return CONTEXT_STRATEGY_ROUTE_AWARE
        if category == "comparative":
            return CONTEXT_STRATEGY_COMPARATIVE_V5
        if category == "enumeration":
            return CONTEXT_STRATEGY_ENUMERATION_V1
        return CONTEXT_STRATEGY_FULL_EVIDENCE
    if strategy == CONTEXT_STRATEGY_SELECTIVE_V6:
        if category == "fact_lookup":
            return FACT_CONTEXT_STRATEGY
        return effective_case_context_strategy(
            CONTEXT_STRATEGY_SELECTIVE_V5, category
        )
    return strategy


@dataclass
class PackedContext:
    """Selected subset plus audit facts about the packing decision."""

    strategy: str
    kept: list[dict] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)
    uncovered_keywords: list[str] = field(default_factory=list)

    @property
    def kept_ids(self) -> list[str]:
        return [entry.get("chunk_id") for entry in self.kept]


def pack_case_context(
    case_payload: dict,
    *,
    required_keywords: list[str] | None = None,
    strategy: str = CONTEXT_STRATEGY_ROUTE_AWARE,
) -> PackedContext:
    """Select the evidence subset for one case under the given strategy."""
    strategy = effective_case_context_strategy(
        strategy, case_payload.get("category", "")
    )
    entries = collect_entries(case_payload)
    result = PackedContext(strategy=strategy)
    if strategy == CONTEXT_STRATEGY_FULL_EVIDENCE:
        result.kept = list(entries)
        return result

    category = case_payload.get("category", "")
    comparative_only_strategies = {
        CONTEXT_STRATEGY_COMPARATIVE_V3,
        CONTEXT_STRATEGY_COMPARATIVE_V4,
        CONTEXT_STRATEGY_COMPARATIVE_V5,
        CONTEXT_STRATEGY_COMPARATIVE_V6,
    }
    if strategy in comparative_only_strategies and category != "comparative":
        result.kept = list(entries)
        return result

    if strategy == CONTEXT_STRATEGY_ENUMERATION_V1:
        if category != "enumeration":
            result.kept = list(entries)
            return result
        branches = [
            EnumerationBranch(
                query=(
                    query_entry.get("query", {}).get("effective_query")
                    or query_entry.get("query", {}).get("retrieval_query")
                    or ""
                ),
                ticker=query_entry.get("query", {}).get("ticker"),
                chunks=query_entry.get("chunks", []),
            )
            for query_entry in case_payload.get("queries", [])
        ]
        kept_ids = {
            entry.get("chunk_id") for entry in select_enumeration_chunks(branches)
        }
        result.kept = [
            entry for entry in entries if entry.get("chunk_id") in kept_ids
        ]
        result.dropped = [
            entry for entry in entries if entry.get("chunk_id") not in kept_ids
        ]
        return result

    if strategy == FACT_CONTEXT_STRATEGY:
        selected = selected_fact_entries(case_payload)
        selected_ids = {entry.get("chunk_id") for entry in selected}
        result.kept = selected
        result.dropped = [
            entry for entry in entries if entry.get("chunk_id") not in selected_ids
        ]
        return result

    if strategy == CONTEXT_STRATEGY_COMPARATIVE_V5:
        branches = [
            ComparativeBranch(
                query=(
                    query_entry.get("query", {}).get("effective_query")
                    or query_entry.get("query", {}).get("retrieval_query")
                    or ""
                ),
                ticker=query_entry.get("query", {}).get("ticker"),
                chunks=query_entry.get("chunks", []),
            )
            for query_entry in case_payload.get("queries", [])
        ]
        kept_ids = {
            entry.get("chunk_id")
            for entry in select_comparative_chunks(branches)
        }
        result.kept = [
            entry for entry in entries if entry.get("chunk_id") in kept_ids
        ]
        result.dropped = [
            entry for entry in entries if entry.get("chunk_id") not in kept_ids
        ]
        return result
    if strategy == CONTEXT_STRATEGY_COMPARATIVE_V6:
        branches = [
            ComparativeBranch(
                query=(
                    query_entry.get("query", {}).get("effective_query")
                    or query_entry.get("query", {}).get("retrieval_query")
                    or ""
                ),
                ticker=query_entry.get("query", {}).get("ticker"),
                chunks=query_entry.get("chunks", []),
            )
            for query_entry in case_payload.get("queries", [])
        ]
        kept_ids = {
            entry.get("chunk_id")
            for entry in select_comparative_chunks_intent_first(branches)
        }
        result.kept = [
            entry for entry in entries if entry.get("chunk_id") in kept_ids
        ]
        result.dropped = [
            entry for entry in entries if entry.get("chunk_id") not in kept_ids
        ]
        return result
    if strategy == CONTEXT_STRATEGY_ROUTE_AWARE_V3 and category == "summary":
        return _pack_summary_intent_first(case_payload, required_keywords)
    if strategy == CONTEXT_STRATEGY_ROUTE_AWARE_V4 and category == "summary":
        return _pack_summary_with_direct_anchors(case_payload, required_keywords)
    expected_tickers = sorted({
        query["query"].get("ticker")
        for query in case_payload.get("queries", [])
        if isinstance(query.get("query"), dict)
        and query["query"].get("ticker")
    })

    kept: list[dict] = []
    kept_chunk_ids: set[str] = set()

    def _add(entry: dict | None) -> bool:
        if entry is None:
            return False
        chunk_id = entry.get("chunk_id")
        if chunk_id in kept_chunk_ids:
            return False
        kept.append(entry)
        kept_chunk_ids.add(chunk_id)
        return True

    def _top_by(predicate) -> dict | None:
        candidates = [e for e in entries if predicate(e)]
        if not candidates:
            return None
        return max(
            enumerate(candidates),
            key=lambda pair: (
                pair[1].get("score") if isinstance(pair[1].get("score"), (int, float)) else float("-inf"),
                -pair[0],
            ),
        )[1]

    uncovered: list[str] = []

    # M1: primary context — the globally first chunk.
    _add(entries[0] if entries else None)
    # M2: structured-lookup promotions.
    for entry in entries:
        score = entry.get("score")
        if isinstance(score, (int, float)) and score >= STRUCTURED_PROMOTION_SCORE:
            _add(entry)
    # V3 comparative breadth: preserve the leading evidence from every
    # decomposed branch instead of collapsing each company to one chunk.
    if strategy == CONTEXT_STRATEGY_COMPARATIVE_V3:
        for query_entry in case_payload.get("queries", []):
            branch_ids: set[str] = set()
            for entry in query_entry.get("chunks", []):
                chunk_id = entry.get("chunk_id")
                if chunk_id in branch_ids:
                    continue
                branch_ids.add(chunk_id)
                _add(entry)
                if len(branch_ids) >= COMPARATIVE_BRANCH_TARGET:
                    break
    # V4 comparative salience: keep one leading chunk per branch, then add
    # only a branch-scoped fact donor or a query-intent donor that contributes
    # evidence the leading chunk does not contain.
    if strategy == CONTEXT_STRATEGY_COMPARATIVE_V4:
        question = case_payload.get("question", "")
        for query_entry in case_payload.get("queries", []):
            branch = _branch_entries(query_entry)
            primary = branch[0] if branch else None
            _add(primary)
            query = query_entry.get("query", {})
            ticker = query.get("ticker") if isinstance(query, dict) else None
            for term in branch_evidence_terms(question, ticker):
                needle = _compact(term)
                if any(
                    needle in _compact(entry.get("text", ""))
                    for entry in branch
                    if entry.get("chunk_id") in kept_chunk_ids
                ):
                    continue
                donor = next(
                    (
                        entry
                        for entry in branch
                        if needle in _compact(entry.get("text", ""))
                    ),
                    None,
                )
                if donor is None:
                    uncovered.append(f"{ticker or 'unknown'}:{term}")
                else:
                    _add(donor)
            groups = _intent_groups(query_entry)
            covered = (
                frozenset().union(
                    *(
                        _matched_intent_groups(entry, groups)
                        for entry in branch
                        if entry.get("chunk_id") in kept_chunk_ids
                    )
                )
                if groups
                else frozenset()
            )
            _add(_best_intent_donor(branch, groups, covered))
    # M2b: a direct fact-lookup answer may cite at most one supporting
    # passage next to its exact structured hit; keep the strongest one.
    if category == "fact_lookup":
        has_structured = any(
            isinstance(e.get("score"), (int, float))
            and e["score"] >= STRUCTURED_PROMOTION_SCORE
            for e in kept
        )
        if has_structured and len(kept) < 2:
            _add(_top_by(lambda e: not (
                isinstance(e.get("score"), (int, float))
                and e["score"] >= STRUCTURED_PROMOTION_SCORE
            )))
    # M3: comparative balance — best chunk per expected ticker.
    if expected_tickers:
        for ticker in expected_tickers:
            _add(_top_by(lambda e, t=ticker: _chunk_ticker(e) == t))
    # M4: required-keyword coverage.
    required_terms = tuple(required_keywords or ())
    if strategy in comparative_only_strategies:
        required_terms = evidence_terms(
            case_payload.get("question", ""), required_terms
        )
    for keyword in required_terms:
        needle = _compact(keyword)
        if not needle:
            continue
        covered = any(needle in _compact(e.get("text", "")) for e in kept)
        if covered:
            continue
        donor = _top_by(lambda e: needle in _compact(e.get("text", "")))
        if donor is None:
            uncovered.append(keyword)
        else:
            _add(donor)
    result.uncovered_keywords = uncovered
    # Fill targets for synthesis-style categories.
    target = _FILL_TARGETS.get(category)
    if target and len(kept) < target:
        ranked = sorted(
            enumerate(entries),
            key=lambda pair: (
                -(pair[1].get("score") if isinstance(pair[1].get("score"), (int, float)) else float("-inf")),
                pair[0],
            ),
        )
        for _, entry in ranked:
            if len(kept) >= target:
                break
            _add(entry)

    # Restore source order for stable [Source N] numbering.
    ordered = [
        entry for entry in entries if entry.get("chunk_id") in kept_chunk_ids
    ]
    result.kept = ordered
    result.dropped = [
        entry for entry in entries if entry.get("chunk_id") not in kept_chunk_ids
    ]
    return result


def render_packed_blocks(packed: PackedContext) -> str:
    """Render the kept subset in the shared [Source N] block format."""
    return render_chunk_evidence(packed.kept)


def render_case_context(
    case_payload: dict,
    *,
    required_keywords: list[str] | None = None,
    strategy: str = CONTEXT_STRATEGY_FULL_EVIDENCE,
) -> str:
    """Render one case under a named policy with one shared implementation."""
    concrete_strategy = effective_case_context_strategy(
        strategy, case_payload.get("category", "")
    )
    if concrete_strategy == CONTEXT_STRATEGY_FULL_EVIDENCE:
        return build_evidence_context(case_payload)
    packed = pack_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=concrete_strategy,
    )
    return render_packed_blocks(packed)


def count_tokens(text: str, encoder) -> int:
    """Token count through an injected tiktoken encoder (hermetic tests)."""
    return len(encoder.encode(text))
