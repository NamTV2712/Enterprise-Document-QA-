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

Summary/enumeration cases additionally fill up to a small fixed target
by descending score because their answers synthesize broad topic
coverage rather than isolated facts. Out-of-corpus cases keep only M1;
their correct behavior is abstention and their context precision is
zero by design either way.

Selection NEVER changes source order, citations, or chunk text, and it
never adds evidence that full evidence would not contain.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CONTEXT_STRATEGY_FULL_EVIDENCE = "full_evidence_v1"
CONTEXT_STRATEGY_ROUTE_AWARE = "route_aware_v2"

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
    expected_tickers = sorted({
        query["query"].get("ticker")
        for query in case_payload.get("queries", [])
        if isinstance(query.get("query"), dict)
        and query["query"].get("ticker")
    })

    kept: list[dict] = []

    def _add(entry: dict | None) -> bool:
        if entry is None or any(entry is k for k in kept):
            return False
        kept.append(entry)
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

    # M1: primary context — the globally first chunk.
    _add(entries[0] if entries else None)
    # M2: structured-lookup promotions.
    for entry in entries:
        score = entry.get("score")
        if isinstance(score, (int, float)) and score >= STRUCTURED_PROMOTION_SCORE:
            _add(entry)
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
    uncovered: list[str] = []
    for keyword in required_keywords or []:
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
    kept_ids = {id(entry) for entry in kept}
    ordered = [entry for entry in entries if id(entry) in kept_ids]
    result.kept = ordered
    result.dropped = [entry for entry in entries if id(entry) not in kept_ids]
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
