"""Shared generation instructions used by every answer-producing path."""

import hashlib
import re

from src.generation.enumeration_completeness import (
    ENUMERATION_COMPLETENESS_FINGERPRINT,
    enumeration_kind,
)

ANSWER_FOCUS_CONTRACT = (
    "Answer the exact dimension asked in the question before adding supporting "
    "detail. For a comparison about each company's approach, first compare the "
    "evidence-supported products, services, revenue sources, or business drivers "
    "that answer that approach question. Use reported figures only as supporting "
    "evidence; do not replace the requested qualitative comparison with a table "
    "of figures or a comparison of reporting formats. Keep the answer concise and "
    "omit evidence that does not help answer the requested comparison dimension."
)

_APPROACH_QUESTION_RE = re.compile(r"\bapproach(?:es)?\b", re.IGNORECASE)


def answer_focus_contract_for_question(question: str) -> str:
    """Return the qualitative approach contract only for approach questions.

    The contract was introduced to correct an approach-comparison failure, so
    applying it to every question can distort unrelated fact and enumeration
    answers. Keep the scope deliberately narrow until a broader intent router
    has evidence for additional question families.
    """
    if _APPROACH_QUESTION_RE.search(question):
        return ANSWER_FOCUS_CONTRACT
    return ""


RISK_FOCUS_CONTRACT = (
    "For a scoped risk question, answer only the requested risk dimension. "
    "For quality or manufacturing questions, lead with the two direct "
    "evidence-backed mechanisms: design or manufacturing defects and defects "
    "in third-party components or products. Keep product liability, recalls, "
    "warranty costs, injuries, reputation, demand, and lost-sales effects "
    "under the defect mechanism that causes them instead of creating separate "
    "risk bullets. Do not broaden this focused answer into generic supplier "
    "continuity, capacity, shortage, industrial-accident, pandemic, natural-"
    "disaster, or other supply-chain risks unless the question explicitly asks "
    "about those dimensions or the excerpt directly makes them the requested "
    "manufacturing mechanism. For other scoped risk dimensions, group duplicate "
    "consequences under the requested mechanism, omit unrelated categories, "
    "and keep each bullet concise and directly supported by the cited filing "
    "evidence."
)

RISK_COMPARISON_CONTRACT = (
    "For a comparison of companies' approaches to international or other "
    "operational risk, compare the shared dimensions requested by the user "
    "in one concise bullet per company, followed by one short comparison. "
    "Prefer the common dimensions such as currency, regulation, and "
    "geopolitical exposure. Do not enumerate every disclosure, example, "
    "sub-risk, or consequence when the question asks about approach; keep "
    "those details implicit under the shared dimension they support."
)
_RISK_COMPARISON_RE = re.compile(
    r"\b(approach|compare|comparison)\w*\b.*\b(risk|risks|operations?)\b"
    r"|\b(risk|risks|operations?)\b.*\b(approach|compare|comparison)\w*\b",
    re.IGNORECASE,
)

_RISK_SCOPE_RE = re.compile(
    r"\b(risk factors?|risks?)\b",
    re.IGNORECASE,
)
_RISK_DIMENSION_RE = re.compile(
    r"\b(quality|manufactur|competition|cybersecurity|international|"
    r"operations?|supply|climate|privacy|trade)\w*\b",
    re.IGNORECASE,
)
RISK_FOCUS_CONTRACT_FINGERPRINT = "sha256:" + hashlib.sha256(
    (
        "risk-focus-v3-direct-defect-third-party-component-scope-"
        "group-consequences-exclude-generic-supply-chain-unless-requested-"
        "scoped-dimension-concise-evidence-"
        + ENUMERATION_COMPLETENESS_FINGERPRINT
    ).encode("utf-8")
).hexdigest()


def risk_focus_contract_for_question(question: str) -> str:
    """Return the scoped risk contract, excluding exhaustive enumerations."""
    if enumeration_kind(question) is not None:
        return ""
    if _RISK_SCOPE_RE.search(question) and _RISK_DIMENSION_RE.search(question):
        return RISK_FOCUS_CONTRACT
    return ""


