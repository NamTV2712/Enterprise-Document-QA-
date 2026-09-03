"""Provider-free rendering for narrow evidence-backed enumerations."""

from __future__ import annotations

import hashlib
import re

from src.generation.enumeration_completeness import (
    assess_enumeration_completeness,
    enumeration_kind,
)
from src.generation.period_value_completeness import parse_evidence_sources


ENUMERATION_ANSWER_RENDERER_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"enumeration-answer-renderer-v3-revenue-main-vs-exhaustive-scope-top-level-labels-with-"
    b"evidence-derived-short-aliases-citations-no-ground-truth"
).hexdigest()


_SHORT_REVENUE_ALIASES = {
    "server products and cloud services": ("Azure", "Server Products"),
    "gaming": ("Xbox",),
    "search and news advertising": ("Bing", "Copilot"),
    "windows and devices": ("Windows OEM", "Devices"),
}


def _revenue_label(item: object, evidence_context: str) -> str:
    label = str(item.label)
    source = next(
        (
            source
            for source in parse_evidence_sources(evidence_context)
            if source.number == item.source_number
        ),
        None,
    )
    aliases = tuple(
        alias
        for alias in _SHORT_REVENUE_ALIASES.get(label.casefold(), ())
        if source is not None
        and re.search(rf"\b{re.escape(alias)}\b", source.text, re.IGNORECASE)
    )
    return f"{label} ({'; '.join(aliases)})" if aliases else label


def render_deterministic_revenue_answer(
    question: str,
    evidence_context: str,
) -> str | None:
    """Render revenue-source labels at the filing's top-level granularity."""
    if enumeration_kind(question) != "revenue":
        return None
    if not parse_evidence_sources(evidence_context):
        return None
    assessment = assess_enumeration_completeness(question, evidence_context, "")
    if (
        not assessment.applicable
        or assessment.kind != "revenue"
        or not assessment.required_items
    ):
        return None
    return "\n".join(
        f"- {_revenue_label(item, evidence_context)} [Source {item.source_number}]"
        for item in assessment.required_items
    ) or None
