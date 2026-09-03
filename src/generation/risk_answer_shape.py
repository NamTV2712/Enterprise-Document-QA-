"""Provider-free shape checks and rendering for exhaustive risk answers.

The risk renderer is intentionally narrow.  It consumes only the rendered
evidence and the evidence-derived risk taxonomy; it never reads evaluation
labels, ground truth, or required-keyword metadata.  It is used by the V14
candidate path so provider wording cannot change the answer's risk granularity.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.generation.enumeration_completeness import (
    EnumerationCompleteness,
    _bullet_content,
    _bullet_item_matches,
    _contains_alias,
    _risk_evidence_descriptor,
    assess_enumeration_completeness,
)
from src.generation.period_value_completeness import parse_evidence_sources


RISK_ANSWER_SHAPE_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"risk-answer-shape-v16-deterministic-major-risk-canonical-scope-"
    b"source-bound-short-clause-descriptors-supporting-label-only-"
    b"one-bullet-per-evidence-item-no-unsupported-peer"
).hexdigest()

_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_SOURCE_CITATION_RE = re.compile(
    r"(?:\[\s*Source\s+(?P<ascii>\d+)\s*\]|"
    r"【\s*Source\s*(?P<cjk>\d+)\s*】)",
    re.IGNORECASE,
)
_SUPPORT_SECTION_RE = re.compile(
    r"^\s*(?:additional cross-cutting risks|supporting items)\s*:?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RiskAnswerShapeAssessment:
    """Deterministic structural assessment for one exhaustive risk answer."""

    applicable: bool
    canonical_count: int
    supporting_count: int
    canonical_bullets: int
    supporting_bullets: int
    support_section_count: int
    reason_codes: tuple[str, ...]
    passed: bool


def _bullet_indexes(answer: str) -> tuple[int, ...]:
    return tuple(
        index
        for index, line in enumerate(answer.splitlines())
        if _BULLET_RE.match(line)
    )


def _item_label_in_line(line: str, item: object) -> bool:
    content = _bullet_content(line)
    return any(_contains_alias(content, alias) for alias in item.aliases)


def _has_descriptor(
    line: str,
    item: object,
    evidence_context: str,
) -> bool:
    """Return whether a bullet contains detail when evidence provides detail."""
    if item.evidence_role == "supporting":
        # Supporting disclosures are already explicit labels in the grouped
        # section. Requiring a second prose sentence makes the exhaustive
        # answer look broader without improving evidence coverage.
        return True
    descriptor = _risk_evidence_descriptor(item, evidence_context)
    if not descriptor:
        return True
    content = _SOURCE_CITATION_RE.sub("", _bullet_content(line)).strip()
    label = str(item.label).strip()
    if content.casefold().startswith(label.casefold()):
        remainder = content[len(label):].strip(" \t:—–-;,.")
    else:
        remainder = content
    return len(re.findall(r"[A-Za-z0-9]+", remainder)) >= 2


_LEADING_RISK_SUBJECT_RE = re.compile(
    r"^(?:we\s+(?:face|may\s+have|are\s+subject\s+to)|"
    r"our\s+(?:company|business)\s+is)\s+",
    re.IGNORECASE,
)
_RISK_CLAUSE_STOP_RE = re.compile(
    r"\s+(?:which\s+could|that\s+could|that\s+may|if\s+we\s+|"
    r"may\s+(?:increase|result|adversely)|could\s+adversely|"
    r"also\s+affect|can\s+take)\b",
    re.IGNORECASE,
)


def _compact_risk_descriptor(item: object, evidence_context: str) -> str:
    """Keep one short source clause instead of reproducing full prose."""
    descriptor = _risk_evidence_descriptor(item, evidence_context)
    if not descriptor:
        return ""
    descriptor = _LEADING_RISK_SUBJECT_RE.sub("", descriptor).strip()
    descriptor = re.sub(r"^increasing\s+", "", descriptor, flags=re.IGNORECASE)
    stop = _RISK_CLAUSE_STOP_RE.search(descriptor)
    if stop:
        descriptor = descriptor[: stop.start()].rstrip(" ,;:")
    words = descriptor.split()
    if len(words) > 14:
        descriptor = " ".join(words[:14]).rstrip(" ,;:") + "…"
    return descriptor.strip(" .;,:-—–")


def _matched_item_indexes(
    answer: str,
    assessment: EnumerationCompleteness,
) -> dict[int, int]:
    required_items = assessment.required_items or assessment.evidence_items
    required_positions = {
        index: item
        for index, item in enumerate(assessment.evidence_items)
        if item in required_items
    }
    raw_matches = _bullet_item_matches(answer, assessment)
    position_by_item = {
        item: index for index, item in enumerate(required_items)
    }
    return {
        line_index: position_by_item[required_positions[item_index]]
        for line_index, item_index in raw_matches.items()
        if item_index in required_positions
        and required_positions[item_index] in position_by_item
    }


def assess_risk_answer_shape(
    question: str,
    evidence_context: str,
    answer: str,
) -> RiskAnswerShapeAssessment:
    """Check canonical/supporting roles, ordering, citations, and descriptors."""
    enumeration = assess_enumeration_completeness(
        question, evidence_context, answer
    )
    if not enumeration.applicable or enumeration.kind != "risk":
        return RiskAnswerShapeAssessment(False, 0, 0, 0, 0, 0, (), True)

    items = enumeration.required_items or enumeration.evidence_items
    canonical = {
        index for index, item in enumerate(items) if item.evidence_role == "canonical"
    }
    supporting = {
        index for index, item in enumerate(items) if item.evidence_role == "supporting"
    }
    lines = answer.splitlines()
    bullets = _bullet_indexes(answer)
    matches = _matched_item_indexes(answer, enumeration)
    reasons: set[str] = set()

    section_indexes = tuple(
        index
        for index, line in enumerate(lines)
        if _SUPPORT_SECTION_RE.match(line)
    )
    if supporting and len(section_indexes) != 1:
        reasons.add("supporting_section_count")
    if len(section_indexes) > 1:
        reasons.add("duplicate_supporting_section")

    seen_items: list[int] = []
    canonical_positions: list[int] = []
    supporting_positions: list[int] = []
    for line_index in bullets:
        item_index = matches.get(line_index)
        if item_index is None:
            reasons.add("unsupported_peer")
            continue
        seen_items.append(item_index)
        item = items[item_index]
        if item_index in canonical:
            canonical_positions.append(line_index)
        else:
            supporting_positions.append(line_index)

        citations = [
            int(match.group("ascii") or match.group("cjk"))
            for match in _SOURCE_CITATION_RE.finditer(lines[line_index])
        ]
        if len(citations) != 1 or citations[0] != item.source_number:
            reasons.add("item_source_citation_mismatch")
        if not _has_descriptor(lines[line_index], item, evidence_context):
            reasons.add("description_missing")

    if not bullets and (canonical or supporting):
        reasons.add("no_bulleted_items")
    if len(seen_items) != len(set(seen_items)):
        reasons.add("duplicate_item")
    if set(seen_items) != canonical | supporting:
        reasons.add("missing_or_extra_item")
    if canonical_positions != sorted(canonical_positions):
        reasons.add("canonical_order_invalid")
    if canonical_positions and supporting_positions:
        if min(supporting_positions) < max(canonical_positions):
            reasons.add("supporting_before_canonical")
        if not section_indexes or min(supporting_positions) < section_indexes[0]:
            reasons.add("supporting_not_grouped")
    if supporting and section_indexes:
        if any(index < section_indexes[0] for index in supporting_positions):
            reasons.add("supporting_outside_section")
    if not supporting and section_indexes:
        reasons.add("empty_supporting_section")

    canonical_bullets = sum(
        1 for item_index in matches.values() if item_index in canonical
    )
    supporting_bullets = sum(
        1 for item_index in matches.values() if item_index in supporting
    )
    return RiskAnswerShapeAssessment(
        True,
        len(canonical),
        len(supporting),
        canonical_bullets,
        supporting_bullets,
        len(section_indexes),
        tuple(sorted(reasons)),
        not reasons,
    )


def render_deterministic_risk_answer(
    question: str,
    evidence_context: str,
) -> str | None:
    """Render an exhaustive risk answer directly from the evidence taxonomy."""
    enumeration = assess_enumeration_completeness(question, evidence_context, "")
    if not enumeration.applicable or enumeration.kind != "risk":
        return None
    sources = parse_evidence_sources(evidence_context)
    if not sources or not enumeration.evidence_items:
        return None

    lines: list[str] = []
    required_items = enumeration.required_items or enumeration.evidence_items
    for item in required_items:
        if item.evidence_role != "canonical":
            continue
        descriptor = _compact_risk_descriptor(item, evidence_context)
        suffix = f" — {descriptor}" if descriptor else ""
        lines.append(
            f"- {item.label}{suffix} [Source {item.source_number}]"
        )
    supporting = [
        item
        for item in required_items
        if item.evidence_role == "supporting"
    ]
    if supporting:
        lines.append("Additional cross-cutting risks:")
        for item in supporting:
            # The supporting section is intentionally label-only: its role is
            # completeness coverage, while canonical bullets carry the short
            # source-bound descriptors that explain the major categories.
            suffix = ""
            lines.append(
                f"  - {item.label}{suffix} [Source {item.source_number}]"
            )
    return "\n".join(lines)
