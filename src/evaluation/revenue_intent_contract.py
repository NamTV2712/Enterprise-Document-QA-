"""Human-reviewed, evaluation-only scope contract for revenue enumerations.

The generation path must remain evidence-only.  This module is intentionally
owned by evaluation so a reviewed expected-item set can adjudicate the one
known ambiguity without being imported by production answer rendering.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from src.generation.enumeration_completeness import (
    assess_enumeration_completeness,
    enumeration_kind,
)


REVENUE_INTENT_CONTRACT_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"revenue-intent-contract-v1-human-reviewed-main-vs-exhaustive-"
    b"microsoft-main-core-families-search-news-supporting-evaluation-only"
).hexdigest()

MICROSOFT_MAIN_REVENUE_QUESTION = (
    "What are the main sources of revenue for Microsoft?"
)


@dataclass(frozen=True)
class ExpectedRevenueFamily:
    """A reviewed semantic family and its evidence-proven aliases."""

    name: str
    aliases: tuple[str, ...]


# This fixture is not read by src.generation.  It records the independent
# human review of the benchmark wording and makes the scope disagreement
# inspectable instead of silently changing the ground truth.
MICROSOFT_MAIN_CORE_FAMILIES = (
    ExpectedRevenueFamily("Microsoft 365", ("Microsoft 365",)),
    ExpectedRevenueFamily(
        "Azure/cloud services",
        ("Azure", "Cloud Services", "Server Products and Cloud Services"),
    ),
    ExpectedRevenueFamily("LinkedIn", ("LinkedIn",)),
    ExpectedRevenueFamily("Dynamics", ("Dynamics",)),
    ExpectedRevenueFamily("Xbox/gaming", ("Xbox", "Gaming")),
    ExpectedRevenueFamily("Windows OEM", ("Windows OEM", "Windows")),
    ExpectedRevenueFamily("Devices", ("Devices",)),
)

MICROSOFT_MAIN_ALLOWED_SUPPORTING = ("Search and News Advertising",)


def _normalize(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _text_contains_alias(text: str, alias: str) -> bool:
    haystack = _normalize(text)
    needle = _normalize(alias)
    if not haystack or not needle:
        return False
    haystack_tokens = haystack.split()
    needle_tokens = needle.split()
    width = len(needle_tokens)
    return any(
        haystack_tokens[index : index + width] == needle_tokens
        for index in range(len(haystack_tokens) - width + 1)
    )


def _family_is_evidence_proven(family: ExpectedRevenueFamily, items: Any) -> bool:
    return any(
        _text_contains_alias(" ".join(item.aliases), alias)
        for item in items
        for alias in family.aliases
    )


def _family_is_answered(family: ExpectedRevenueFamily, answer: str) -> bool:
    return any(_text_contains_alias(answer, alias) for alias in family.aliases)


def audit_revenue_intent_scope(
    question: str,
    evidence_context: str,
    answer: str,
) -> dict[str, Any]:
    """Audit reviewed revenue scope while preserving evidence provenance."""
    assessment = assess_enumeration_completeness(question, evidence_context, answer)
    if enumeration_kind(question) != "revenue":
        return {
            "applicable": False,
            "passed": True,
            "question_scope": "not_revenue_enumeration",
            "contract_fingerprint": REVENUE_INTENT_CONTRACT_FINGERPRINT,
        }

    is_main = question == MICROSOFT_MAIN_REVENUE_QUESTION
    scope = "main" if is_main else "exhaustive_or_other"
    evidence_items = assessment.evidence_items
    supporting_labels = [
        item.label
        for item in evidence_items
        if item.evidence_role == "supporting"
    ]
    supporting_answered = [
        label
        for label in supporting_labels
        if _text_contains_alias(answer, label)
    ]

    if is_main:
        families = [
            {
                "name": family.name,
                "evidence_proven": _family_is_evidence_proven(
                    family, evidence_items
                ),
                "answered": _family_is_answered(family, answer),
            }
            for family in MICROSOFT_MAIN_CORE_FAMILIES
        ]
        missing_families = [
            family["name"]
            for family in families
            if not family["evidence_proven"] or not family["answered"]
        ]
        allowed_supporting_present = [
            label
            for label in MICROSOFT_MAIN_ALLOWED_SUPPORTING
            if _text_contains_alias(answer, label)
        ]
        allowed_supporting_evidence_present = [
            label
            for label in MICROSOFT_MAIN_ALLOWED_SUPPORTING
            if any(
                _text_contains_alias(item.label, label)
                for item in evidence_items
            )
        ]
        passed = (
            assessment.applicable
            and not assessment.missing_items
            and not missing_families
            and {
                label.casefold() for label in supporting_labels
            }.issubset(
                {label.casefold() for label in MICROSOFT_MAIN_ALLOWED_SUPPORTING}
            )
            and {
                label.casefold() for label in allowed_supporting_present
            }.issubset(
                {label.casefold() for label in allowed_supporting_evidence_present}
            )
        )
        return {
            "applicable": True,
            "passed": passed,
            "question_scope": scope,
            "contract_fingerprint": REVENUE_INTENT_CONTRACT_FINGERPRINT,
            "core_families": families,
            "missing_core_families": missing_families,
            "supporting_evidence_items": supporting_labels,
            "supporting_items_in_answer": supporting_answered,
            "allowed_supporting_items": list(MICROSOFT_MAIN_ALLOWED_SUPPORTING),
            "allowed_supporting_evidence_present": allowed_supporting_evidence_present,
            "allowed_supporting_items_are_optional": True,
            "generation_ground_truth_dependency": False,
        }

    return {
        "applicable": True,
        "passed": assessment.passed,
        "question_scope": scope,
        "contract_fingerprint": REVENUE_INTENT_CONTRACT_FINGERPRINT,
        "required_items": [item.label for item in assessment.required_items],
        "missing_items": [item.label for item in assessment.missing_items],
        "supporting_evidence_items": supporting_labels,
        "supporting_items_in_answer": supporting_answered,
        "supporting_items_required": True,
        "generation_ground_truth_dependency": False,
    }
