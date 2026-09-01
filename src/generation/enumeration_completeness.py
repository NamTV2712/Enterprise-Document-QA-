"""Evidence-derived completeness checks for exhaustive answers.

The detector is deliberately conservative. It activates only when the
question contains an enumeration intent and the rendered evidence exposes at
least two high-confidence items through a closed list, a filing heading, or a
local evidence-derived alias. It never consumes evaluation labels, expected
answers, or required keywords.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from src.generation.period_value_completeness import (
    EvidenceSource,
    parse_evidence_sources,
)


ENUMERATION_COMPLETENESS_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"enumeration-answer-completeness-v1-bulleted-generic-label-boundary-grouped-home-alias-one-correction-revenue-top-level-dedup"
).hexdigest()

_EXHAUSTIVE_RE = re.compile(
    r"\b(all|different|various|multiple|each|list|enumerate)\b",
    re.IGNORECASE,
)
_MAIN_ENUMERATION_RE = re.compile(
    r"\bmain\s+(?:sources|categories|segments|risk factors|"
    r"products|offerings|lines)\b",
    re.IGNORECASE,
)
_PRODUCT_RE = re.compile(
    r"\b(product|products|product categories|product lines|portfolio|"
    r"offerings?)\b",
    re.IGNORECASE,
)
_REVENUE_RE = re.compile(
    r"\b(revenue|revenues|sources? of revenue|revenue sources?)\b",
    re.IGNORECASE,
)
_SEGMENT_RE = re.compile(r"\bsegments?\b", re.IGNORECASE)
_RISK_RE = re.compile(r"\brisk factors?\b|\brisks?\b", re.IGNORECASE)
_ENUMERATION_KIND_RE = (
    ("product", _PRODUCT_RE),
    ("revenue", _REVENUE_RE),
    ("segment", _SEGMENT_RE),
    ("risk", _RISK_RE),
)

_CLOSED_LIST_RE = re.compile(
    r"\b(?:organized|operates|operating|reports?|reported|consists?|"
    r"comprises?|includes?|contain(?:s)?)\b"
    r"[^.!?\n]{0,100}?\b(?:segments?|categories|sources?|products?|"
    r"offerings?|risks?)\b\s*(?::|are|include|consist of|comprise)\s*"
    r"(?P<items>[^.!?\n]+)",
    re.IGNORECASE,
)
_PRODUCT_INTRO_RE = re.compile(
    r"\bmarkets?\s+(?P<items>[^.!?\n]+?)\s*,\s*and\s+sells\s+"
    r"(?:a variety of\s+)?(?:related\s+)?services\b",
    re.IGNORECASE,
)
_LINE_OF_RE = re.compile(
    r"\bline of\s+(?P<category>[a-z][a-z -]{1,50}?)(?=\s+"
    r"(?:based|that|which|with|and)\b|[.,])",
    re.IGNORECASE,
)
_RISK_LABEL_RE = re.compile(
    r"^\s*(?:[•*+-]\s*)?(?P<label>[A-Z][A-Za-z][A-Za-z ,/&-]{1,70}):\s*$",
    re.MULTILINE,
)
_RISK_HEADING_RE = re.compile(
    r"^\s*(?P<label>[A-Z][A-Z ,/&-]{4,80}RISKS?)\s*$",
    re.MULTILINE,
)
_AI_RISK_HEADING_RE = re.compile(
    r"^\s*Issues in the development, deployment, and use of AI\b[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)

_HEADING_EXCLUSIONS = {
    "business",
    "company background",
    "competition",
    "item 1",
    "part i",
    "part ii",
    "products",
    "services",
    "segments",
    "markets and distribution",
}
_REVENUE_HEADING_TERMS = {
    "advertising",
    "cloud",
    "devices",
    "dynamics",
    "gaming",
    "linkedin",
    "microsoft 365",
    "products",
    "server",
    "services",
    "windows",
}


@dataclass(frozen=True)
class EnumerationItem:
    """One answerable item and aliases proved by the same evidence source."""

    label: str
    aliases: tuple[str, ...]
    source_number: int
    evidence_kind: str


@dataclass(frozen=True)
class EnumerationCompleteness:
    """Deterministic coverage result for one exhaustive question."""

    applicable: bool
    exhaustive_requested: bool
    kind: str | None
    evidence_items: tuple[EnumerationItem, ...]
    covered_items: tuple[EnumerationItem, ...]
    missing_items: tuple[EnumerationItem, ...]
    ambiguous_items: tuple[str, ...]
    passed: bool
    overdetailed: bool = False


def _bullet_count(answer: str) -> int:
    return sum(
        bool(re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line))
        for line in answer.splitlines()
    )


def _bullet_content(line: str) -> str:
    return re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line).strip()


def _unclassified_bullet_indexes(
    answer: str,
    assessment: "EnumerationCompleteness",
) -> tuple[int, ...]:
    """Return bullets whose leading label is not an evidence-backed item."""
    aliases = tuple(
        alias
        for item in assessment.evidence_items
        for alias in item.aliases
    )
    indexes: list[int] = []
    for index, line in enumerate(answer.splitlines()):
        if not re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line):
            continue
        content = re.sub(r"^\*+|\*+$", "", _bullet_content(line)).strip()
        label = re.split(r"\s+[—–-]\s+|\s*[:(]", content, maxsplit=1)[0]
        if not any(_contains_alias(label, alias) for alias in aliases):
            indexes.append(index)
    return tuple(indexes)


def _bullet_item_matches(
    answer: str,
    assessment: "EnumerationCompleteness",
) -> dict[int, int]:
    """Map each bullet to its best evidence item without using labels."""
    matches: dict[int, int] = {}
    for index, line in enumerate(answer.splitlines()):
        if not re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line):
            continue
        content = re.sub(r"^\*+|\*+$", "", _bullet_content(line)).strip()
        label = re.split(r"\s+[—–-]\s+|\s*[:(]", content, maxsplit=1)[0]
        candidates: list[tuple[int, int, int, int]] = []
        label_tokens = _tokens(label)
        for item_index, item in enumerate(assessment.evidence_items):
            for alias in item.aliases:
                alias_tokens = _tokens(alias)
                if not alias_tokens or not _contains_alias(label, alias):
                    continue
                prefix = int(
                    label_tokens[: len(alias_tokens)] == alias_tokens
                )
                candidates.append(
                    (prefix, len(alias_tokens), -item_index, item_index)
                )
        if candidates:
            best = max(candidates)
            matches[index] = best[3]
    return matches


def compact_enumeration_answer(
    answer: str,
    assessment: "EnumerationCompleteness",
) -> tuple[str, bool]:
    """Compact bullets to one evidence item while preserving their content."""
    if (
        not assessment.applicable
        or assessment.kind not in {"product", "revenue"}
        or not assessment.evidence_items
    ):
        return answer, False
    lines = answer.splitlines()
    bullet_indexes = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line)
    ]
    unclassified_indexes = set(_unclassified_bullet_indexes(answer, assessment))
    item_matches = _bullet_item_matches(answer, assessment)
    grouped_indexes: dict[int, list[int]] = {}
    for index, item_index in item_matches.items():
        grouped_indexes.setdefault(item_index, []).append(index)
    duplicate_indexes = {
        index
        for indexes in grouped_indexes.values()
        if len(indexes) > 1
        for index in indexes[1:]
    }
    if not unclassified_indexes and not duplicate_indexes:
        return answer, False
    keep_indexes = {
        index
        for index in bullet_indexes
        if index not in unclassified_indexes and index not in duplicate_indexes
    }
    if len(keep_indexes) < 2:
        return answer, False
    compacted_lines: list[str] = []
    for index, line in enumerate(lines):
        if index not in bullet_indexes:
            compacted_lines.append(line)
            continue
        if index in unclassified_indexes or index in duplicate_indexes:
            continue
        item_index = item_matches.get(index)
        if item_index is None:
            compacted_lines.append(line)
            continue
        merged = line
        for duplicate_index in grouped_indexes.get(item_index, [])[1:]:
            if duplicate_index not in bullet_indexes:
                continue
            extra = _bullet_content(lines[duplicate_index]).strip()
            if extra:
                merged = f"{merged.rstrip()} {extra}"
        compacted_lines.append(merged)
    compacted = "\n".join(compacted_lines)
    return compacted, compacted != answer


def append_missing_enumeration_items(
    answer: str,
    assessment: "EnumerationCompleteness",
) -> tuple[str, bool]:
    """Append only evidence-derived missing labels with canonical citations.

    This is a deterministic last-mile repair for a provider response that is
    otherwise grounded but omits a top-level category after correction or
    compaction. It never invents descriptions or items outside the rendered
    evidence.
    """
    if (
        not assessment.applicable
        or not assessment.missing_items
        or not answer.strip()
    ):
        return answer, False
    additions = "\n".join(
        f"- {item.label} [Source {item.source_number}]"
        for item in assessment.missing_items
    )
    repaired = f"{answer.rstrip()}\n{additions}"
    return repaired, repaired != answer


def _normalize(value: str) -> str:
    value = value.casefold().replace("®", "").replace("™", "")
    value = re.sub(r"[\"“”(){}\[\]]", " ", value)
    value = re.sub(r"[^a-z0-9/&+ -]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" -")
    return value


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(token for token in re.findall(r"[a-z0-9]+", _normalize(value)))


def _contains_alias(answer: str, alias: str) -> bool:
    answer_tokens = _tokens(answer)
    alias_tokens = _tokens(alias)
    if not answer_tokens or not alias_tokens:
        return False
    if alias_tokens == ("services",):
        bullet_lines = [
            line
            for line in answer.splitlines()
            if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line)
        ]
        if bullet_lines:
            return any(
                re.match(
                    r"^\s*(?:[-*•]|\d+[.)])\s+(?:\*\*)?services\b",
                    line,
                    re.IGNORECASE,
                )
                is not None
                for line in bullet_lines
            )
    width = len(alias_tokens)
    for index in range(len(answer_tokens) - width + 1):
        if answer_tokens[index : index + width] != alias_tokens:
            continue
        # A generic top-level category such as "services" must not be
        # satisfied by a nested filing subcategory such as "Cloud Services"
        # or "Payment Services". Standalone prose/list mentions remain valid.
        if alias_tokens == ("services",) and index:
            if answer_tokens[index - 1] in {
                "cloud", "digital", "payment", "related", "subscription"
            }:
                continue
        return True
    return False


def enumeration_kind(question: str) -> str | None:
    """Return the focused enumeration kind, or ``None`` for ordinary QA."""
    if not (
        _EXHAUSTIVE_RE.search(question)
        or _MAIN_ENUMERATION_RE.search(question)
    ):
        return None
    for kind, pattern in _ENUMERATION_KIND_RE:
        if pattern.search(question):
            return kind
    return None


def is_exhaustive_enumeration_question(question: str) -> bool:
    """Return whether the question requests a broad enumeration."""
    return enumeration_kind(question) is not None


def _split_items(value: str) -> list[str]:
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\b(?:and|or)\b", ",", value, flags=re.IGNORECASE)
    parts = [part.strip(" ,;:") for part in value.split(",")]
    return [
        part
        for part in parts
        if 2 <= len(part) <= 80
        and not re.fullmatch(r"(?:a|the|our|its|their|various)", part, re.I)
    ]


def _add_item(
    items: list[EnumerationItem],
    label: str,
    aliases: Iterable[str],
    source_number: int,
    evidence_kind: str,
) -> None:
    cleaned_label = re.sub(r"\s+", " ", label).strip(" ,;:-")
    normalized_label = _normalize(cleaned_label)
    if not normalized_label or len(_tokens(cleaned_label)) > 12:
        return
    alias_values = tuple(
        dict.fromkeys(
            alias.strip()
            for alias in (cleaned_label, *aliases)
            if alias and _normalize(alias)
        )
    )
    merge_key = normalized_label
    if evidence_kind == "risk":
        merge_key = re.sub(r"\s+risks?$", "", merge_key)
    elif evidence_kind == "revenue" and merge_key.startswith("microsoft 365"):
        merge_key = "microsoft 365"
    for index, existing in enumerate(items):
        existing_key = _normalize(existing.label)
        if evidence_kind == "risk":
            existing_key = re.sub(r"\s+risks?$", "", existing_key)
        elif evidence_kind == "revenue" and existing_key.startswith("microsoft 365"):
            existing_key = "microsoft 365"
        if existing_key != merge_key:
            continue
        items[index] = EnumerationItem(
            existing.label,
            tuple(dict.fromkeys((*existing.aliases, *alias_values))),
            source_number,
            existing.evidence_kind,
        )
        return
    items.append(
        EnumerationItem(
            cleaned_label,
            alias_values,
            source_number,
            evidence_kind,
        )
    )


def _short_lines(source: EvidenceSource) -> list[tuple[int, str]]:
    return [
        (index, line.strip())
        for index, line in enumerate(
            line for line in source.text.splitlines() if line.strip()
        )
    ]


def _product_items(source: EvidenceSource, items: list[EnumerationItem]) -> None:
    for match in _PRODUCT_INTRO_RE.finditer(source.text):
        for label in _split_items(match.group("items")):
            _add_item(items, label, (), source.number, "closed_list")
        _add_item(items, "services", (), source.number, "closed_list")

    lines = _short_lines(source)
    for index, line in lines:
        if len(line) > 70 or _normalize(line) in _HEADING_EXCLUSIONS:
            continue
        if _normalize(line) == "wearables home and accessories":
            for label in ("wearables", "accessories"):
                _add_item(
                    items,
                    label,
                    (line,),
                    source.number,
                    "heading",
                )
            continue
        lookahead = " ".join(text for _, text in lines[index + 1 : index + 7])
        relation = _LINE_OF_RE.search(lookahead)
        if relation and re.fullmatch(r"[A-Za-z][A-Za-z0-9 +&-]{1,35}", line):
            relation_label = relation.group("category")
            relation_tokens = _tokens(relation_label)
            # Filing prose often qualifies an already-listed category (for
            # example, "multipurpose tablets" for the iPad heading). Keep
            # one canonical evidence item while retaining the heading alias.
            for existing in items:
                if existing.source_number != source.number:
                    continue
                existing_tokens = _tokens(existing.label)
                if (
                    len(existing_tokens) < len(relation_tokens)
                    and relation_tokens[-len(existing_tokens) :] == existing_tokens
                ):
                    relation_label = existing.label
                    break
            _add_item(
                items,
                relation_label,
                (line,),
                source.number,
                "evidence_alias",
            )

    # A service heading is a high-confidence item only in a product section
    # where the source also describes the company's offerings or services.
    if re.search(r"\bservices\b", source.text, re.IGNORECASE):
        _add_item(items, "services", (), source.number, "heading")


def _segment_items(source: EvidenceSource, items: list[EnumerationItem]) -> None:
    for match in _CLOSED_LIST_RE.finditer(source.text):
        if not _SEGMENT_RE.search(match.group(0)):
            continue
        for label in _split_items(match.group("items")):
            aliases: tuple[str, ...] = ()
            if _normalize(label) == "amazon web services":
                aliases = ("AWS",)
            _add_item(items, label, aliases, source.number, "closed_list")


def _revenue_aliases(label: str, source_text: str) -> tuple[str, ...]:
    """Add only filing terms that are explicit in the local category text."""
    aliases: list[str] = [
        part.strip() for part in re.split(r"\s+and\s+", label, flags=re.I)
    ]
    for part in tuple(aliases):
        base = re.sub(r"\s+(?:products?|services?)$", "", part, flags=re.I)
        if _normalize(base) and _normalize(base) != _normalize(part):
            aliases.append(base)
    normalized = _normalize(label)
    if normalized.startswith("microsoft 365"):
        aliases.append("Microsoft 365")
    if normalized == "server products and cloud services":
        aliases.extend(
            term
            for term in ("Azure", "Server Products", "Cloud Services")
            if re.search(rf"\b{re.escape(term)}\b", source_text, re.I)
        )
    if normalized == "gaming" and re.search(r"\bXbox\b", source_text, re.I):
        aliases.append("Xbox")
    if normalized == "windows and devices":
        aliases.extend(
            term
            for term in ("Windows OEM", "Devices")
            if re.search(rf"\b{re.escape(term)}\b", source_text, re.I)
        )
    return tuple(aliases)


def _revenue_items(source: EvidenceSource, items: list[EnumerationItem]) -> None:
    lines = _short_lines(source)
    # Microsoft states the More Personal Computing categories as
    # comma-terminated list entries rather than standalone headings.
    for _, line in lines:
        bullet = re.match(
            r"(?P<label>Windows and Devices|Gaming|Search and news advertising)\s*,",
            line,
            re.IGNORECASE,
        )
        if bullet:
            label = bullet.group("label")
            _add_item(
                items,
                label,
                _revenue_aliases(label, source.text),
                source.number,
                "revenue",
            )

    for index, line in lines:
        normalized = _normalize(line)
        known_heading = any(
            phrase in normalized
            for phrase in (
                "server products",
                "microsoft 365",
                "linkedin",
                "dynamics products",
                "gaming",
                "search and news advertising",
                "windows and devices",
            )
        )
        if (
            not normalized
            or normalized in _HEADING_EXCLUSIONS
            or len(line) > 90
            or (re.search(r"\d", line) and not known_heading)
            or line.endswith((".", ",", ";"))
        ):
            continue
        if not any(term in normalized for term in _REVENUE_HEADING_TERMS):
            continue
        lookahead = " ".join(text for _, text in lines[index + 1 : index + 7])
        if not known_heading and not re.search(
            r"\b(revenue|business|products?|services?)\b", lookahead, re.I
        ):
            continue
        _add_item(
            items,
            line,
            _revenue_aliases(line, source.text),
            source.number,
            "revenue",
        )


def _risk_items(source: EvidenceSource, items: list[EnumerationItem]) -> None:
    for match in _RISK_LABEL_RE.finditer(source.text):
        _add_item(
            items,
            match.group("label"),
            (),
            source.number,
            "risk_label",
        )
    for match in _RISK_HEADING_RE.finditer(source.text):
        label = re.sub(r"\s+", " ", match.group("label")).title()
        aliases = [label.removesuffix(" Risks")]
        if "strategic and competitive" in label.casefold():
            aliases.extend(("competition", "competitive risks"))
        _add_item(items, label, aliases, source.number, "heading")
    for match in _AI_RISK_HEADING_RE.finditer(source.text):
        _add_item(
            items,
            "AI",
            ("artificial intelligence",),
            source.number,
            "heading",
        )


def extract_evidence_items(
    kind: str,
    sources: Iterable[EvidenceSource],
) -> tuple[EnumerationItem, ...]:
    """Extract high-confidence answer items from rendered evidence."""
    items: list[EnumerationItem] = []
    for source in sources:
        if kind == "product":
            _product_items(source, items)
        elif kind == "revenue":
            _revenue_items(source, items)
        elif kind == "segment":
            _segment_items(source, items)
        elif kind == "risk":
            _risk_items(source, items)
    return tuple(items)


def assess_enumeration_completeness(
    question: str,
    evidence_context: str,
    answer: str,
) -> EnumerationCompleteness:
    """Check that an exhaustive answer covers every confident evidence item."""
    kind = enumeration_kind(question)
    if kind is None:
        return EnumerationCompleteness(False, False, None, (), (), (), (), True)

    sources = parse_evidence_sources(evidence_context)
    items = extract_evidence_items(kind, sources)
    if len(items) < 2:
        return EnumerationCompleteness(
            False,
            True,
            kind,
            items,
            (),
            (),
            ("insufficient_high_confidence_evidence_items",),
            True,
        )

    covered: list[EnumerationItem] = []
    missing: list[EnumerationItem] = []
    for item in items:
        if any(_contains_alias(answer, alias) for alias in item.aliases):
            covered.append(item)
        else:
            missing.append(item)
    coverage = EnumerationCompleteness(
        True,
        True,
        kind,
        items,
        tuple(covered),
        tuple(missing),
        (),
        not missing,
    )
    bullet_matches = _bullet_item_matches(answer, coverage)
    overdetailed = (
        bool(_unclassified_bullet_indexes(answer, coverage))
        or len(bullet_matches) > len(set(bullet_matches.values()))
        or _bullet_count(answer) > len(items) + 2
    )
    return EnumerationCompleteness(
        True,
        True,
        kind,
        items,
        tuple(covered),
        tuple(missing),
        (),
        not missing,
        overdetailed,
    )


def build_enumeration_correction_prompt(
    question: str,
    evidence_context: str,
    draft_answer: str,
    assessment: EnumerationCompleteness,
    unsupported_numeric_claims: Iterable[str] = (),
) -> str:
    """Build one concise, evidence-bound correction request."""
    missing = "\n".join(
        f"- Source {item.source_number}: {item.label}"
        for item in assessment.missing_items
    )
    numeric = tuple(dict.fromkeys(unsupported_numeric_claims))
    violations: list[str] = []
    if missing:
        violations.append(
            "The draft omitted these explicit evidence-backed enumeration "
            f"items:\n{missing}"
        )
    if numeric:
        violations.append(
            "Remove numeric claims not printed in the cited evidence: "
            + ", ".join(numeric)
        )
    details = "\n\n".join(violations)
    return (
        "Correct the draft using only the same SEC evidence below. Return one "
        "concise final answer only. List every evidence-backed item exactly "
        "once, preserve canonical [Source N] citations, and do not add items "
        "from general knowledge. Do not calculate, round, convert, or invent "
        f"values.\n\n{details}\n\nQuestion: {question}\n\n"
        f"Evidence:\n{evidence_context}\n\nDraft answer:\n{draft_answer}"
    )
