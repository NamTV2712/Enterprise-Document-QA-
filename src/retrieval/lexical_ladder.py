"""Conservative field-aware lexical candidate fallback.

The ladder searches only the ticker/section scope already selected by the
retrieval plan. It returns the first non-empty tier in strict order and keeps
fuzzy matching disabled unless a ticker is known and every exact tier missed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable


LEXICAL_LADDER_VERSION = 1
FUZZY_MIN_TERM_LENGTH = 5
FUZZY_SIMILARITY = 0.88
LEXICAL_LADDER_FINGERPRINT = "sha256:" + hashlib.sha256(
    json.dumps(
        {
            "version": LEXICAL_LADDER_VERSION,
            "tier_order": [
                "exact_phrase",
                "full_terms",
                "partial_terms",
                "fuzzy",
            ],
            "partial_minimum": "max(2, ceil(2/3 * terms))",
            "fuzzy_min_term_length": FUZZY_MIN_TERM_LENGTH,
            "fuzzy_similarity": FUZZY_SIMILARITY,
            "fuzzy_requires_ticker": True,
            "fuzzy_max_candidates": 3,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", text.casefold()))


def _normalized(text: str) -> str:
    return " ".join(_tokens(text))


@dataclass(frozen=True)
class LexicalCandidate:
    chunk: dict
    tier: str
    matched_terms: int
    score: float


def _scope_chunks(
    chunks: Iterable[dict],
    ticker: str | None,
    section: str | None,
) -> list[dict]:
    return [
        chunk
        for chunk in chunks
        if (ticker is None or chunk.get("ticker") == ticker)
        and (section is None or chunk.get("section") == section)
    ]


def _rank(
    matches: list[LexicalCandidate], max_candidates: int
) -> list[LexicalCandidate]:
    return sorted(
        matches,
        key=lambda match: (
            -match.score,
            -match.matched_terms,
            match.chunk["chunk_id"],
        ),
    )[:max_candidates]


def _exact_phrase_candidates(
    chunks: list[dict], phrases: tuple[str, ...]
) -> list[LexicalCandidate]:
    normalized_phrases = tuple(_normalized(phrase) for phrase in phrases if phrase)
    matches: list[LexicalCandidate] = []
    for chunk in chunks:
        text = _normalized(chunk.get("text", ""))
        hits = sum(text.count(phrase) for phrase in normalized_phrases)
        if hits:
            matches.append(LexicalCandidate(chunk, "exact_phrase", hits, float(hits)))
    return matches


def _term_candidates(
    chunks: list[dict],
    terms: tuple[str, ...],
    tier: str,
    minimum_hits: int,
) -> list[LexicalCandidate]:
    normalized_terms = tuple(dict.fromkeys(_normalized(term) for term in terms if term))
    matches: list[LexicalCandidate] = []
    for chunk in chunks:
        text = _normalized(chunk.get("text", ""))
        token_set = set(text.split())
        hits = sum(
            term in text if " " in term else term in token_set
            for term in normalized_terms
        )
        if hits >= minimum_hits:
            matches.append(
                LexicalCandidate(
                    chunk=chunk,
                    tier=tier,
                    matched_terms=hits,
                    score=hits / max(1, len(normalized_terms)),
                )
            )
    return matches


def _fuzzy_candidates(
    chunks: list[dict], terms: tuple[str, ...]
) -> list[LexicalCandidate]:
    guarded_terms = tuple(
        term
        for term in dict.fromkeys(_normalized(term) for term in terms if term)
        if len(term) >= FUZZY_MIN_TERM_LENGTH
    )
    if not guarded_terms:
        return []

    matches: list[LexicalCandidate] = []
    for chunk in chunks:
        chunk_tokens = _tokens(chunk.get("text", ""))
        similarities = [
            max(
                (SequenceMatcher(None, term, token).ratio() for token in chunk_tokens),
                default=0.0,
            )
            for term in guarded_terms
        ]
        if similarities and min(similarities) >= FUZZY_SIMILARITY:
            matches.append(
                LexicalCandidate(
                    chunk=chunk,
                    tier="fuzzy",
                    matched_terms=len(similarities),
                    score=sum(similarities) / len(similarities),
                )
            )
    return matches


def lexical_ladder_candidates(
    chunks: Iterable[dict],
    *,
    ticker: str | None,
    section: str | None,
    exact_phrases: tuple[str, ...] = (),
    full_terms: tuple[str, ...] = (),
    partial_terms: tuple[str, ...] = (),
    fuzzy_terms: tuple[str, ...] = (),
    max_candidates: int = 10,
) -> list[LexicalCandidate]:
    """Return candidates from the first non-empty lexical tier."""
    scoped = _scope_chunks(chunks, ticker, section)
    if not scoped or max_candidates <= 0:
        return []

    exact = _exact_phrase_candidates(scoped, exact_phrases)
    if exact:
        return _rank(exact, max_candidates)

    normalized_full = tuple(
        dict.fromkeys(_normalized(term) for term in full_terms if term)
    )
    if normalized_full:
        full = _term_candidates(
            scoped, normalized_full, "full_terms", len(normalized_full)
        )
        if full:
            return _rank(full, max_candidates)

    normalized_partial = tuple(
        dict.fromkeys(_normalized(term) for term in partial_terms if term)
    )
    if normalized_partial:
        minimum_hits = max(2, math.ceil(len(normalized_partial) * 2 / 3))
        partial = _term_candidates(
            scoped, normalized_partial, "partial_terms", minimum_hits
        )
        if partial:
            return _rank(partial, max_candidates)

    if ticker is not None:
        fuzzy = _fuzzy_candidates(scoped, fuzzy_terms)
        if fuzzy:
            return _rank(fuzzy, min(max_candidates, 3))

    return []