def risk_comparison_contract_for_question(question: str) -> str:
    """Return the concise comparison contract for approach-risk questions."""
    return (
        RISK_COMPARISON_CONTRACT
        if _RISK_COMPARISON_RE.search(question)
        else ""
    )


RISK_COMPARISON_CONTRACT_FINGERPRINT = "sha256:" + hashlib.sha256(
    RISK_COMPARISON_CONTRACT.encode("utf-8")
).hexdigest()


ENUMERATION_COMPLETENESS_CONTRACT = (
    "For an exhaustive enumeration question, return a compact evidence-backed "
    "list. Include every distinct item explicitly exposed by the provided "
    "filing excerpts, give each item a canonical [Source N] citation, and do "
    "not add categories from general knowledge. Keep grouped filing categories "
    "grouped unless the evidence explicitly separates them. Do not omit an "
    "evidence-backed item merely because another item is more prominent. Use "
    "one concise bullet per filing-native category; do not expand examples, "
    "sub-products, features, brands, or sub-risks into extra bullets unless "
    "the excerpts present them as separate top-level categories. For a "
    "question asking for main sources or categories, answer at the same "
    "top-level granularity as the filing headings and omit descriptive "
    "details that are not themselves requested categories."
    " For revenue-source questions, omit reporting-segment or container "
    "labels and list only the revenue-bearing product or service headings "
    "explicitly described in the excerpts. For risk-factor questions, present "
    "filing headings and labeled categories as the primary list, then preserve "
    "prose-only or cross-cutting risk disclosures in one compact additional "
    "section. Include a short source-backed descriptor after each canonical risk "
    "label when the excerpt supports one, using no more than a brief phrase. "
    "Supporting risks may appear as short sub-bullets under that additional "
    "section, with one sub-bullet per explicitly disclosed supporting item. "
    "Do not make consequences, examples, or a child risk a separate peer "
    "category when the evidence identifies a parent category."
)


def enumeration_contract_for_question(question: str) -> str:
    """Return the list-completeness contract only for exhaustive enumerations."""
    return (
        ENUMERATION_COMPLETENESS_CONTRACT
        if enumeration_kind(question) is not None
        else ""
    )


def answer_completion_contract_for_question(question: str) -> str:
    """Combine the narrowly scoped answer contracts for one question."""
    return "\n".join(
        contract
        for contract in (
            answer_focus_contract_for_question(question),
            risk_focus_contract_for_question(question),
            risk_comparison_contract_for_question(question),
            enumeration_contract_for_question(question),
        )
        if contract
    )
NUMERIC_PAIR_CONTRACT = (
    "For every question that explicitly asks for a numeric trend, numeric "
    "comparison, or growth, inspect all provided "
    "sources for explicit period-and-value pairs for each compared entity. "
    "When those pairs exist, the answer MUST first list every underlying "
    "value relevant to the comparison together with its period, exactly as "
    "printed, before any trend summary. A percentage-only, qualitative, "
    "rounded, abbreviated, approximate, or range-based answer is incomplete "
    "when exact underlying values are available. Never omit those values or "
    "replace them with a percentage. Never replace filing values with rounded, "
    "abbreviated, or recalculated values. Do not calculate a difference, ratio, "
    "percentage, average, approximation, range, or unit conversion, even when "
    "the underlying values are cited. Do not introduce numeric shorthand such "
    "as '$100 billion range'. Report only numeric values explicitly present in "
    "the cited evidence. Before finalizing, check that every numeric comparison "
    "claim is a verbatim evidence value and that every available period-value "
    "pair was listed. Never answer with only a percentage when those underlying "
    "values are present."
)

NUMERIC_PAIR_REMINDER = (
    "Numeric checklist: for a numeric trend, numeric comparison, or growth "
    "question, first quote every "
    "relevant underlying value with its period when the context provides "
    "multiple period-and-value pairs. Do not round, abbreviate, or omit them, "
    "replace them with only a percentage, or summarize them as a numeric range. "
    "Do not calculate a difference, ratio, percentage, average, approximation, "
    "range, or unit conversion. Report only values explicitly present in the "
    "cited evidence, and verify every numeric claim before finalizing."
)
