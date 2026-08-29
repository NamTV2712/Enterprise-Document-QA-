"""Oracle-free context selection for comparative generation.

The selector operates only on a question, branch queries, and ranked chunks.
It deliberately has no dependency on evaluation labels, ground truth, or
expected answer values, so the same decision can be used by production and
frozen-artifact replay adapters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from src.retrieval.query_shaper import shape_retrieval_query


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

# This is an implementation fingerprint for offline diagnostics and replay
# provenance. It is intentionally independent of evaluation labels.
COMPARATIVE_SELECTOR_FINGERPRINT = (
    "sha256:"
    "e3c7d6a17e420d0640e4a2d52bd8a6a3c8ee286cb0ffacac6958d3732f76e7c8"
)


@dataclass(frozen=True)
class ComparativeBranch:
    """One company branch and its already-ranked retrieval results."""

    query: str
    ticker: str | None
    chunks: Sequence[Any]


def _field(entry: Any, name: str, default: Any = None) -> Any:
    if isinstance(entry, dict):
        return entry.get(name, default)
    return getattr(entry, name, default)


def _chunk_id(entry: Any) -> str | None:
    value = _field(entry, "chunk_id")
    return value if isinstance(value, str) else None


def _entry_key(entry: Any) -> tuple[str, str | int]:
    chunk_id = _chunk_id(entry)
    if chunk_id is not None:
        return ("chunk", chunk_id)
    return ("object", id(entry))


def _text(entry: Any) -> str:
    value = _field(entry, "text", "")
    return value if isinstance(value, str) else ""


def _score(entry: Any) -> float:
    value = _field(entry, "score")
    return float(value) if isinstance(value, (int, float)) else float("-inf")


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def _has_multiple_period_value_pairs(text: str) -> bool:
    """Recognize a leader that already carries a multi-period numeric trend."""
    normalized = _normalize(text)
    years = re.findall(r"\b20\d{2}\b", normalized)
    values = re.findall(r"\b\d[\d,.]*(?:%|bn|billion|million)?\b", normalized)
    return len(years) >= 2 and len(values) >= 2


def _unique_chunks(chunks: Sequence[Any]) -> list[Any]:
    unique: list[Any] = []
    seen: set[tuple[str, str | int]] = set()
    for chunk in chunks:
        key = _entry_key(chunk)
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


def _phrase_hits(text: str, phrases: Sequence[str]) -> int:
    normalized_text = _normalize(text)
    return sum(normalized_text.count(_normalize(phrase)) for phrase in phrases)


def _best_hint_donor(branch: list[Any], primary: Any, query: str) -> Any | None:
    hints = shape_retrieval_query(query)
    phrases = tuple(phrase for phrase in hints.exact_phrases if phrase)
    if not phrases or _phrase_hits(_text(primary), phrases):
        return None

    candidates: list[tuple[int, float, int, Any]] = []
    for index, entry in enumerate(branch):
        hits = _phrase_hits(_text(entry), phrases)
        if not hits or entry is primary:
            continue
        candidates.append((hits, _score(entry), -index, entry))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[:-1])[-1]


def _intent_groups(query: str) -> tuple[tuple[str, ...], ...]:
    tokens = re.findall(r"[a-z0-9]+", query.casefold())
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
    entry: Any, groups: tuple[tuple[str, ...], ...]
) -> frozenset[int]:
    text = _normalize(_text(entry))
    return frozenset(
        index
        for index, alternatives in enumerate(groups)
        if any(_normalize(term) in text for term in alternatives)
    )


def _best_intent_donor(
    branch: list[Any], primary: Any, groups: tuple[tuple[str, ...], ...]
) -> Any | None:
    covered = _matched_intent_groups(primary, groups)
    missing = set(range(len(groups))) - set(covered)
    if not missing:
        return None

    # A ranked leader with explicit values for multiple periods is already
    # sufficient for a trend answer. Do not add a qualitative tail merely
    # because it contains the word "growth" or "increased".
    growth_groups = {
        index
        for index, alternatives in enumerate(groups)
        if "growth" in alternatives
    }
    if growth_groups & missing and _has_multiple_period_value_pairs(_text(primary)):
        return None

    candidates: list[tuple[int, int, float, int, Any]] = []
    for index, entry in enumerate(branch):
        if entry is primary:
            continue
        matched = _matched_intent_groups(entry, groups) & missing
        if not matched:
            continue
        text = _normalize(_text(entry))
        occurrences = sum(
            max(text.count(_normalize(term)) for term in groups[group_index])
            for group_index in matched
        )
        candidates.append((len(matched), occurrences, _score(entry), -index, entry))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[:-1])[-1]


def select_comparative_chunks(
    branches: Sequence[ComparativeBranch],
) -> list[Any]:
    """Keep branch leaders plus one evidence-shape donor at most.

    An exact filing phrase donor has priority because it is a deterministic
    retrieval hint. If no such donor exists, an intent donor is added only
    when the branch leader misses a query-intent group. Original branch/source
    order is restored after cross-branch de-duplication.
    """
    all_entries: list[Any] = []
    seen_all: set[tuple[str, str | int]] = set()
    for branch in branches:
        for entry in branch.chunks:
            key = _entry_key(entry)
            if key in seen_all:
                continue
            seen_all.add(key)
            all_entries.append(entry)

    kept_ids: set[tuple[str, str | int]] = set()

    def add(entry: Any | None) -> None:
        if entry is None:
            return
        kept_ids.add(_entry_key(entry))

    for branch in branches:
        entries = _unique_chunks(branch.chunks)
        if not entries:
            continue
        primary = entries[0]
        add(primary)
        for entry in entries:
            if _score(entry) >= 10.0:
                add(entry)
        donor = _best_hint_donor(entries, primary, branch.query)
        if donor is None:
            donor = _best_intent_donor(
                entries, primary, _intent_groups(branch.query)
            )
        add(donor)

    selected: list[Any] = []
    for index, entry in enumerate(all_entries):
        if _entry_key(entry) in kept_ids:
            selected.append(entry)
    return selected
