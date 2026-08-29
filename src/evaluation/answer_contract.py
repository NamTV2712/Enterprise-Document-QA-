"""Deterministic answer-integrity checks for frozen evaluation answers.

These checks are diagnostics, not a replacement for the semantic judge. They
make citation and numeric-grounding regressions visible without a provider
call, so prompt or packing changes can be gated before spending quota.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_CANONICAL_CITATION_RE = re.compile(r"[\[【]Source\s+(\d+)[\]】]", re.IGNORECASE)
_LEGACY_LINE_CITATION_RE = re.compile(r"【\s*\d+\s*†\s*L[^】]*】")
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:[$€£]\s*)?[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?"
)
_FALLBACK_PHRASE = "could not find sufficient information"


@dataclass(frozen=True)
class AnswerIntegrity:
    canonical_citations: tuple[int, ...]
    malformed_line_citations: int
    out_of_range_citations: tuple[int, ...]
    uncited_answer: bool
    numeric_claims: tuple[str, ...]
    unsupported_numeric_claims: tuple[str, ...]
    fallback_answer: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _normalized_number(value: str) -> str:
    """Normalize punctuation/currency so OCR spacing does not hide matches."""
    return re.sub(r"[^0-9%.-]", "", value).lower()


def audit_answer(
    answer: str,
    source_texts: list[str],
) -> AnswerIntegrity:
    """Audit one answer against source texts in rendered ``Source N`` order."""
    citations = tuple(int(value) for value in _CANONICAL_CITATION_RE.findall(answer))
    out_of_range = tuple(sorted({n for n in citations if n < 1 or n > len(source_texts)}))
    fallback = _FALLBACK_PHRASE in answer.casefold()
    # A non-fallback answer must use the canonical source marker. Fallbacks
    # intentionally need not cite irrelevant retrieved chunks.
    uncited = not fallback and not citations

    cited_text = " ".join(
        source_texts[n - 1] for n in citations if 1 <= n <= len(source_texts)
    )
    cited_numbers = {_normalized_number(n) for n in _NUMBER_RE.findall(cited_text)}
    raw_numeric_claims = _NUMBER_RE.findall(answer)
    # Bare years and citation indices are not useful integrity claims. Keep
    # currency, percentages, and comma-grouped amounts (including $5).
    numeric_claims = tuple(dict.fromkeys(
        claim for claim in raw_numeric_claims
        if any(symbol in claim for symbol in ("$", "€", "£", "%"))
        or "," in claim
    ))
    unsupported = tuple(
        claim for claim in numeric_claims
        if _normalized_number(claim) not in cited_numbers
    )
    return AnswerIntegrity(
        canonical_citations=citations,
        malformed_line_citations=len(_LEGACY_LINE_CITATION_RE.findall(answer)),
        out_of_range_citations=out_of_range,
        uncited_answer=uncited,
        numeric_claims=numeric_claims,
        unsupported_numeric_claims=unsupported,
        fallback_answer=fallback,
    )


def render_source_texts(case_payload: dict) -> list[str]:
    """Return deduplicated evidence texts in the same order as Source N."""
    texts: list[str] = []
    seen: set[str] = set()
    for query in case_payload.get("queries", []):
        for chunk in query.get("chunks", []):
            chunk_id = chunk.get("chunk_id")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            texts.append(chunk.get("text", ""))
    return texts
