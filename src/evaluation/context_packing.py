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

from src.generation.comparative_context import (
    ComparativeBranch,
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
    }
    if strategy in comparative_only_strategies and category != "comparative":
        result.kept = list(entries)
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
    blocks: list[str] = []
    for index, entry in enumerate(packed.kept):
        blocks.append(
            f"[Source {index + 1}] {entry.get('citation', '')}\n"
            f"{entry.get('text', '')}"
        )
    return "\n\n".join(blocks)


def count_tokens(text: str, encoder) -> int:
    """Token count through an injected tiktoken encoder (hermetic tests)."""
    return len(encoder.encode(text))
